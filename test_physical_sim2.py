import os
import json

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

with open('OMR_SCAN/active_batch.json', 'r') as f:
    b = json.load(f)
    batch_id = b['batchId']

docs = db.collection('scanSheets').where('batchId', '==', batch_id).get()
print(f"Found {len(docs)} completed sheets in database.")
for d in docs:
    data = d.to_dict()
    print(f"  - Sheet ID: {d.id} | Status: {data.get('status')} | Questions extracted: {len(data.get('answers', {}))}")
