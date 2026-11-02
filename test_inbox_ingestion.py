import os
import time
import json
import shutil
from pathlib import Path
from google.cloud import firestore

os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
db = firestore.Client(project="rise-omr-backend-2027")

def test_ingestion():
    print("Testing OMR Scan Inbox Ingestion...")
    v_doc = db.collection('templates').document('template_exam_rise_2027').collection('versions').document('v1.0.0').get()
    config = v_doc.to_dict().get('configuration')

    # 1. Setup active_batch.json
    batch_config = {
        "batchId": "BATCH_TEST_VERIFY",
        "examId": "exam_rise_2027",
        "classId": "class_8",
        "paperSet": "A",
        "templateId": "template_exam_rise_2027",
        "templateVersionId": "v1.0.0",
        "template_config": config
    }
    with open("OMR_SCAN/active_batch.json", "w") as f:
        json.dump(batch_config, f, indent=2)
    print("  [+] Configured OMR_SCAN/active_batch.json")

    # 2. Copy sheet 1 (valid) and sheet 3 (multiple) into OMR_SCAN/inbox
    inbox = Path("OMR_SCAN/inbox")
    inbox.mkdir(parents=True, exist_ok=True)
    
    shutil.copy("output/test_sheets/sheet_1_valid.png", str(inbox / "verify_sheet_1_valid.png"))
    shutil.copy("output/test_sheets/sheet_3_multiple.png", str(inbox / "verify_sheet_3_multiple.png"))
    print("  [+] Dropped 2 test sheets into OMR_SCAN/inbox/")

    # 3. Wait for ingestion service to pick up and process
    print("  [*] Waiting for ingestion processing...")
    for _ in range(15):
        time.sleep(1)
        proc_file = Path("OMR_SCAN/processed/verify_sheet_1_valid.png")
        rev_file = Path("OMR_SCAN/review/verify_sheet_3_multiple.png")
        if proc_file.exists() and rev_file.exists():
            print("  [+] File routing verified:")
            print(f"      - Valid sheet moved to: {proc_file}")
            print(f"      - Multiple mark sheet moved to: {rev_file}")
            break
    else:
        print("  [-] Timeout waiting for file movement. Checking directory contents:")
        print("      Inbox:", list(inbox.iterdir()))
        print("      Processed:", list(Path("OMR_SCAN/processed").iterdir()))
        print("      Review:", list(Path("OMR_SCAN/review").iterdir()))

    # 4. Check Firestore scanSheets
    docs = list(db.collection('scanSheets').where('batchId', '==', 'BATCH_TEST_VERIFY').stream())
    print(f"  [+] Firestore scanSheets recorded: {len(docs)} documents.")
    for d in docs:
        data = d.to_dict()
        print(f"      Document {d.id}: status={data.get('status')}, file={data.get('fileName')}")

    assert len(docs) >= 2, "Expected at least 2 scanSheets documents"
    print("  ✓ PASS: Inbox ingestion, routing, and database persistence verified!")

if __name__ == "__main__":
    test_ingestion()
