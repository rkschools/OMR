import json
import os

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

def upload_template(file_path: str, template_id: str, template_name: str, description: str):
    with open(file_path, 'r') as f:
        template_data = json.load(f)

    # 1. Create canonical exam if not exists (we will link Template 1 to exam_list1, Template 2 to exam_list2)
    exam_id = f"exam_{template_id}"
    exam_data = {
        "name": template_name,
        "description": description,
        "year": "2027",
        "classes": ["8"],
        "status": "ACTIVE",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "examId": exam_id,
        "templateId": template_id,
        "templateVersionId": "v1.0.0"
    }
    db.collection('exams').document(exam_id).set(exam_data)

    template_doc = {
        "name": template_name,
        "description": description,
        "examId": exam_id,
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
        "commitMessage": f"Initial upload for {template_name}"
    }

    db.collection('templates').document(template_id).set(template_doc)
    db.collection('templates').document(template_id).collection('versions').document('v1.0.0').set(version_doc)

if __name__ == "__main__":
    upload_template('list1_template.json', 'template_list1', 'RISE 2027 - List 1', 'English 10, Science 20, Maths 15, GK 3, Current Affairs 2')
    upload_template('list2_template.json', 'template_list2', 'RISE 2027 - List 2', 'English 11, Science 21, Maths 15, GK 3')
    print("Both templates uploaded and linked to new exams!")
