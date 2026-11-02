"""
RISE 2027 CANONICAL DATABASE SEED
Seeds the single canonical exam, template, and answer key.
"""
import json
import os

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore
db = firestore.Client(project="rise-omr-backend-2027")

# ============================================================
# 1. CANONICAL RISE 2027 EXAM
# ============================================================
exam_data = {
    "name": "RISE 2027",
    "description": "Official RISE 2027 Scholarship Examination",
    "year": "2027",
    "classes": ["8"],
    "status": "ACTIVE",
    "createdAt": firestore.SERVER_TIMESTAMP,
    "updatedAt": firestore.SERVER_TIMESTAMP,
    "examId": "exam_rise_2027",
    "templateId": "template_exam_rise_2027",
    "templateVersionId": "v1.0.0"
}
db.collection('exams').document('exam_rise_2027').set(exam_data)
print("[1/5] Exam 'exam_rise_2027' created.")

# ============================================================
# 2. CANONICAL 50-QUESTION TEMPLATE
# ============================================================
with open('rise_omr_template.json', 'r') as f:
    template_config = json.load(f)

# Verify question count
total_q = sum(s['question_count'] for s in template_config['sections'])
assert total_q == 50, f"Template has {total_q} questions, expected 50!"

template_doc = {
    "name": "RISE 2027 Official OMR",
    "description": f"Official {total_q}-question OMR template for RISE 2027",
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
    "approvedAt": firestore.SERVER_TIMESTAMP,
    "configuration": template_config,
    "commitMessage": "Approved 50-question physical hardware template"
}

db.collection('templates').document('template_exam_rise_2027').set(template_doc)
db.collection('templates').document('template_exam_rise_2027').collection('versions').document('v1.0.0').set(version_doc)
print(f"[2/5] Template 'template_exam_rise_2027' v1.0.0 created ({total_q} questions).")

# ============================================================
# 3. SECTIONS VERIFICATION
# ============================================================
expected_sections = {
    "TELUGU": 3, "HINDI": 3, "ENGLISH": 5,
    "MATHEMATICS": 10, "SCIENCE": 18, "SOCIAL STUDIES": 5,
    "GK / COMPUTER": 4, "CURRENT AFFAIRS": 2
}
for s in template_config['sections']:
    exp = expected_sections.get(s['name'])
    assert exp == s['question_count'], f"Section {s['name']}: expected {exp}, got {s['question_count']}"
print("[3/5] All 8 sections verified: Total = 50 questions.")

# ============================================================
# 4. SAMPLE ANSWER KEY (Set A) — PUBLISHED
# ============================================================
import random
for p_set, seed_val in [('A', 42), ('B', 43), ('C', 44), ('D', 45)]:
    random.seed(seed_val)
    answer_key = {str(q): random.choice(['A', 'B', 'C', 'D']) for q in range(1, 51)}
    answer_key_doc = {
        "examId": "exam_rise_2027",
        "classId": "8",
        "class": "8",
        "paperSet": p_set,
        "status": "PUBLISHED",
        "isTestData": True,
        "keys": answer_key,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "publishedAt": firestore.SERVER_TIMESTAMP
    }
    db.collection('answerKeys').document(f'exam_rise_2027_8_{p_set}').set(answer_key_doc)
    print(f"[4/5] Answer Key for Set {p_set} published ({len(answer_key)} answers).")

# ============================================================
# 5. CREATE ADMIN USER
# ============================================================
print("[5/5] Admin user must be created via Auth Emulator UI (http://127.0.0.1:9099).")
print()
print("=" * 60)
print("CANONICAL RISE 2027 CONFIGURATION:")
print(f"  Exam ID:              exam_rise_2027")
print(f"  Template ID:          template_exam_rise_2027")
print(f"  Template Version:     v1.0.0")
print(f"  Status:               APPROVED")
print(f"  Total Questions:      {total_q}")
print(f"  Total Sections:       {len(template_config['sections'])}")
for s in template_config['sections']:
    print(f"    {s['name']:20s}  Q{s['question_numbering']['start']}-Q{s['question_numbering']['end']}  ({s['question_count']} questions)")
print(f"  Answer Key Set A:     PUBLISHED ({len(answer_key)} answers)")
print("=" * 60)
