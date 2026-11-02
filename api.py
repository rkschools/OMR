import os
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from pdf_generator import PDFGenerator
from scanner_engine import ScannerEngine
from evaluation_engine import EvaluationEngine

app = FastAPI(title="RISE OMR Platform API")

# Setup CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize Firebase Admin ONLY for token verification (does not require ADC)
try:
    firebase_admin.initialize_app(options={'projectId': 'rise-omr-backend-2027'})
except Exception as e:
    print("Warning: Firebase already initialized.", e)

class TemplateValidationRequest(BaseModel):
    template_config: dict

def verify_token():
    return {'uid': 'emulator-admin', 'email': 'admin@rise.com'}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/templates/validate")
def validate_template(request: TemplateValidationRequest, user: dict = Depends(verify_token)):
    """
    Validates a raw template JSON by running it through the OMRLayoutEngine.
    If it fits on the page and the geometry is valid, returns success.
    """
    config = request.template_config
    
    try:
        from omr_layout_engine import OMRLayoutEngine
        # Initialization itself will fail if constraints (like height) are violated
        engine = OMRLayoutEngine(config_dict=config)
        return {"valid": True, "message": "Template geometry is valid."}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.post("/api/templates/generate-preview")
def generate_preview(request: TemplateValidationRequest, user: dict = Depends(verify_token)):
    config = request.template_config
    import uuid
    
    os.makedirs('output', exist_ok=True)
    pdf_filename = f"preview_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join('output', pdf_filename)
    
    try:
        gen = PDFGenerator(config_dict=config, output_path=pdf_path)
        gen.generate()
        return {"status": "success", "local_path": pdf_path, "url": f"/output/{pdf_filename}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class BatchConfigRequest(BaseModel):
    batchId: str
    examId: str
    classId: str
    paperSet: str
    templateId: str
    templateVersionId: str
    template_config: dict

@app.post("/api/scanner/batch/active")
def set_active_batch(request: BatchConfigRequest, user: dict = Depends(verify_token)):
    try:
        os.makedirs('OMR_SCAN', exist_ok=True)
        with open('OMR_SCAN/active_batch.json', 'w') as f:
            json.dump(request.dict(), f, indent=2)
        return {"status": "success", "message": "Active batch configured successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
async def scan_omr(file: UploadFile = File(...), template_config: str = Form(...), user: dict = Depends(verify_token)):
    import uuid
    os.makedirs('uploads', exist_ok=True)
    
    try:
        config_dict = json.loads(template_config)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid template_config JSON")
        
    
    img_path = os.path.join('uploads', f"scan_{uuid.uuid4()}_{file.filename}")
    with open(img_path, 'wb') as f:
        content = await file.read()
        f.write(content)
        
    try:
        scanner = ScannerEngine(config_dict=config_dict)
        img = scanner.load_image(img_path)
        marks = scanner.detect_registration_marks(img)
        warped = scanner.warp_canonical(img, marks)
        answers = scanner.extract_answers(warped)
        return {"status": "success", "answers": answers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.makedirs('processed', exist_ok=True)
        processed_path = os.path.join('processed', os.path.basename(img_path))
        if os.path.exists(img_path):
            os.rename(img_path, processed_path)

class EvaluationRequest(BaseModel):
    extracted_answers: Dict[str, Any]
    answer_key: Dict[str, str]
    template_config: dict

@app.post("/api/evaluate")
def evaluate_omr(request: EvaluationRequest, user: dict = Depends(verify_token)):
    try:
        engine = EvaluationEngine(config_dict=request.template_config)
        results = engine.evaluate(request.extracted_answers, request.answer_key)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/answer-keys/upload")
async def upload_answer_key(
    file: UploadFile = File(...),
    exam_id: str = Form(...),
    class_id: str = Form(...),
    paper_set: str = Form(...),
    is_test_data: bool = Form(True),
    user: dict = Depends(verify_token)
):
    import time
    import csv
    import io

    t0 = time.perf_counter()
    content = await file.read()
    t1 = time.perf_counter()
    upload_time = t1 - t0

    # Parse
    raw_text = content.decode('utf-8', errors='replace')
    filename = file.filename.lower()
    
    parsed_entries = []
    t2_start = time.perf_counter()
    if filename.endswith('.json'):
        try:
            data = json.loads(raw_text)
            if isinstance(data, dict):
                for k, v in data.items():
                    parsed_entries.append((str(k), str(v)))
            elif isinstance(data, list):
                for item in data:
                    parsed_entries.append((str(item.get('q')), str(item.get('ans'))))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"JSON parsing error: {e}")
    else:
        # Default CSV
        reader = csv.reader(io.StringIO(raw_text))
        for row in reader:
            if not row or len(row) < 2:
                continue
            # Skip header
            if row[0].strip().lower() in ['q', 'question', 'question_number', 'q_no']:
                continue
            parsed_entries.append((row[0].strip(), row[1].strip()))
    t2_end = time.perf_counter()
    parse_time = t2_end - t2_start

    # Mapping Q1-Q50
    t3_start = time.perf_counter()
    mapped_keys = {}
    duplicates = []
    for q_str, ans_str in parsed_entries:
        # Clean question number (e.g. Q1 -> 1)
        q_clean = ''.join(c for c in q_str if c.isdigit())
        if not q_clean:
            continue
        q_num = int(q_clean)
        ans_clean = ans_str.strip().upper()
        if q_num in mapped_keys:
            duplicates.append(q_num)
        mapped_keys[q_num] = ans_clean
    t3_end = time.perf_counter()
    mapping_time = t3_end - t3_start

    # Validation
    t4_start = time.perf_counter()
    errors = []
    if duplicates:
        errors.append(f"Duplicate question numbers detected: {sorted(list(set(duplicates)))}")

    missing = [q for q in range(1, 51) if q not in mapped_keys]
    if missing:
        errors.append(f"Missing question numbers: {missing[:10]}{'...' if len(missing) > 10 else ''} (Total missing: {len(missing)})")

    invalid_options = {q: a for q, a in mapped_keys.items() if a not in ['A', 'B', 'C', 'D']}
    if invalid_options:
        errors.append(f"Invalid answer options detected on questions: {list(invalid_options.keys())} (Only A, B, C, D allowed)")

    if len(mapped_keys) != 50:
        errors.append(f"Expected exactly 50 mapped questions, got {len(mapped_keys)}")

    t4_end = time.perf_counter()
    validation_time = t4_end - t4_start
    total_time = t4_end - t0

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "mapped_count": len(mapped_keys),
            "timings": {
                "upload_time_s": round(upload_time, 4),
                "parse_time_s": round(parse_time, 4),
                "mapping_time_s": round(mapping_time, 4),
                "validation_time_s": round(validation_time, 4),
                "total_time_s": round(total_time, 4)
            }
        }

    return {
        "valid": True,
        "exam_id": exam_id,
        "class_id": class_id,
        "paper_set": paper_set,
        "is_test_data": is_test_data,
        "keys": {str(k): v for k, v in mapped_keys.items()},
        "total_questions": len(mapped_keys),
        "timings": {
            "upload_time_s": round(upload_time, 4),
            "parse_time_s": round(parse_time, 4),
            "mapping_time_s": round(mapping_time, 4),
            "validation_time_s": round(validation_time, 4),
            "total_time_s": round(total_time, 4)
        }
    }

# Serve output directory statically so frontend can display the PDFs
from fastapi.staticfiles import StaticFiles
app.mount("/output", StaticFiles(directory="output"), name="output")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
