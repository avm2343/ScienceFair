import time
import numpy as np
import json

class EpistemicGuardian:
    def __init__(self):
        # Behavioral weights
        self.weights = {'w1': 0.5, 'w2': 0.3, 'w3': 0.2}
        self.nudge_threshold = 0.5  # Delta C threshold
        
        # Personal Baseline (Learned in Phase 1)
        self.personal_stats = {
            'latency': [],
            'velocity': [],
            'revisions': []
        }
        
        # Analytics Data
        self.control_results = []
        self.experimental_results = []
        self.nudges_triggered = 0
        self.corrections = 0

    def calculate_z_score(self, value, history):
        if len(history) < 2: return 0
        mean = np.mean(history)
        std = np.std(history)
        return (value - mean) / (std if std > 0 else 1)

    def get_user_input(self, question_text):
        print(f"\nQUESTION: {question_text}")
        start_time = time.time()
        
        # In a console app, we simulate 'revisions' by asking the user 
        # or measuring input length changes. For this version, enter 
        # your answer, then how many times you hesitated/deleted.
        answer = input("Your Answer: ")
        end_time = time.time()
        
        try:
            revs = int(input("How many times did you backspace/retype? "))
        except:
            revs = 0
            
        latency = end_time - start_time
        velocity = len(answer) / latency if latency > 0 else 0
        
        return answer, latency, velocity, revs

    def run_phase(self, questions, mode="control"):
        print(f"\n{'='*20}\nSTARTING {mode.upper()} PHASE\n{'='*20}")
        
        for q in questions:
            ans, lat, vel, rev = self.get_user_input(q['text'])
            
            # 1. Calculate BCI based on Personal Differences (Z-scores)
            # We use Phase 1 history to judge Phase 2 behavior
            z_lat = self.calculate_z_score(1/lat if lat > 0 else 0, 
                                          [1/l for l in self.personal_stats['latency']] if self.personal_stats['latency'] else [0.2])
            z_vel = self.calculate_z_score(vel, self.personal_stats['velocity'])
            z_rev = self.calculate_z_score(rev, self.personal_stats['revisions'])
            
            # Sigmoid used to squash Z-scores into 0-1 probability (BCI)
            bci = 1 / (1 + np.exp(-( (self.weights['w1'] * z_lat) + 
                                     (self.weights['w2'] * z_vel) - 
                                     (self.weights['w3'] * z_rev) )))
            
            delta_c = bci - q['p_obj']
            is_correct = 1 if ans.strip().lower() == q['correct'].lower() else 0
            
            # 2. Experimental Logic: The Nudge
            if mode == "experimental" and delta_c > self.nudge_threshold and q['p_obj'] < 0.4:
                self.nudges_triggered += 1
                print("\n⚠️ [SYSTEM ALERT]: High Calibration Delta Detected.")
                print("Behavior suggests overconfidence on a high-difficulty task.")
                print("--- PAUSE: 3 SECOND COGNITIVE FRICTION ---")
                time.sleep(3)
                
                new_ans = input("Review your logic. Final Answer: ")
                if new_ans.strip().lower() == q['correct'].lower() and is_correct == 0:
                    self.corrections += 1
                is_correct = 1 if new_ans.strip().lower() == q['correct'].lower() else 0

            # 3. Store Data
            res = {'bci': bci, 'outcome': is_correct, 'is_trap': q['p_obj'] < 0.4}
            if mode == "control":
                self.control_results.append(res)
                # Build the personal profile
                self.personal_stats['latency'].append(lat)
                self.personal_stats['velocity'].append(vel)
                self.personal_stats['revisions'].append(rev)
            else:
                self.experimental_results.append(res)

    def show_metrics(self):
        print(f"\n{'='*20}\nISEF PROJECT EVALUATION\n{'='*20}")
        
        def brier(results):
            return np.mean([(r['bci'] - r['outcome'])**2 for r in results])
        
        bs_control = brier(self.control_results)
        bs_exp = brier(self.experimental_results)
        
        err_control = 1 - np.mean([r['outcome'] for r in self.control_results if r['is_trap']])
        err_exp = 1 - np.mean([r['outcome'] for r in self.experimental_results if r['is_trap']])
        err_reduction = ((err_control - err_exp) / err_control) * 100 if err_control > 0 else 0
        
        efficiency = self.corrections / self.nudges_triggered if self.nudges_triggered > 0 else 0

        print(f"1. Brier Score (Control): {bs_control:.4f}")
        print(f"2. Brier Score (Experimental): {bs_exp:.4f}")
        print(f"3. Error Reduction Rate: {err_reduction:.1f}%")
        print(f"4. Nudge Efficiency (η): {efficiency:.2f}")

# --- Questions ---
# p_obj is established from previous general population data (standard for ISEF)
control_qs = [
    {"text": "A bat and ball cost $1.10. The bat costs $1 more. Cost of ball?", "correct": "0.05", "p_obj": 0.15},
    {"text": "Square root of 144?", "correct": "12", "p_obj": 0.90}
]

experimental_qs = [
    {"text": "If 5 machines make 5 widgets in 5 mins, how long for 100 machines for 100?", "correct": "5", "p_obj": 0.20},
    {"text": "Capital of France?", "correct": "paris", "p_obj": 0.95}
]

# Run Simulation
guardian = EpistemicGuardian()
guardian.run_phase(control_qs, mode="control")
guardian.run_phase(experimental_qs, mode="experimental")
guardian.show_metrics()