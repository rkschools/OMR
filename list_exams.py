import os
os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")
exams = db.collection('exams').get()
for e in exams:
    print(e.id, e.to_dict())
