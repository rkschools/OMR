import os
import time
import json
import uuid
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import fitz  # PyMuPDF
import cv2
import firebase_admin
from firebase_admin import credentials
from concurrent.futures import ProcessPoolExecutor, as_completed
from scanner_engine import ScannerEngine

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

BASE_DIR = Path("OMR_SCAN")
INBOX_DIR = BASE_DIR / "inbox"
PROCESSING_DIR = BASE_DIR / "processing"
PROCESSED_DIR = BASE_DIR / "processed"
REVIEW_DIR = BASE_DIR / "review"
FAILED_DIR = BASE_DIR / "failed"
ARCHIVE_DIR = BASE_DIR / "archive"
ACTIVE_BATCH_FILE = BASE_DIR / "active_batch.json"

for d in [INBOX_DIR, PROCESSING_DIR, PROCESSED_DIR, REVIEW_DIR, FAILED_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def process_single_image(img_path: Path, batch_config: dict):
    """Run scanner engine on a single image inside a worker process."""
    try:
        scanner = ScannerEngine(config_dict=batch_config['template_config'])
        img = scanner.load_image(str(img_path))
        marks = scanner.detect_registration_marks(img)
        warped = scanner.warp_canonical(img, marks)
        answers = scanner.extract_answers(warped)
        
        # Determine status
        status = 'VALID'
        answered_count = 0
        for q, ans in answers.items():
            if not str(q).startswith('REG_'):
                if isinstance(ans, dict):
                    classification = ans.get('classification', '')
                    if classification in ['MULTIPLE / INVALID', 'AMBIGUOUS', 'MULTIPLE']:
                        status = 'REVIEW_REQUIRED'
                    if ans.get('extracted') not in [None, '', 'BLANK']:
                        answered_count += 1
                elif ans in ['MULTIPLE', 'AMBIGUOUS']:
                    status = 'REVIEW_REQUIRED'
                elif ans not in [None, '', 'BLANK']:
                    answered_count += 1
                
        reg_num = ""
        for i in range(6):
            r = answers.get(f'REG_{i}')
            if isinstance(r, dict):
                reg_num += str(r.get('extracted', ''))
            elif r:
                reg_num += str(r)

        # If not bubbled via REG columns, check batch roster mapping or inspect filename for 6-digit registration pattern
        if not reg_num or len(reg_num.strip()) < 6:
            import re
            m = re.search(r'(\d{6})', img_path.name)
            if m:
                reg_num = m.group(1)
            elif batch_config and batch_config.get('page_roster'):
                page_m = re.search(r'_page(\d+)', img_path.name)
                if page_m:
                    reg_num = str(batch_config['page_roster'].get(str(page_m.group(1)), ''))

        # Ambiguous if registration number unreadable or blank sheet or questions ambiguous
        if not reg_num or len(reg_num.strip()) < 6 or '?' in reg_num or 'X' in reg_num:
            status = 'REVIEW_REQUIRED'
        elif answered_count == 0:
            status = 'REVIEW_REQUIRED'

        return {
            "success": True,
            "path": img_path,
            "answers": answers,
            "status": status,
            "registration_number": reg_num
        }
    except Exception as e:
        return {
            "success": False,
            "path": img_path,
            "error": str(e)
        }

def process_file(filepath: Path):
    if not ACTIVE_BATCH_FILE.exists():
        print(f"[{time.strftime('%X')}] No active_batch.json found. Waiting for dashboard configuration to process {filepath.name}.")
        return

    try:
        with open(ACTIVE_BATCH_FILE, 'r') as f:
            batch_config = json.load(f)
    except Exception as e:
        print(f"Error reading active_batch.json: {e}")
        return
    if not filepath.exists():
        return

    print(f"[{time.strftime('%X')}] Processing new scan arrival: {filepath.name}")
    
    # Move to processing
    processing_path = PROCESSING_DIR / filepath.name
    try:
        shutil.move(str(filepath), str(processing_path))
    except FileNotFoundError:
        print(f"File {filepath.name} vanished before moving.")
        return
    
    images_to_process = []
    
    if processing_path.suffix.lower() == '.pdf':
        try:
            doc = fitz.open(str(processing_path))
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=300)
                img_out_path = PROCESSING_DIR / f"{processing_path.stem}_page{page_num+1}.png"
                pix.save(str(img_out_path))
                images_to_process.append(img_out_path)
            doc.close()
            # Move the original PDF to archive
            shutil.move(str(processing_path), str(ARCHIVE_DIR / processing_path.name))
        except Exception as e:
            print(f"Error splitting PDF {filepath.name}: {e}")
            shutil.move(str(processing_path), str(FAILED_DIR / processing_path.name))
            return
    else:
        images_to_process.append(processing_path)
        
    print(f"Queueing {len(images_to_process)} pages for parallel OMR recognition...")
    
    # Parallel processing queue
    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_single_image, img_path, batch_config): img_path for img_path in images_to_process}
        
        for future in as_completed(futures):
            res: dict = future.result()
            results.append(res)
            
            img_path = Path(res.get('path', ''))
            is_success = bool(res.get('success', False))
            if is_success:
                # Save to Firestore
                doc_id = str(uuid.uuid4())
                
                # Convert answers keys to strings because Firestore requires string keys
                answers_dict: dict = res.get('answers', {})
                str_answers = {str(k): v for k, v in answers_dict.items()}
                str_answers['registration_number'] = res.get('registration_number', '')
                str_answers['paperSet'] = batch_config.get('paperSet', 'A')
                
                status_str = str(res.get('status', 'VALID'))
                scan_doc = {
                    "id": doc_id,
                    "batchId": batch_config['batchId'],
                    "examId": batch_config['examId'],
                    "classId": batch_config['classId'],
                    "paperSet": batch_config['paperSet'],
                    "templateId": batch_config.get('templateId', ''),
                    "templateVersionId": batch_config.get('templateVersionId', ''),
                    "answers": str_answers,
                    "status": status_str,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "fileName": img_path.name
                }
                
                try:
                    db.collection('scanSheets').document(doc_id).set(scan_doc)
                    print(f"  [+] Sheet processed: {status_str} | Reg: {res.get('registration_number')}")
                    
                    # Move image based on status
                    if status_str == 'REVIEW_REQUIRED':
                        shutil.move(str(img_path), str(REVIEW_DIR / img_path.name))
                    else:
                        shutil.move(str(img_path), str(PROCESSED_DIR / img_path.name))
                except Exception as e:
                    print(f"  [-] Database failure for {img_path.name}: {e}")
                    shutil.move(str(img_path), str(FAILED_DIR / img_path.name))
            else:
                print(f"  [-] Sheet failed: {res.get('error')}")
                shutil.move(str(img_path), str(FAILED_DIR / img_path.name))

class IngestionHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            filepath = Path(event.src_path)
            if filepath.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
                # Wait for file to finish copying over LAN via stable-size check
                stable_count = 0
                last_size = -1
                while stable_count < 3:
                    if not filepath.exists():
                        return
                    current_size = filepath.stat().st_size
                    if current_size == last_size and current_size > 0:
                        stable_count += 1
                    else:
                        stable_count = 0
                        last_size = current_size
                    time.sleep(0.5)
                
                process_file(filepath)

def start_ingestion_service():
    print(f"Starting OMR Scan Ingestion Service.")
    print(f"Watching inbox directory: {INBOX_DIR.absolute()}")
    
    # Process existing files in inbox first
    for f in INBOX_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
            process_file(f)
            
    event_handler = IngestionHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INBOX_DIR), recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_ingestion_service()
