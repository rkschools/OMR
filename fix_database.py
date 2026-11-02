import json
import os

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

# 1. Create Canonical Exam
exam_data = {
    "name": "RISE 2027",
    "description": "Official RISE 2027 Examination",
    "year": "2027",
    "classes": ["8"],
    "status": "ACTIVE",
    "createdAt": firestore.SERVER_TIMESTAMP,
    "updatedAt": firestore.SERVER_TIMESTAMP,
    "examId": "exam_rise_2027"
}
db.collection('exams').document('exam_rise_2027').set(exam_data)

# 2. Upload Template Configuration correctly
with open('rise_omr_template.json', 'r') as f:
    template_data = json.load(f)

template_doc = {
    "name": "RISE 2027 Final OMR",
    "description": "Official 50-question OMR template",
    "examId": "exam_rise_2027",
    "status": "APPROVED",
    "createdAt": firestore.SERVER_TIMESTAMP,
    "updatedAt": firestore.SERVER_TIMESTAMP,
    "currentVersion": "v1.0.0",
    "versions": ["v1.0.0"]
}

version_doc = {
    "version": "v1.0.0",
    "status": "APPROVED",
    "createdAt": firestore.SERVER_TIMESTAMP,
    "configuration": template_data,
    "commitMessage": "Approved 50-Question Physical Hardware Template"
}

db.collection('templates').document('template_exam_rise_2027').set(template_doc)
db.collection('templates').document('template_exam_rise_2027').collection('versions').document('v1.0.0').set(version_doc)

print("Database fixed: Created exam_rise_2027 and its associated 50-question template.")
