import requests
import json

# Define the payload simulating the FastAPI evaluation request
payload = {
    "examId": "rise_2027",
    "classId": "8",
    "paperSet": "A",
    "extracted_answers": {
        "1": "A", 
        "2": "B", 
        "3": "BLANK", 
        "4": "C"
    },
    "answer_key": {
        "1": "A", # Correct (+1)
        "2": "C", # Wrong (-0.33)
        "3": "A", # Unanswered (0)
        "4": "C"  # Correct (+1)
        # Total should be 1 + (-0.33) + 0 + 1 = 1.67 approx
    },
    "template_config": {
        "marking_engine_rule": {
            "correct": 1,
            "wrong": -0.3333,
            "unanswered": 0
        }
    }
}

try:
    print("Testing /api/evaluate endpoint...")
    response = requests.post("http://localhost:8000/api/evaluate", json=payload)
    if response.status_code == 200:
        data = response.json()
        print("Success! Results:")
        print(json.dumps(data, indent=2))
        
        # Verify correctness
        score = data.get("results", {}).get("total_score", 0)
        print(f"Calculated Score: {score}")
        
        expected = 1 - 0.3333 + 0 + 1
        print(f"Expected Score: {expected}")
        
        if abs(score - expected) < 0.01:
            print("EVALUATION PASS: Score matches expected rules.")
        else:
            print("EVALUATION FAIL: Score mismatch!")
    else:
        print(f"FAILED with status {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error testing evaluation: {e}")
