import re

with open('api.py', 'r') as f:
    content = f.read()

new_imports = """import os
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import auth as firebase_auth, firestore
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
"""
content = re.sub(r'import os.*?from typing import List, Dict, Any\n', new_imports, content, flags=re.DOTALL)

db_init = """
# Initialize Firebase Admin ONLY for token verification (does not require ADC)
try:
    firebase_admin.initialize_app(options={'projectId': 'rise-omr-backend-2027'})
except Exception as e:
    print("Warning: Firebase already initialized.", e)

db = firestore.client()
"""
content = re.sub(r'# Initialize Firebase Admin.*?print\("Warning: Firebase already initialized\.", e\)\n', db_init, content, flags=re.DOTALL)

scan_eval_code = """
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

@app.post("/api/scan")
async def scan_omr(file: UploadFile = File(...), template_id: str = Form(...), template_version: str = Form(None), user: dict = Depends(verify_token)):
    import uuid
    os.makedirs('uploads', exist_ok=True)
    
    # Fetch template config from Firestore
    if template_version:
        doc_ref = db.collection('templates').document(template_id).collection('versions').document(template_version)
    else:
        doc_ref = db.collection('templates').document(template_id)
        
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Template not found")
        
    template_config = doc.to_dict().get('config', doc.to_dict())
    
    img_path = os.path.join('uploads', f"scan_{uuid.uuid4()}_{file.filename}")
    with open(img_path, 'wb') as f:
        content = await file.read()
        f.write(content)
        
    try:
        scanner = ScannerEngine(config_dict=template_config)
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
"""
content = re.sub(r'@app\.post\("/api/templates/generate-preview"\).*?os\.rename\(img_path, processed_path\)\n', scan_eval_code, content, flags=re.DOTALL)

with open('api.py', 'w') as f:
    f.write(content)
