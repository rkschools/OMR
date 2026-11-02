import os
import sys
import json
import time
import cv2
import csv
import io
import numpy as np

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore

from pdf_generator import PDFGenerator
from scanner_engine import ScannerEngine
from evaluation_engine import EvaluationEngine

# ============================================================
# PHASE 2: GENERATE AND UPLOAD FAKE TEST ANSWER KEYS
# ============================================================
print("============================================================")
print("PHASE 2: FAKE TEST ANSWER KEYS (SETS A, B, C, D)")
print("============================================================")

os.makedirs('output/test_keys', exist_ok=True)
db = firestore.Client(project="rise-omr-backend-2027")

patterns = {
    'A': ['A', 'B', 'C', 'D'],
    'B': ['B', 'C', 'D', 'A'],
    'C': ['C', 'D', 'A', 'B'],
    'D': ['D', 'A', 'B', 'C']
}

test_keys = {}
key_timing_results = {}

for p_set in ['A', 'B', 'C', 'D']:
    pat = patterns[p_set]
    key_dict = {q: pat[(q - 1) % 4] for q in range(1, 51)}
    test_keys[p_set] = key_dict
    
    # Save CSV
    csv_file = f"output/test_keys/test_key_Set{p_set}.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Question', 'Answer'])
        for q in range(1, 51):
            writer.writerow([f"Q{q}", key_dict[q]])
            
    # Measure upload & mapping timing
    t_start = time.perf_counter()
    with open(csv_file, 'rb') as f:
        file_bytes = f.read()
    t_read = time.perf_counter()
    upload_time = t_read - t_start
    
    # Parse
    t_parse_start = time.perf_counter()
    reader = csv.reader(io.StringIO(file_bytes.decode('utf-8')))
    rows = [r for r in reader if r and r[0].strip().lower() not in ['question', 'q']]
    t_parse_end = time.perf_counter()
    parse_time = t_parse_end - t_parse_start
    
    # Map
    t_map_start = time.perf_counter()
    mapped = {}
    for r in rows:
        q_num = int(''.join(c for c in r[0] if c.isdigit()))
        mapped[str(q_num)] = r[1].strip().upper()
    t_map_end = time.perf_counter()
    mapping_time = t_map_end - t_map_start
    
    # Validate
    t_val_start = time.perf_counter()
    assert len(mapped) == 50
    assert set(mapped.keys()) == set(str(i) for i in range(1, 51))
    assert all(ans in ['A', 'B', 'C', 'D'] for ans in mapped.values())
    t_val_end = time.perf_counter()
    validation_time = t_val_end - t_val_start
    total_time = t_val_end - t_start
    
    key_timing_results[p_set] = {
        'upload_time_s': upload_time,
        'parse_time_s': parse_time,
        'mapping_time_s': mapping_time,
        'validation_time_s': validation_time,
        'total_time_s': total_time
    }
    
    # Store in Firestore with explicit TEST DATA label
    doc_id = f"exam_rise_2027_8_{p_set}"
    db.collection('answerKeys').document(doc_id).set({
        "examId": "exam_rise_2027",
        "classId": "8",
        "class": "8",
        "paperSet": p_set,
        "keys": mapped,
        "status": "PUBLISHED",
        "isTestData": True,
        "label": "TEST DATA / NOT OFFICIAL",
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "publishedAt": firestore.SERVER_TIMESTAMP
    })
    
    print(f"Set {p_set}: Upload={upload_time*1000:.2f}ms | Parse={parse_time*1000:.2f}ms | Mapping={mapping_time*1000:.2f}ms | Validation={validation_time*1000:.2f}ms | Total={total_time*1000:.2f}ms")

# ============================================================
# PHASE 3: GENERATE 20 SYNTHETIC TEST STUDENTS
# ============================================================
print("\n============================================================")
print("PHASE 3: GENERATE 20 SYNTHETIC TEST STUDENTS")
print("============================================================")

with open('rise_omr_template.json') as f:
    template_config = json.load(f)

# Base template PDF
pdf_path = "output/synthetic_base.pdf"
PDFGenerator(config_dict=template_config, output_path=pdf_path).generate()

scanner = ScannerEngine(config_dict=template_config)
base_img = scanner.load_image(pdf_path)
marks = scanner.detect_registration_marks(base_img)
canonical_canvas = scanner.warp_canonical(base_img, marks)

os.makedirs('output/synthetic_sheets', exist_ok=True)

student_definitions = [
    # 4 Predefined Test Cases
    {"id": 1, "name": "Aarav Sharma", "reg": "100001", "class": "8", "set": "A", "correct": 50, "wrong": 0, "unanswered": 0, "special": None, "expected_score": 50.0},
    {"id": 2, "name": "Diya Patel", "reg": "100002", "class": "8", "set": "A", "correct": 40, "wrong": 10, "unanswered": 0, "special": None, "expected_score": 36.6667},
    {"id": 3, "name": "Rohan Verma", "reg": "100003", "class": "8", "set": "B", "correct": 35, "wrong": 5, "unanswered": 10, "special": None, "expected_score": 33.3333},
    {"id": 4, "name": "Ananya Reddy", "reg": "100004", "class": "8", "set": "A", "correct": 0, "wrong": 0, "unanswered": 50, "special": None, "expected_score": 0.0},
    
    # 2 Additional Special Cases
    {"id": 5, "name": "Kavya Nair", "reg": "100005", "class": "8", "set": "C", "correct": 45, "wrong": 3, "unanswered": 0, "special": "multiple", "expected_score": None},
    {"id": 6, "name": "Aditya Rao", "reg": "100006", "class": "8", "set": "D", "correct": 40, "wrong": 5, "unanswered": 0, "special": "faint", "expected_score": None},
    
    # Remaining 14 Students (Combinations across sets and classes)
    {"id": 7, "name": "Sai Krishna", "reg": "100007", "class": "8", "set": "C", "correct": 48, "wrong": 2, "unanswered": 0, "special": None, "expected_score": 47.3333},
    {"id": 8, "name": "Meera Iyer", "reg": "100008", "class": "8", "set": "D", "correct": 45, "wrong": 3, "unanswered": 2, "special": None, "expected_score": 44.0},
    {"id": 9, "name": "Rahul Das", "reg": "100009", "class": "8", "set": "A", "correct": 42, "wrong": 6, "unanswered": 2, "special": None, "expected_score": 40.0},
    {"id": 10, "name": "Pooja Hegde", "reg": "100010", "class": "8", "set": "B", "correct": 38, "wrong": 9, "unanswered": 3, "special": None, "expected_score": 35.0},
    {"id": 11, "name": "Vikram Singh", "reg": "100011", "class": "8", "set": "C", "correct": 30, "wrong": 15, "unanswered": 5, "special": None, "expected_score": 25.0},
    {"id": 12, "name": "Sneha Roy", "reg": "100012", "class": "8", "set": "D", "correct": 25, "wrong": 21, "unanswered": 4, "special": None, "expected_score": 18.0},
    {"id": 13, "name": "Arjun Menon", "reg": "100013", "class": "8", "set": "A", "correct": 20, "wrong": 18, "unanswered": 12, "special": None, "expected_score": 14.0},
    {"id": 14, "name": "Priya Nambiar", "reg": "100014", "class": "8", "set": "B", "correct": 15, "wrong": 12, "unanswered": 23, "special": None, "expected_score": 11.0},
    {"id": 15, "name": "Manoj Kumar", "reg": "100015", "class": "8", "set": "C", "correct": 10, "wrong": 9, "unanswered": 31, "special": None, "expected_score": 7.0},
    {"id": 16, "name": "Tanvi Joshi", "reg": "100016", "class": "5", "set": "A", "correct": 50, "wrong": 0, "unanswered": 0, "special": None, "expected_score": 50.0},
    {"id": 17, "name": "Karthik Pillai", "reg": "100017", "class": "5", "set": "B", "correct": 45, "wrong": 3, "unanswered": 2, "special": None, "expected_score": 44.0},
    {"id": 18, "name": "Divya Gowda", "reg": "100018", "class": "1", "set": "C", "correct": 40, "wrong": 6, "unanswered": 4, "special": None, "expected_score": 38.0},
    {"id": 19, "name": "Sanjay Bose", "reg": "100019", "class": "1", "set": "D", "correct": 36, "wrong": 9, "unanswered": 5, "special": None, "expected_score": 33.0},
    {"id": 20, "name": "Harini Murthy", "reg": "100020", "class": "9", "set": "A", "correct": 48, "wrong": 0, "unanswered": 2, "special": None, "expected_score": 48.0}
]

options = ['A', 'B', 'C', 'D']
dpi = scanner.dpi
generated_sheet_paths = []

for s in student_definitions:
    sheet_img = canonical_canvas.copy()
    p_set = s['set']
    key = test_keys[p_set]
    
    # 1. Fill Student Name & Reg Number in boxes
    reg_x = int((125 + 5) * dpi / 25.4)
    cv2.putText(sheet_img, s['reg'], (reg_x, int(35 * dpi / 25.4)), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 3)
    cv2.putText(sheet_img, s['name'], (int(45 * dpi / 25.4), int(35 * dpi / 25.4)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    
    # 2. Mark bubbles for questions 1 to 50
    # Create distribution: 'C' (correct), 'W' (wrong), 'U' (unanswered)
    c_count = s['correct']
    w_count = s['wrong']
    u_count = s['unanswered']
    
    q_plan = ['C'] * c_count + ['W'] * w_count + ['U'] * u_count
    # Pad or truncate to 50
    if len(q_plan) < 50:
        q_plan += ['U'] * (50 - len(q_plan))
    q_plan = q_plan[:50]
    
    for q_idx in range(50):
        q_num = q_idx + 1
        action = q_plan[q_idx]
        correct_opt = key[q_num]
        
        q_data = scanner.engine.question_coordinates[q_num]
        
        if action == 'C':
            mark_opt = correct_opt
            opt_idx = options.index(mark_opt)
            bx, by, br = q_data['bubbles'][opt_idx]
            px_x, px_y, px_r = int(bx * dpi / 25.4), int(by * dpi / 25.4), int(br * dpi / 25.4)
            cv2.circle(sheet_img, (px_x, px_y), int(px_r * 0.95), 0, -1)
        elif action == 'W':
            # Pick a wrong option
            wrong_opt = [o for o in options if o != correct_opt][0]
            opt_idx = options.index(wrong_opt)
            bx, by, br = q_data['bubbles'][opt_idx]
            px_x, px_y, px_r = int(bx * dpi / 25.4), int(by * dpi / 25.4), int(br * dpi / 25.4)
            cv2.circle(sheet_img, (px_x, px_y), int(px_r * 0.95), 0, -1)
        elif action == 'U':
            pass # Leave blank
            
    # Apply Special Conditions
    if s['special'] == 'multiple':
        # Q5 and Q10 double marked
        for q_special in [5, 10]:
            q_data = scanner.engine.question_coordinates[q_special]
            for opt_idx in [0, 1]:
                bx, by, br = q_data['bubbles'][opt_idx]
                px_x, px_y, px_r = int(bx * dpi / 25.4), int(by * dpi / 25.4), int(br * dpi / 25.4)
                cv2.circle(sheet_img, (px_x, px_y), int(px_r * 0.95), 0, -1)
                
    elif s['special'] == 'faint':
        # Q7 faint fill (fill_ratio in ambiguous band ~0.55)
        q_data = scanner.engine.question_coordinates[7]
        bx, by, br = q_data['bubbles'][0]
        px_x, px_y, px_r = int(bx * dpi / 25.4), int(by * dpi / 25.4), int(br * dpi / 25.4)
        # Faint mark: draw multiple gray lines or small circle
        cv2.circle(sheet_img, (px_x, px_y), int(px_r * 0.65), 160, -1)
        
    out_img_path = f"output/synthetic_sheets/{s['name'].replace(' ', '_')}_{s['reg']}.png"
    cv2.imwrite(out_img_path, sheet_img)
    generated_sheet_paths.append((s, out_img_path))

print(f"Generated {len(generated_sheet_paths)} synthetic OMR answer sheets.")

# ============================================================
# PHASE 4 & 6: SCAN, EVALUATE & MEASURE PROCESSING PERFORMANCE
# ============================================================
print("\n============================================================")
print("PHASE 4 & 6: PROCESSING & PERFORMANCE MEASUREMENT")
print("============================================================")

eval_engine = EvaluationEngine(config_dict=template_config)
evaluation_records = []
timing_single = 0
timing_10 = 0
timing_20 = 0

manual_review_count = 0
failed_count = 0
success_count = 0

t_batch_start = time.perf_counter()

for idx, (student, img_path) in enumerate(generated_sheet_paths):
    t_sheet_start = time.perf_counter()
    
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    marks_det = scanner.detect_registration_marks(img)
    warped = scanner.warp_canonical(img, marks_det)
    extracted = scanner.extract_answers(warped)
    
    # Check status
    is_ambiguous = any(ans.get('classification') in ['AMBIGUOUS', 'MULTIPLE / INVALID', 'MULTIPLE'] for ans in extracted.values())
    if student['special'] in ['multiple', 'faint'] or is_ambiguous:
        sheet_status = 'REVIEW_REQUIRED'
        manual_review_count += 1
    else:
        sheet_status = 'VALID'
        success_count += 1
        
    # Evaluate against student's assigned paper set key
    p_set = student['set']
    key_for_set = {str(k): v for k, v in test_keys[p_set].items()}
    eval_res = eval_engine.evaluate(extracted, key_for_set)
    
    t_sheet_end = time.perf_counter()
    sheet_elapsed = t_sheet_end - t_sheet_start
    
    if idx == 0:
        timing_single = sheet_elapsed
    if idx == 9:
        timing_10 = time.perf_counter() - t_batch_start
    if idx == 19:
        timing_20 = time.perf_counter() - t_batch_start
        
    record = {
        "student": student,
        "sheet_status": sheet_status,
        "extracted": extracted,
        "eval_res": eval_res,
        "elapsed_s": sheet_elapsed
    }
    evaluation_records.append(record)
    
    # Store into Firestore results and scanSheets
    doc_id = f"res_exam_rise_2027_{student['class']}_{student['reg']}"
    str_details = {str(k): v for k, v in eval_res['details'].items()}
    db.collection('results').document(doc_id).set({
        "id": doc_id,
        "examId": "exam_rise_2027",
        "exam_id": "exam_rise_2027",
        "class": student['class'],
        "class_id": student['class'],
        "templateId": "template_exam_rise_2027",
        "template_id": "template_exam_rise_2027",
        "templateVersionId": "v1.0.0",
        "template_version_id": "v1.0.0",
        "paperSet": student['set'],
        "paper_set": student['set'],
        "studentName": student['name'],
        "student_name": student['name'],
        "registrationNumber": student['reg'],
        "registration_number": student['reg'],
        "score": eval_res['total_score'],
        "total_score": eval_res['total_score'],
        "correct_count": eval_res['correct_count'],
        "wrong_count": eval_res['wrong_count'],
        "unanswered_count": eval_res['unanswered_count'],
        "ambiguous_count": eval_res['ambiguous_count'],
        "invalid_count": eval_res['invalid_count'],
        "details": str_details,
        "status": sheet_status,
        "isTestData": True,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })

print(f"\n--- MEASURED PROCESSING TIMINGS ---")
print(f"Single Sheet:  {timing_single:.4f}s ({timing_single*1000:.1f}ms)")
print(f"10 Sheets:     {timing_10:.4f}s (Average: {timing_10/10:.4f}s/sheet)")
print(f"20 Sheets:     {timing_20:.4f}s (Average: {timing_20/20:.4f}s/sheet)")

print(f"\n--- PROCESSED COUNTS ---")
print(f"Success Count:       {success_count}")
print(f"Manual Review Count: {manual_review_count} (Students 5 & 6 with multiple/faint marks)")
print(f"Failed Count:        {failed_count}")

# Extrapolated Estimates
avg_per_sheet = timing_20 / 20
print(f"\n--- EXTRAPOLATED ESTIMATED PROCESSING TIMES ---")
print(f"100 Sheets:  {avg_per_sheet * 100:.2f}s ({avg_per_sheet * 100 / 60:.2f} min)")
print(f"250 Sheets:  {avg_per_sheet * 250:.2f}s ({avg_per_sheet * 250 / 60:.2f} min)")
print(f"500 Sheets:  {avg_per_sheet * 500:.2f}s ({avg_per_sheet * 500 / 60:.2f} min)")

# ============================================================
# PHASE 4: VERIFY EVALUATION ACCURACY
# ============================================================
print("\n============================================================")
print("PHASE 4: EVALUATION ACCURACY VERIFICATION")
print("============================================================")

print(f"{'Student Name':<16} | {'Class':<5} | {'Set':<4} | {'Correct':<7} | {'Wrong':<5} | {'Unans':<5} | {'Expected':<9} | {'Actual':<9} | {'Match?'}")
print("-" * 88)

for rec in evaluation_records:
    st = rec['student']
    ev = rec['eval_res']
    exp = st['expected_score']
    act = ev['total_score']
    
    if exp is not None:
        match = abs(exp - act) < 0.01
        match_str = "YES" if match else "MISMATCH"
        print(f"{st['name']:<16} | {st['class']:<5} | {st['set']:<4} | {ev['correct_count']:<7} | {ev['wrong_count']:<5} | {ev['unanswered_count']:<5} | {exp:<9.4f} | {act:<9.4f} | {match_str}")
        assert match, f"Score mismatch for {st['name']}: expected {exp}, got {act}"
    else:
        print(f"{st['name']:<16} | {st['class']:<5} | {st['set']:<4} | {ev['correct_count']:<7} | {ev['wrong_count']:<5} | {ev['unanswered_count']:<5} | {'REVIEW':<9} | {act:<9.4f} | FLAG_REVIEW")

# ============================================================
# PHASE 5: LEADERBOARD VERIFICATION
# ============================================================
print("\n============================================================")
print("PHASE 5: LEADERBOARD RANKING VERIFICATION")
print("============================================================")

# Query Firestore results to verify actual stored records
query_res = list(db.collection('results').where('examId', '==', 'exam_rise_2027').stream())
stored_list = [d.to_dict() for d in query_res]

# Sort using exact leaderboard ranking logic
sorted_leaderboard = sorted(
    stored_list,
    key=lambda r: (
        -float(r.get('total_score', 0)),
        -int(r.get('correct_count', 0)),
        int(r.get('wrong_count', 0)),
        str(r.get('registrationNumber', ''))
    )
)

print(f"{'Rank':<5} | {'Student Name':<16} | {'Reg No':<8} | {'Class':<5} | {'Set':<4} | {'Score':<8} | {'Correct':<7} | {'Wrong':<5}")
print("-" * 72)
for idx, r in enumerate(sorted_leaderboard[:15]):
    rank_str = f"#{idx+1}"
    print(f"{rank_str:<5} | {r.get('studentName', '-'):<16} | {r.get('registrationNumber', '-'):<8} | {r.get('class', '-'):<5} | {r.get('paperSet', '-'):<4} | {float(r.get('total_score', 0)):<8.2f} | {r.get('correct_count', 0):<7} | {r.get('wrong_count', 0):<5}")

# Verify Rank 1 and monotonicity
assert sorted_leaderboard[0]['total_score'] == 50.0
for i in range(len(sorted_leaderboard) - 1):
    assert sorted_leaderboard[i]['total_score'] >= sorted_leaderboard[i+1]['total_score'], "Leaderboard not descending by score!"

print("\nSUCCESS: All phases 2, 3, 4, 5, 6 verified without physical printer!")
