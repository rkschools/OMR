import json

class EvaluationEngine:
    def __init__(self, config_path=None, config_dict=None):
        if config_dict is not None:
            self.config = config_dict
        elif config_path is not None:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            
        self.rules = self.config.get("marking_engine_rule", {})
        self.correct_val = self.rules.get("correct", 1)
        self.wrong_group_size = self.rules.get("wrong_group_size", 3)
        self.wrong_group_penalty = self.rules.get("wrong_group_penalty", 1)
        self.unanswered_val = self.rules.get("unanswered", 0)
        self.wrong_val = self.rules.get("wrong", -1.0 / 3.0)

    def evaluate(self, extracted_answers, answer_key):
        """
        extracted_answers: dict { q_num: { 'extracted': 'A', 'classification': 'VALID' } }
        answer_key: dict { q_num: 'A' }
        """
        results = {
            'total_score': 0.0,
            'correct_count': 0,
            'wrong_count': 0,
            'unanswered_count': 0,
            'ambiguous_count': 0,
            'invalid_count': 0,
            'details': {}
        }
        
        for q_num, ans_data in extracted_answers.items():
            # Only evaluate actual questions (e.g. 1 to 50), skip metadata keys
            if not str(q_num).isdigit():
                continue
            correct_ans = answer_key.get(str(q_num))
            
            if isinstance(ans_data, dict):
                student_ans = ans_data.get('extracted', '')
                classification = ans_data.get('classification', '')
                if student_ans == 'BLANK' and not classification:
                    classification = 'BLANK'
            else:
                student_ans = str(ans_data)
                if student_ans == 'BLANK':
                    classification = 'BLANK'
                elif student_ans in ['MULTIPLE', 'AMBIGUOUS']:
                    classification = 'AMBIGUOUS'
                else:
                    classification = 'VALID'
            
            q_score = 0.0
            status = ""
            
            if classification == "AMBIGUOUS":
                results['ambiguous_count'] += 1
                status = "AMBIGUOUS"
            elif classification in ["MULTIPLE / INVALID", "INVALID"]:
                results['invalid_count'] += 1
                results['wrong_count'] += 1
                q_score = self.wrong_val
                status = "INVALID (WRONG)"
            elif classification == "BLANK":
                results['unanswered_count'] += 1
                q_score = self.unanswered_val
                status = "UNANSWERED"
            elif student_ans == correct_ans:
                results['correct_count'] += 1
                q_score = self.correct_val
                status = "CORRECT"
            else:
                results['wrong_count'] += 1
                q_score = self.wrong_val
                status = "WRONG"
                
            results['details'][q_num] = {
                'student_ans': student_ans,
                'correct_ans': correct_ans,
                'status': status,
                'score': q_score
            }
            
        # Exact marking formula: Score = Correct - (Wrong / 3.0)
        results['total_score'] = (results['correct_count'] * self.correct_val) - (results['wrong_count'] / 3.0)

        return results

if __name__ == "__main__":
    engine = EvaluationEngine('rise_omr_template.json')
    test_answers = {
        1: {'extracted': 'A', 'classification': 'VALID'},
        2: {'extracted': 'B', 'classification': 'VALID'},
        3: {'extracted': 'BLANK', 'classification': 'BLANK'},
        4: {'extracted': 'INVALID', 'classification': 'MULTIPLE / INVALID'}
    }
    test_key = {1: 'A', 2: 'C', 3: 'A', 4: 'B'}
    print("Evaluation Results:", engine.evaluate(test_answers, test_key))
