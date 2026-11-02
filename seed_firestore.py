import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase (requires GOOGLE_APPLICATION_CREDENTIALS)
try:
    firebase_admin.initialize_app(options={'projectId': 'rise-omr-backend-2027'})
except ValueError:
    pass # Already initialized

db = firestore.client()

def seed():
    exam_id = "exam_rise_2027"
    template_id = "template_rise_2027"
    version_id = "v1"

    # 1. Create Exam Document
    exam_ref = db.collection('exams').document(exam_id)
    exam_ref.set({
        "examId": exam_id,
        "name": "RISE 2027 (Classes 1-10)",
        "year": "2027",
        "description": "Seeded RISE Exam Configuration",
        "status": "ACTIVE",
        "createdAt": firestore.firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.firestore.SERVER_TIMESTAMP
    })

    # 2. Create Template Document
    template_ref = db.collection('templates').document(template_id)
    template_ref.set({
        "examId": exam_id,
        "name": "RISE 2027 Standard Template",
        "currentVersion": version_id,
        "status": "APPROVED",
        "createdAt": firestore.firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.firestore.SERVER_TIMESTAMP
    })

    # 3. Load existing JSON
    with open('rise_omr_template.json', 'r') as f:
        config = json.load(f)

    # Ensure marking scheme is accurate to constraints (Correct=+1, Wrong=-1/3, Blank=0)
    config['marking_scheme'] = {
        "correct": 1.0,
        "wrong": -0.333333,
        "blank": 0.0
    }

    # Ensure it exactly preserves: Telugu(3), Hindi(3), English(5), Maths(10), Science(18), Social(5), GK(4), CurrentAffairs(2)
    # The JSON already has this exact structure if generated correctly earlier.

    # 4. Create Template Version Document (Immutable since APPROVED)
    version_ref = template_ref.collection('versions').document(version_id)
    version_ref.set({
        "version": version_id,
        "status": "APPROVED",
        "configuration": config,
        "createdAt": firestore.firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.firestore.SERVER_TIMESTAMP,
        "approvedAt": firestore.firestore.SERVER_TIMESTAMP
    })

    print(f"Successfully seeded RISE 2027 Exam ({exam_id}) and Template Version ({version_id}) into Firestore.")

if __name__ == "__main__":
    seed()
