import shutil
import time
from pathlib import Path

# Act as the Ricoh scanner copying a batch of files over SMB to the inbox
inbox_dir = Path("OMR_SCAN/inbox")
inbox_dir.mkdir(parents=True, exist_ok=True)

test_file = Path("test_marked2.png")

if not test_file.exists():
    print("test_marked2.png not found!")
    exit(1)

print("Simulating Ricoh LAN scan (5 files)...")
for i in range(5):
    dest = inbox_dir / f"scan_ricoh_{i}.png"
    shutil.copy(test_file, dest)
    print(f"-> Scanned sheet to {dest}")
    time.sleep(0.5)

print("Scan complete.")
