import os
import json

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore

# ============================================================
# 1. DEFINE CLASS 1-5 AND CLASS 6-9 SECTION ALLOCATIONS
# ============================================================

c1_5_sections = [
    {
        "section_id": "english",
        "name": "ENGLISH",
        "order": 1,
        "allocated_marks": 11,
        "question_count": 11,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 1, "end": 11}
    },
    {
        "section_id": "science",
        "name": "SCIENCE",
        "order": 2,
        "allocated_marks": 21,
        "question_count": 21,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 12, "end": 32}
    },
    {
        "section_id": "maths",
        "name": "MATHEMATICS",
        "order": 3,
        "allocated_marks": 15,
        "question_count": 15,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 33, "end": 47}
    },
    {
        "section_id": "gk_computer",
        "name": "GK / COMPUTER",
        "order": 4,
        "allocated_marks": 3,
        "question_count": 3,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 48, "end": 50}
    }
]

c6_9_sections = [
    {
        "section_id": "english",
        "name": "ENGLISH",
        "order": 1,
        "allocated_marks": 10,
        "question_count": 10,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 1, "end": 10}
    },
    {
        "section_id": "science",
        "name": "SCIENCE",
        "order": 2,
        "allocated_marks": 20,
        "question_count": 20,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 11, "end": 30}
    },
    {
        "section_id": "maths",
        "name": "MATHEMATICS",
        "order": 3,
        "allocated_marks": 15,
        "question_count": 15,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 31, "end": 45}
    },
    {
        "section_id": "gk_computer",
        "name": "GK / COMPUTER",
        "order": 4,
        "allocated_marks": 3,
        "question_count": 3,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 46, "end": 48}
    },
    {
        "section_id": "current_affairs",
        "name": "CURRENT AFFAIRS",
        "order": 5,
        "allocated_marks": 2,
        "question_count": 2,
        "marks_per_question": 1,
        "option_count": 4,
        "question_numbering": {"start": 49, "end": 50}
    }
]

# Load existing rise_omr_template.json
with open('rise_omr_template.json', 'r') as f:
    template_config = json.load(f)

# Set base default sections to Classes 6-9
template_config['sections'] = c6_9_sections
template_config['total_questions'] = 50
template_config['total_marks'] = 50

# Configure independent classesConfig for all 9 classes (1 to 9)
classes_config = {}
for c in ["1", "2", "3", "4", "5"]:
    classes_config[c] = {"sections": c1_5_sections}
for c in ["6", "7", "8", "9"]:
    classes_config[c] = {"sections": c6_9_sections}

template_config['classesConfig'] = classes_config

# Save back to rise_omr_template.json
with open('rise_omr_template.json', 'w') as f:
    json.dump(template_config, f, indent=2)
print("[1/4] Updated rise_omr_template.json with Classes 1-9 configurations.")

# ============================================================
# 2. UPDATE FIRESTORE TEMPLATE & EXAM DOCUMENTS
# ============================================================
db = firestore.Client(project="rise-omr-backend-2027")

# Update Exam: all 9 classes
exam_ref = db.collection('exams').document('exam_rise_2027')
exam_ref.update({
    "classes": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    "updatedAt": firestore.SERVER_TIMESTAMP
})
print("[2/4] Updated exam_rise_2027 classes list to Classes 1-9.")

# Update Template Version
version_ref = db.collection('templates').document('template_exam_rise_2027').collection('versions').document('v1.0.0')
version_ref.set({
    "version": "v1.0.0",
    "status": "APPROVED",
    "configuration": template_config,
    "commitMessage": "Approved Classes 1-9 Subject Configuration (No Telugu/Hindi)",
    "updatedAt": firestore.SERVER_TIMESTAMP,
    "approvedAt": firestore.SERVER_TIMESTAMP
}, merge=True)
print("[3/4] Updated template_exam_rise_2027 version v1.0.0 in Firestore.")

# Update active_batch.json for Class 8
active_batch_data = {
    "batchId": "BATCH_RISE_2027_PRACTICAL",
    "examId": "exam_rise_2027",
    "classId": "8",
    "paperSet": "A",
    "templateId": "template_exam_rise_2027",
    "templateVersionId": "v1.0.0",
    "template_config": dict(template_config, sections=c6_9_sections)
}
with open('OMR_SCAN/active_batch.json', 'w') as f:
    json.dump(active_batch_data, f, indent=2)
print("[4/4] Updated OMR_SCAN/active_batch.json for Class 8.")

# ============================================================
# 3. VERIFY ALL 9 CLASS CONFIGURATIONS
# ============================================================
print("\n--- VALIDATING ALL 9 CLASS CONFIGURATIONS ---")
for cls_num in range(1, 10):
    c_str = str(cls_num)
    c_conf = classes_config[c_str]
    sects = c_conf['sections']
    
    total_q = sum(s['question_count'] for s in sects)
    total_m = sum(s['allocated_marks'] for s in sects)
    sec_names = [s['name'] for s in sects]
    
    assert total_q == 50, f"Class {cls_num} total questions = {total_q}, expected 50"
    assert total_m == 50, f"Class {cls_num} total marks = {total_m}, expected 50"
    assert "TELUGU" not in sec_names, f"Telugu found in Class {cls_num}!"
    assert "HINDI" not in sec_names, f"Hindi found in Class {cls_num}!"
    
    # Check continuous numbering
    expected_start = 1
    for s in sects:
        q_start = s['question_numbering']['start']
        q_end = s['question_numbering']['end']
        q_cnt = s['question_count']
        assert q_start == expected_start, f"Class {cls_num} {s['name']} start={q_start}, expected {expected_start}"
        assert q_end == q_start + q_cnt - 1, f"Class {cls_num} {s['name']} end={q_end}, expected {q_start + q_cnt - 1}"
        expected_start = q_end + 1
    assert expected_start == 51, f"Class {cls_num} does not end at Q50 (ended at {expected_start - 1})"
    
    sec_summary = ", ".join(f"{s['name']} ({s['question_count']}Q: Q{s['question_numbering']['start']}-Q{s['question_numbering']['end']})" for s in sects)
    print(f"Class {cls_num}: VALID (50Q/50M) -> {sec_summary}")

print("\nSUCCESS: All 9 classes validated! No Telugu, No Hindi. Class 8 updated to Classes 6-9 distribution.")
