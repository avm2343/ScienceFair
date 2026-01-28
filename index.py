import time
import math
import sys

# Terminal Raw Input Handler
try:
    import tty, termios
    def get_key():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
except ImportError:
    import msvcrt
    def get_key():
        return msvcrt.getch().decode('utf-8')

class EpistemicGuardian:
    def __init__(self):
        # Sensitivity settings
        self.weights = {'w1': 0.6, 'w2': 0.2, 'w3': 0.2} 
        self.nudge_threshold = 0.35 
        
        self.personal_stats = {'latency': [], 'velocity': [], 'revisions': []}
        self.results_control = []
        self.results_exp = []
        self.nudges_triggered = 0
        self.corrections = 0

    def calculate_z_score(self, value, history):
        if len(history) < 3: return 0 # Need more data for a real Z-score
        mean = sum(history) / len(history)
        var = sum((x - mean) ** 2 for x in history) / len(history)
        std = math.sqrt(var)
        return (value - mean) / (std if std > 0.001 else 1)

    def tracked_input(self):
        chars = []
        keystrokes = 0
        revisions = 0
        start_time = time.time()
        first_key_time = None
        while True:
            char = get_key()
            if not first_key_time: first_key_time = time.time()
            if char in ('\r', '\n'):
                sys.stdout.write('\n')
                break
            elif char in ('\x7f', '\x08'):
                if len(chars) > 0:
                    chars.pop()
                    revisions += 1
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            else:
                chars.append(char)
                keystrokes += 1
                sys.stdout.write(char)
                sys.stdout.flush()
        
        end_time = time.time()
        total_time = end_time - start_time
        latency = (first_key_time - start_time) if first_key_time else total_time
        velocity = keystrokes / total_time if total_time > 0 else 0
        return "".join(chars).strip().lower(), latency, velocity, revisions

    def run_phase(self, questions, mode):
        print(f"\n{'='*50}\nPHASE: {mode.upper()}\n{'='*50}")
        for i, q in enumerate(questions):
            print(f"\nQ{i+1}: {q['text']}")
            ans, lat, vel, rev = self.tracked_input()

            # Using 1/lat because higher speed (lower latency) indicates higher confidence
            inv_lat_hist = [1/l for l in self.personal_stats['latency']] if self.personal_stats['latency'] else []
            z_lat = self.calculate_z_score(1/lat if lat > 0 else 0, inv_lat_hist)
            z_vel = self.calculate_z_score(vel, self.personal_stats['velocity'])
            z_rev = self.calculate_z_score(rev, self.personal_stats['revisions'])

            # BCI Formula
            raw_bci = (self.weights['w1'] * z_lat) + (self.weights['w2'] * z_vel) - (self.weights['w3'] * z_rev)
            bci = 1 / (1 + math.exp(-raw_bci))
            delta_c = bci - q['p_obj']
            is_correct = 1 if any(ext in ans for ext in q['correct_keywords']) else 0

            print(f"--- DEBUG: BCI: {bci:.2f} | P_obj: {q['p_obj']:.2f} | Delta_C: {delta_c:.2f} ---")

            if mode == "experimental" and delta_c > self.nudge_threshold:
                self.nudges_triggered += 1
                print("\n⚠️  [COGNITIVE NUDGE]: Behavioral anomaly detected.")
                time.sleep(3)
                print("PAUSE ENGAGED. Re-type your final answer:")
                final_ans, _, _, _ = self.tracked_input()
                if any(ext in final_ans for ext in q['correct_keywords']) and is_correct == 0:
                    self.corrections += 1
                is_correct = 1 if any(ext in final_ans for ext in q['correct_keywords']) else 0

            entry = {'bci': bci, 'outcome': is_correct, 'is_trap': q['p_obj'] < 0.4}
            if mode == "control": self.results_control.append(entry)
            elif mode == "experimental": self.results_exp.append(entry)
            
            # Always feed the baseline
            self.personal_stats['latency'].append(lat)
            self.personal_stats['velocity'].append(vel)
            self.personal_stats['revisions'].append(rev)

    def print_final_report(self):
        print(f"\n{'='*50}\nFINAL PERFORMANCE REPORT\n{'='*50}")
        def get_acc(res_list):
            traps = [r['outcome'] for r in res_list if r['is_trap']]
            return sum(traps) / len(traps) if traps else 0
        def brier(res_list):
            return sum((r['bci'] - r['outcome'])**2 for r in res_list) / len(res_list) if res_list else 0

        print(f"Brier Score (Control): {brier(self.results_control):.4f}")
        print(f"Brier Score (Exp):     {brier(self.results_exp):.4f}")
        print(f"Trap Accuracy (Control): {get_acc(self.results_control)*100:.1f}%")
        print(f"Trap Accuracy (Exp):     {get_acc(self.results_exp)*100:.1f}%")
        eta = self.corrections / self.nudges_triggered if self.nudges_triggered > 0 else 0
        print(f"Nudge Efficiency (η): {eta:.2f}")

# --- 10-QUESTION CALIBRATION (Varying speeds) ---
calibration_qs = [
    {"text": "What is 10 + 10?", "correct_keywords": ["20"], "p_obj": 0.99},
    {"text": "What is the opposite of 'up'?", "correct_keywords": ["down"], "p_obj": 0.99},
    {"text": "Name a fruit that is typically red.", "correct_keywords": ["apple", "strawberry", "cherry"], "p_obj": 0.95},
    {"text": "How many legs does a dog have?", "correct_keywords": ["4", "four"], "p_obj": 0.99},
    {"text": "What is 5 x 5?", "correct_keywords": ["25"], "p_obj": 0.95},
    {"text": "What do you use to cut paper?", "correct_keywords": ["scissors"], "p_obj": 0.95},
    {"text": "What is the capital of the USA?", "correct_keywords": ["washington"], "p_obj": 0.90},
    {"text": "What is the frozen form of water?", "correct_keywords": ["ice"], "p_obj": 0.98},
    {"text": "Which season comes after Winter?", "correct_keywords": ["spring"], "p_obj": 0.95},
    {"text": "What is the color of a lemon?", "correct_keywords": ["yellow"], "p_obj": 0.99},
]

# --- CONTROL PHASE (Traps included) ---
control_qs = [
    {"text": "A bat and ball cost $1.10. The bat is $1 more. Ball cost in cents?", "correct_keywords": ["5", "five"], "p_obj": 0.15},
    {"text": "Emily's father has 3 daughters: April, May, and...?", "correct_keywords": ["emily"], "p_obj": 0.25},
    {"text": "How many months have 28 days?", "correct_keywords": ["12", "twelve", "all"], "p_obj": 0.20},
    {"text": "Is 1 a prime number?", "correct_keywords": ["no"], "p_obj": 0.35},
    {"text": "Divide 30 by 0.5 and add 10. Result?", "correct_keywords": ["70"], "p_obj": 0.20},
]

# --- EXPERIMENTAL PHASE ---
experimental_qs = [
    {"text": "5 machines make 5 widgets in 5 mins. 100 machines make 100 in how many mins?", "correct_keywords": ["5", "five"], "p_obj": 0.25},
    {"text": "Lily pads double daily. Cover lake in 48 days. Cover half in how many?", "correct_keywords": ["47"], "p_obj": 0.20},
    {"text": "If you overtake the 2nd person in a race, what place are you in?", "correct_keywords": ["2", "second"], "p_obj": 0.30},
    {"text": "A farmer has 17 sheep. All but 9 die. How many are left?", "correct_keywords": ["9", "nine"], "p_obj": 0.30},
    {"text": "If you have 3 apples and take away 2, how many do YOU have?", "correct_keywords": ["2", "two"], "p_obj": 0.30},
]

guardian = EpistemicGuardian()
guardian.run_phase(calibration_qs, mode="calibration")
guardian.run_phase(control_qs, mode="control")
guardian.run_phase(experimental_qs, mode="experimental")
guardian.print_final_report()