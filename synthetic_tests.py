import cv2
import pymupdf
import numpy as np
import os
from scanner_engine import ScannerEngine
from evaluation_engine import EvaluationEngine

def pdf_to_png(pdf_path, png_path, dpi=300):
    doc = pymupdf.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(png_path)
    return png_path

def generate_synthetic_image(base_png_path, out_png_path, answers_to_fill, scanner_engine, fill_ratio=1.0):
    """
    answers_to_fill: dict { q_num: option_index } e.g. { 1: 0 } for A
    fill_ratio: how dark/big to draw the circle. 1.0 is full, 0.5 is ambiguous.
    """
    img = cv2.imread(base_png_path)
    if img is None:
        raise ValueError(f"Could not load base image from {base_png_path}")
    
    for q_num, opt_idx in answers_to_fill.items():
        if q_num not in scanner_engine.engine.question_coordinates:
            continue
            
        data = scanner_engine.engine.question_coordinates[q_num]
        
        # If opt_idx is a list (multiple marks)
        if not isinstance(opt_idx, list):
            opt_idx = [opt_idx]
            
        for idx in opt_idx:
            bx, by, br = data['bubbles'][idx]
            px_x = scanner_engine._mm_to_px(bx)
            px_y = scanner_engine._mm_to_px(by)
            px_r = int(scanner_engine._mm_to_px(br) * fill_ratio)
            
            # Draw filled black circle
            cv2.circle(img, (px_x, px_y), px_r, (0,0,0), -1)
            
    cv2.imwrite(out_png_path, img)
    return out_png_path

def run_synthetic_tests():
    print("=== RUNNING HARDENING & SYNTHETIC TESTS ===")
    
    os.makedirs('output/synthetic', exist_ok=True)
    pdf_path = 'output/RISE_2027_OMR.pdf'
    base_png_path = 'output/synthetic/RISE_2027_base.png'
    
    from pdf_generator import PDFGenerator
    print("\n[0] Generating fresh PDF from config...")
    gen = PDFGenerator('rise_omr_template.json', pdf_path)
    gen.generate()
    
    print("\n[1] Rendering PDF to 300 DPI PNG...")
    pdf_to_png(pdf_path, base_png_path, dpi=300)
    
    scanner = ScannerEngine('rise_omr_template.json')
    eval_engine = EvaluationEngine('rise_omr_template.json')
    
    print("\n[2] Testing Registration Marks on Base PNG...")
    gray = scanner.load_image(base_png_path)
    marks = scanner.detect_registration_marks(gray)
    print("Detected marks:", marks)
    
    warped = scanner.warp_canonical(gray, marks)
    answers = scanner.extract_answers(warped)
    all_blank = all(a['classification'] == 'BLANK' for a in answers.values())
    if all_blank:
        print("PASS: Clean PNG recognized as 100% BLANK.")
    else:
        print("FAIL: Clean PNG has false positives.")
        
    print("\n[3] Building Synthetic Image 1: All A's (Perfect Marking)")
    img1_path = 'output/synthetic/test1_all_A.png'
    generate_synthetic_image(base_png_path, img1_path, {i: 0 for i in range(1, 51)}, scanner, fill_ratio=0.9)
    
    ans1 = scanner.extract_answers(scanner.warp_canonical(scanner.load_image(img1_path), scanner.detect_registration_marks(scanner.load_image(img1_path))))
    all_A = all(a['extracted'] == 'A' for a in ans1.values())
    if all_A:
        print("PASS: Synthetic 'All A' recognized correctly.")
    else:
        print("FAIL: Not all A's detected.")
        
    print("\n[4] Building Synthetic Image 2: Mixed (Correct, Wrong, Blank, Multiple, Ambiguous)")
    # Q1-10: A (Correct)
    # Q11-20: B (Wrong)
    # Q21-30: Blank
    # Q31-40: A and B (Multiple)
    # Q41-50: A but lightly shaded (Ambiguous)
    
    mixed_answers = {}
    for i in range(1, 11): mixed_answers[i] = 0
    for i in range(11, 21): mixed_answers[i] = 1
    # 21-30 blank
    for i in range(31, 41): mixed_answers[i] = [0, 1]
    
    img2_path = 'output/synthetic/test2_mixed.png'
    generate_synthetic_image(base_png_path, img2_path, mixed_answers, scanner, fill_ratio=0.9)
    
    # Add ambiguous lightly shaded bubbles for Q41-50 manually by using smaller fill_ratio
    generate_synthetic_image(img2_path, img2_path, {i: 0 for i in range(41, 51)}, scanner, fill_ratio=0.66)

    ans2 = scanner.extract_answers(scanner.warp_canonical(scanner.load_image(img2_path), scanner.detect_registration_marks(scanner.load_image(img2_path))))
    
    # Verify classifications
    c_valid = sum(1 for i in range(1, 11) if ans2[i]['classification'] == 'VALID')
    c_wrong = sum(1 for i in range(11, 21) if ans2[i]['classification'] == 'VALID')
    c_blank = sum(1 for i in range(21, 31) if ans2[i]['classification'] == 'BLANK')
    c_mult = sum(1 for i in range(31, 41) if ans2[i]['classification'] == 'MULTIPLE / INVALID')
    c_ambig = sum(1 for i in range(41, 51) if ans2[i]['classification'] == 'AMBIGUOUS')
    
    print(f"Verified: {c_valid} Valid/Correct, {c_wrong} Valid/Wrong, {c_blank} Blank, {c_mult} Multiple, {c_ambig} Ambiguous")
    if c_valid == 10 and c_wrong == 10 and c_blank == 10 and c_mult == 10 and c_ambig == 10:
        print("PASS: All classifications matched exactly.")
    else:
        print("FAIL: Classification mismatch.")
        
    print("\n[5] Testing Evaluation Engine on Synthetic Mixed Output...")
    key = {i: 'A' for i in range(1, 51)} # Key is all A's
    res = eval_engine.evaluate(ans2, key)
    print("Correct (10):", res['correct_count'])
    print("Wrong (20 = 10 explicitly wrong + 10 multiple):", res['wrong_count'])
    print("Unanswered (10):", res['unanswered_count'])
    print("Ambiguous (10):", res['ambiguous_count'])
    print(f"Total Score: {res['total_score']:.2f}")

if __name__ == "__main__":
    run_synthetic_tests()
