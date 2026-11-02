import os
import time
import shutil
import uuid
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Directories
BASE_DIR = Path("OMR_SCAN")
INBOX_DIR = BASE_DIR / "inbox"
PROCESSED_DIR = BASE_DIR / "processed"
FAILED_DIR = BASE_DIR / "failed"
REVIEW_DIR = BASE_DIR / "review"

def setup_test_files():
    if not os.path.exists("test_marked2.png"):
        raise Exception("test_marked2.png not found!")

def clear_directories():
    for d in [INBOX_DIR, PROCESSED_DIR, FAILED_DIR, REVIEW_DIR]:
        for f in d.glob("*"):
            if f.is_file():
                f.unlink()
        
def drop_files(count, prefix="test", corrupted=False):
    files = []
    for i in range(count):
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.png"
        dest = INBOX_DIR / filename
        if corrupted:
            with open(dest, "w") as f:
                f.write("Not a real image")
        else:
            shutil.copy("test_marked2.png", dest)
        files.append(filename)
    return files

def wait_for_processing(files, timeout=600):
    start = time.time()
    processed = []
    failed = []
    review = []
    
    while True:
        processed = [f.name for f in PROCESSED_DIR.glob("*")]
        failed = [f.name for f in FAILED_DIR.glob("*")]
        review = [f.name for f in REVIEW_DIR.glob("*")]
        
        total_done = len(processed) + len(failed) + len(review)
        if total_done >= len(files):
            break
            
        if time.time() - start > timeout:
            print("TIMEOUT waiting for processing!")
            break
            
        time.sleep(1)
        
    duration = time.time() - start
    return processed, failed, review, duration

def run_test_suite():
    setup_test_files()
    
    report = {}
    
    # Test 1: Single file
    print("Testing 1 sheet...")
    clear_directories()
    f1 = drop_files(1, "single")
    p, f, r, d = wait_for_processing(f1)
    report['single'] = {'passed': len(p) + len(r) == 1, 'duration': d}
    
    # Test 2: 10 files (Parallel Check)
    print("Testing 10 sheets...")
    clear_directories()
    f10 = drop_files(10, "ten")
    p, f, r, d = wait_for_processing(f10)
    report['ten'] = {'passed': len(p) + len(r) == 10, 'duration': d}
    
    # Test 3: Failure Cases (Corrupted image)
    print("Testing corrupted file isolation...")
    clear_directories()
    drop_files(1, "corrupted", corrupted=True)
    drop_files(1, "valid_after_corrupt")
    p, f, r, d = wait_for_processing(["corrupted", "valid"], timeout=30)
    report['failure_isolation'] = {'passed': len(f) == 1 and (len(p) + len(r)) == 1, 'duration': d}

    # Test 4: 500 Sheets (Load test)
    print("Testing 500 sheets load simulation...")
    clear_directories()
    f500 = drop_files(500, "load500")
    p, f, r, d = wait_for_processing(f500, timeout=1200)
    report['load500'] = {
        'passed': len(p) + len(f) + len(r) == 500, 
        'duration': d,
        'success': len(p),
        'review': len(r),
        'failed': len(f)
    }
    
    print("\n--- FINAL AUDIT RESULTS ---")
    print(json.dumps(report, indent=2))
    
if __name__ == "__main__":
    run_test_suite()
