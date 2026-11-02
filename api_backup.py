import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel
from typing import List, Dict, Any

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

def verify_token(authorization: str = Header(...)):
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Invalid authorization header')
    token = authorization.split('Bearer ')[1]
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f'Invalid authentication credentials: {e}')

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
    
    # Save temporarily to let the engine parse it
    # A cleaner approach would be updating OMRLayoutEngine to accept a dict directly, 
    # but for now we write to a temp file.
    import tempfile
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.json') as f:
        json.dump(config, f)
        temp_path = f.name
        
    try:
        from omr_layout_engine import OMRLayoutEngine
        # Initialization itself will fail if constraints (like height) are violated
        engine = OMRLayoutEngine(temp_path)
        return {"valid": True, "message": "Template geometry is valid."}
    except Exception as e:
        return {"valid": False, "error": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/templates/generate-preview")
def generate_preview(request: TemplateValidationRequest, user: dict = Depends(verify_token)):
    """
    Generates a PDF from the requested config and returns a local URL.
    """
    config = request.template_config
    import tempfile
    import uuid
    
    os.makedirs('temp', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    
    config_path = os.path.join('temp', f"{uuid.uuid4()}.json")
    with open(config_path, 'w') as fc:
        json.dump(config, fc)
        
    pdf_filename = f"preview_{uuid.uuid4()}.pdf"
    pdf_path = os.path.join('output', pdf_filename)
    
    try:
        gen = PDFGenerator(config_path, pdf_path)
        gen.generate()
        
        # We serve the output directory statically or return the path for local use
        return {"status": "success", "local_path": pdf_path, "url": f"/output/{pdf_filename}"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(config_path): os.remove(config_path)

@app.post("/api/scan")
async def scan_omr(file: UploadFile = File(...), user: dict = Depends(verify_token)):
    """
    Receives an uploaded scanned image, runs the scanner_engine locally, and returns answers.
    """
    import uuid
    os.makedirs('uploads', exist_ok=True)
    
    img_path = os.path.join('uploads', f"scan_{uuid.uuid4()}_{file.filename}")
    with open(img_path, 'wb') as f:
        content = await file.read()
        f.write(content)
        
    try:
        scanner = ScannerEngine('rise_omr_template.json')
        img = scanner.load_image(img_path)
        marks = scanner.detect_registration_marks(img)
        warped = scanner.warp_canonical(img, marks)
        answers = scanner.extract_answers(warped)
        return {"status": "success", "answers": answers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Optionally move to 'processed' folder instead of removing, based on reqs
        os.makedirs('processed', exist_ok=True)
        processed_path = os.path.join('processed', os.path.basename(img_path))
        if os.path.exists(img_path):
            os.rename(img_path, processed_path)

# Serve output directory statically so frontend can display the PDFs
from fastapi.staticfiles import StaticFiles
app.mount("/output", StaticFiles(directory="output"), name="output")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
