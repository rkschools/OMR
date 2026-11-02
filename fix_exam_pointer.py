import os
os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

db.collection('exams').document('exam_rise_2027').update({
    "templateId": "template_exam_rise_2027",
    "templateVersionId": "v1.0.0"
})

print("Exam updated to point securely to the template.")
