import json
import os

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

with open('rise_omr_template.json', 'r') as f:
    template_data = json.load(f)

# The root template document MUST map to the exam for ExamDetail to find it!
template_doc = {
    "name": "RISE 2027 Official OMR",
    "description": "Canonical 50-question OMR template for RISE 2027",
    "examId": "exam_rise_2027",
    "status": "APPROVED",
    "createdAt": firestore.SERVER_TIMESTAMP,
    "updatedAt": firestore.SERVER_TIMESTAMP,
    "currentVersion": "v1.0.0",
    "versions": ["v1.0.0"]
}

# The version subdocument
version_doc = {
    "version": "v1.0.0",
    "status": "APPROVED",
    "createdAt": firestore.SERVER_TIMESTAMP,
    "configuration": template_data,
    "commitMessage": "Approved 50-question physical hardware template"
}

# Seed it using canonical template_exam_rise_2027
db.collection('templates').document('template_exam_rise_2027').set(template_doc)
db.collection('templates').document('template_exam_rise_2027').collection('versions').document('v1.0.0').set(version_doc)

print("Canonical RISE 2027 50-question template successfully seeded to Firestore Emulator!")
