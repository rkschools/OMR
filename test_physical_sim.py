import json
import os
import shutil
import uuid
import time
from pathlib import Path

# Use the real db
os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

# Use our PDF
from pdf_generator import PDFGenerator
from simulate_ricoh import simulate_ricoh_network_drop

# Setup directories
inbox = Path("OMR_SCAN/inbox")
processed = Path("OMR_SCAN/processed")
inbox.mkdir(parents=True, exist_ok=True)
processed.mkdir(parents=True, exist_ok=True)

# 1. Create Active Batch exactly as UI would
with open('rise_omr_template.json', 'r') as f:
    config = json.load(f)

batch_id = f"BATCH_SIM_{int(time.time())}"
batch_doc = {
    "batchId": batch_id,
    "examId": "exam_rise_2027",
    "classId": "8",
    "paperSet": "A",
    "templateId": "template_exam_rise_2027",
    "templateVersionId": "v1.0.0",
    "template_config": config
}

with open('OMR_SCAN/active_batch.json', 'w') as f:
    json.dump(batch_doc, f, indent=2)

print(f"Set Active Batch: {batch_id}")

# 2. Simulate 5 physical sheets arriving over network
sim_pdf = Path("output/RISE_2027_OMR_Final_50Q.pdf")
print("Injecting sheets over simulated SMB...")
for i in range(5):
    simulate_ricoh_network_drop(sim_pdf, inbox)

# 3. Wait for ingestion service to pick them up
print("Waiting for ingestion service (10 seconds)...")
time.sleep(10)

# 4. Verify Firestore
docs = db.collection('scanSheets').where('batchId', '==', batch_id).get()
print(f"Found {len(docs)} completed sheets in database.")
for d in docs:
    data = d.to_dict()
    print(f"  - Sheet ID: {d.id} | Status: {data.get('status')} | Questions extracted: {len(data.get('answers', {}))}")
    if len(data.get('answers', {})) == 50:
        print("    [OK] Extraction exactly matches 50 questions!")
    else:
        print(f"    [FAIL] Expected 50, got {len(data.get('answers', {}))}")

