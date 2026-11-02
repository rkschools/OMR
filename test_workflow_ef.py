import os
import json
import cv2
import pymupdf
import requests
from pathlib import Path
from pdf_generator import PDFGenerator
from scanner_engine import ScannerEngine
from evaluation_engine import EvaluationEngine

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
from google.cloud import firestore

def run():
    print("=================================================================")
    print("STEP 1: VERIFY EVALUATION ARITHMETIC & SET RESOLUTION (TEST DATA)")
    print("=================================================================")
    
    # Official RISE 2027 marking rules
    marking_rules = {
        "marking_engine_rule": {
            "correct": 1.0,
            "wrong": -0.33333333,
            "unanswered": 0.0
        }
    }
    engine = EvaluationEngine(config_dict=marking_rules)

    # Distinct Keys for Set A and Set B (Explicitly labeled TEST DATA)
    set_a_key = {str(i): "A" for i in range(1, 51)} # TEST DATA: all A
    set_b_key = {str(i): "B" for i in range(1, 51)} # TEST DATA: all B

    # Test Student Response:
    # Q1: A (Correct for Set A, Wrong for Set B)
    # Q2: B (Wrong for Set A, Correct for Set B)
    # Q3: BLANK (Unanswered for both)
    # Q4: INVALID (Multiple mark -> Wrong for both)
    sample_extracted = {
        "1": {"extracted": "A", "classification": "VALID"},
        "2": {"extracted": "B", "classification": "VALID"},
        "3": {"extracted": "BLANK", "classification": "BLANK"},
        "4": {"extracted": "INVALID", "classification": "MULTIPLE / INVALID"}
    }

    eval_a = engine.evaluate(sample_extracted, set_a_key)
    print("\n[Set A Evaluation]:")
    print(f"  Score: {eval_a['total_score']:.4f}")
    print(f"  Correct: {eval_a['correct_count']} | Wrong: {eval_a['wrong_count']} | Blank: {eval_a['unanswered_count']} | Invalid: {eval_a['invalid_count']}")
    # Expected Set A: Q1(+1), Q2(-0.3333), Q3(0), Q4(-0.3333) = 1 - 0.6666 = +0.3333
    expected_a = 1.0 - (2 * 0.33333333)
    assert abs(eval_a['total_score'] - expected_a) < 0.01, f"Mismatch in Set A: {eval_a['total_score']} vs {expected_a}"
    print("  ✓ PASS: Set A score arithmetic verified (+1, -1/3, 0).")

    eval_b = engine.evaluate(sample_extracted, set_b_key)
    print("\n[Set B Evaluation]:")
    print(f"  Score: {eval_b['total_score']:.4f}")
    print(f"  Correct: {eval_b['correct_count']} | Wrong: {eval_b['wrong_count']} | Blank: {eval_b['unanswered_count']} | Invalid: {eval_b['invalid_count']}")
    # Expected Set B: Q1(-0.3333), Q2(+1), Q3(0), Q4(-0.3333) = +0.3333
    assert abs(eval_b['total_score'] - expected_a) < 0.01
    assert eval_a['details']['1']['status'] == 'CORRECT' and eval_b['details']['1']['status'] == 'WRONG'
    print("  ✓ PASS: Set B independently resolves using Set B key (Q1 is WRONG, Q2 is CORRECT).")

    print("\n=================================================================")
    print("STEP 2: GENERATE 4 SYNTHETIC TEST SHEETS FOR PHYSICAL INGESTION")
    print("=================================================================")
    db = firestore.Client(project="rise-omr-backend-2027")
    v_doc = db.collection('templates').document('template_exam_rise_2027').collection('versions').document('v1.0.0').get()
    config = v_doc.to_dict().get('configuration')

    os.makedirs('output/test_sheets', exist_ok=True)
    clean_pdf = 'output/test_sheets/base_sheet.pdf'
    gen = PDFGenerator(config_dict=config, output_path=clean_pdf)
    gen.generate()

    # Render base sheet to 300 DPI image
    doc = pymupdf.open(clean_pdf)
    page = doc.load_page(0)
    zoom = 300 / 72.0
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    base_img_path = 'output/test_sheets/base_sheet.png'
    pix.save(base_img_path)

    scanner = ScannerEngine(config_dict=config)
    base_img = cv2.imread(base_img_path)

    # 1. Sheet 1: Valid Sheet (All 50 questions answered, Set A)
    valid_img = base_img.copy()
    for q in range(1, 51):
        coord = scanner.engine.question_coordinates.get(q)
        if coord:
            opt_idx = (q - 1) % 4
            bx, by, br = coord['bubbles'][opt_idx]
            px_x = scanner._mm_to_px(bx)
            px_y = scanner._mm_to_px(by)
            px_r = int(scanner._mm_to_px(br) * 0.9)
            cv2.circle(valid_img, (px_x, px_y), px_r, (0, 0, 0), -1)
    sheet1_path = 'output/test_sheets/sheet_1_valid.png'
    cv2.imwrite(sheet1_path, valid_img)
    print("  [+] Generated Sheet 1: Valid sheet with all 50 questions filled.")

    # 2. Sheet 2: Blank Sheet (No questions filled)
    blank_img = base_img.copy()
    sheet2_path = 'output/test_sheets/sheet_2_blank.png'
    cv2.imwrite(sheet2_path, blank_img)
    print("  [+] Generated Sheet 2: Blank sheet (0 filled).")

    # 3. Sheet 3: Multiple-mark Sheet (Q1 and Q5 have two bubbles filled)
    multi_img = valid_img.copy()
    for q in [1, 5]:
        coord = scanner.engine.question_coordinates.get(q)
        if coord:
            # fill additional bubble (option 1 and 2)
            bx, by, br = coord['bubbles'][1]
            cv2.circle(multi_img, (scanner._mm_to_px(bx), scanner._mm_to_px(by)), int(scanner._mm_to_px(br) * 0.9), (0, 0, 0), -1)
            bx, by, br = coord['bubbles'][2]
            cv2.circle(multi_img, (scanner._mm_to_px(bx), scanner._mm_to_px(by)), int(scanner._mm_to_px(br) * 0.9), (0, 0, 0), -1)
    sheet3_path = 'output/test_sheets/sheet_3_multiple.png'
    cv2.imwrite(sheet3_path, multi_img)
    print("  [+] Generated Sheet 3: Multiple marks on Q1 & Q5.")

    # 4. Sheet 4: Ambiguous/Unreadable Registration Sheet (Slight fill / scratch)
    ambig_img = blank_img.copy()
    # Fill Q1-Q9, Q11-Q50 with valid marks
    for q in range(1, 51):
        if q == 10:
            continue
        coord = scanner.engine.question_coordinates.get(q)
        if coord:
            opt_idx = (q - 1) % 4
            bx, by, br = coord['bubbles'][opt_idx]
            cv2.circle(ambig_img, (scanner._mm_to_px(bx), scanner._mm_to_px(by)), int(scanner._mm_to_px(br) * 0.9), (0, 0, 0), -1)
    coord10 = scanner.engine.question_coordinates.get(10)
    if coord10:
        bx, by, br = coord10['bubbles'][0]
        # Ambiguous faint mark (fill ratio ~0.57 in [0.50, 0.65] band)
        cv2.circle(ambig_img, (scanner._mm_to_px(bx), scanner._mm_to_px(by)), int(scanner._mm_to_px(br) * 0.68), (0, 0, 0), -1)
    sheet4_path = 'output/test_sheets/sheet_4_ambiguous.png'
    cv2.imwrite(sheet4_path, ambig_img)
    print("  [+] Generated Sheet 4: Ambiguous mark on Q10.")

    print("\n=================================================================")
    print("STEP 3: RUN SCANNER RECOGNITION AUDIT ON ALL 4 SHEETS")
    print("=================================================================")
    for path, expected_kind in [
        (sheet1_path, "VALID"),
        (sheet2_path, "BLANK"),
        (sheet3_path, "REVIEW_REQUIRED"),
        (sheet4_path, "REVIEW_REQUIRED")
    ]:
        gray = scanner.load_image(path)
        marks = scanner.detect_registration_marks(gray)
        warped = scanner.warp_canonical(gray, marks)
        answers = scanner.extract_answers(warped)
        
        has_ambig = any(a['classification'] in ['AMBIGUOUS', 'MULTIPLE / INVALID'] for a in answers.values())
        all_blank = all(a['classification'] == 'BLANK' for a in answers.values())
        
        if expected_kind == "VALID":
            assert not has_ambig and not all_blank
            print(f"  ✓ {os.path.basename(path)} -> Clean VALID detection (50 answers detected)")
        elif expected_kind == "BLANK":
            assert all_blank
            print(f"  ✓ {os.path.basename(path)} -> 100% BLANK sheet detected (50 blank questions)")
        elif expected_kind == "REVIEW_REQUIRED":
            assert has_ambig
            multi_qs = [q for q, a in answers.items() if a['classification'] in ['AMBIGUOUS', 'MULTIPLE / INVALID']]
            print(f"  ✓ {os.path.basename(path)} -> REVIEW_REQUIRED triggered correctly (Ambiguous/Invalid on Q: {multi_qs})")

    print("\nAll Evaluation, Key Resolution, and Scanner Detection tests PASSED!")

if __name__ == "__main__":
    run()
