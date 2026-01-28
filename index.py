import time
import math
import sys

# Platform-specific character reading
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
    import mscvrt
    def get_key():
        return msvcrt.getch().decode('utf-8')

class EpistemicGuardian:
    def __init__(self):
        self.weights = {'w1': 0.4, 'w2': 0.3, 'w3': 0.3}
        self.nudge_threshold = 0.55
        self.personal_stats = {'latency': [], 'velocity': [], 'revisions': []}
        self.results_control = []
        self.results_exp = []
        self.nudges_triggered = 0
        self.corrections = 0

    def calculate_z_score(self, value, history):
        if len(history) < 2: return 0
        mean = sum(history) / len(history)
        var = sum((x - mean) ** 2 for x in history) / len(history)
        std = math.sqrt(var)
        return (value - mean) / (std if std > 0 else 1)

    def tracked_input(self):
        """Captures raw keystrokes and backspaces automatically."""
        chars = []
        keystrokes = 0
        revisions = 0
        start_time = time.time()
        first_key_time = None

        while True:
            char = get_key()
            if not first_key_time:
                first_key_time = time.time()
            
            # Enter key
            if char in ('\r', '\n'):
                sys.stdout.write('\n')
                break
            # Backspace (ASCII 127 or 8)
            elif char in ('\x7f', '\x08'):
                if len(chars) > 0:
                    chars.pop()
                    revisions += 1
                    keystrokes += 1
                    sys.stdout.write('\b \b') # Erase char from terminal
                    sys.stdout.flush()
            else:
                chars.append(char)
                keystrokes += 1
                sys.stdout.write(char)
                sys.stdout.flush()

        end_time = time.time()
        total_time = end_time - start_time
        latency = first_key_time - start_time if first_key_time else total_time
        
        # Velocity = Keystrokes per second
        velocity = keystrokes / total_time if total_time > 0 else 0
        
        return "".join(chars).strip().upper(), latency, velocity, revisions

    def run_session(self, questions, mode="control"):
        print(f"\n{'='*30}\nPHASE: {mode.upper()}\n{'='*30}")
        for i, q in enumerate(questions):
            print(f"\nQuestion {i+1}: {q['text']}")
            for opt in q['options']:
                print(opt)
            
            print("\nType A, B, C, or D and press ENTER:")
            ans, lat, vel, rev = self.tracked_input()

            # Z-Score math relative to PERSONAL history
            inv_lat_hist = [1/l for l in self.personal_stats['latency']] if self.personal_stats['latency'] else []
            z_lat = self.calculate_z_score(1/lat if lat > 0 else 0, inv_lat_hist)
            z_vel = self.calculate_z_score(vel, self.personal_stats['velocity'])
            z_rev = self.calculate_z_score(rev, self.personal_stats['revisions'])

            # BCI Formula (Sigmoid squash)
            raw_bci = (self.weights['w1'] * z_lat) + (self.weights['w2'] * z_vel) - (self.weights['w3'] * z_rev)
            bci = 1 / (1 + math.exp(-raw_bci))
            
            delta_c = bci - q['p_obj']
            is_correct = 1 if ans == q['correct'] else 0

            # Intervention logic
            if mode == "experimental" and delta_c > self.nudge_threshold and q['p_obj'] < 0.4:
                self.nudges_triggered += 1
                print("\n⚠️ [COGNITIVE NUDGE]: You are moving faster than your baseline.")
                print("--- SCREEN BLUR (3s) ---")
                time.sleep(3)
                print("Double-check the question logic. Re-enter your answer:")
                final_ans, _, _, _ = self.tracked_input()
                if final_ans == q['correct'] and is_correct == 0:
                    self.corrections += 1
                is_correct = 1 if final_ans == q['correct'] else 0

            # Store stats
            entry = {'bci': bci, 'outcome': is_correct, 'is_trap': q['p_obj'] < 0.4}
            if mode == "control":
                self.results_control.append(entry)
                self.personal_stats['latency'].append(lat)
                self.personal_stats['velocity'].append(vel)
                self.personal_stats['revisions'].append(rev)
            else:
                self.results_exp.append(entry)

    def print_final_report(self):
        print(f"\n{'='*30}\nISEF EVALUATION REPORT\n{'='*30}")
        def brier(res): return sum((r['bci'] - r['outcome'])**2 for r in res) / len(res)
        
        bs_c = brier(self.results_control)
        bs_e = brier(self.results_exp)
        
        acc_c = sum(r['outcome'] for r in self.results_control if r['is_trap']) / len([r for r in self.results_control if r['is_trap']])
        acc_e = sum(r['outcome'] for r in self.results_exp if r['is_trap']) / len([r for r in self.results_exp if r['is_trap']])

        print(f"Brier Score (Calibration Accuracy):")
        print(f" - Control:      {bs_c:.4f}")
        print(f" - Experimental: {bs_e:.4f}")
        print(f"\nTrap Accuracy (Safety Impact):")
        print(f" - Control:      {acc_c*100:.1f}%")
        print(f" - Experimental: {acc_e*100:.1f}%")
        print(f"\nNudge Efficiency (η): {self.corrections/self.nudges_triggered if self.nudges_triggered > 0 else 0:.2f}")

# QUESTION DATABASE
# p_obj is standard difficulty probability (1.0 = easiest)
questions = [
    # CONTROL QUESTIONS (To build your profile)
    {"text": "What is the square root of 81?", "options": ["A) 7", "B) 8", "C) 9", "D) 10"], "correct": "C", "p_obj": 0.9},
    {"text": "Which planet is known as the Red Planet?", "options": ["A) Venus", "B) Mars", "C) Jupiter", "D) Saturn"], "correct": "B", "p_obj": 0.95},
    {"text": "What is 15% of 200?", "options": ["A) 20", "B) 30", "C) 40", "D) 50"], "correct": "B", "p_obj": 0.75},
    {"text": "Which gas do plants absorb from the atmosphere?", "options": ["A) Oxygen", "B) Carbon Dioxide", "C) Nitrogen", "D) Helium"], "correct": "B", "p_obj": 0.9},
    {"text": "In the series 2, 4, 8, 16... what is the next number?", "options": ["A) 24", "B) 30", "C) 32", "D) 64"], "correct": "C", "p_obj": 0.85},
    
    # EXPERIMENTAL QUESTIONS (The Guardian is active)
    {"text": "A bat and a ball cost $1.10. The bat costs $1.00 more than the ball. How much is the ball?", "options": ["A) $0.10", "B) $0.05", "C) $1.00", "D) $0.15"], "correct": "B", "p_obj": 0.15},
    {"text": "If it takes 5 machines 5 minutes to make 5 widgets, how long for 100 machines to make 100?", "options": ["A) 100 min", "B) 50 min", "C) 5 min", "D) 20 min"], "correct": "C", "p_obj": 0.25},
    {"text": "Is 1 a prime number?", "options": ["A) Yes", "B) No"], "correct": "B", "p_obj": 0.35},
    {"text": "In a lake, there is a patch of lily pads. Every day, the patch doubles in size. If it takes 48 days for the patch to cover the entire lake, how long for it to cover half?", "options": ["A) 24 days", "B) 47 days", "C) 12 days", "D) 36 days"], "correct": "B", "p_obj": 0.20},
    {"text": "A man looks at a photo. He says: 'Brothers and sisters I have none, but that man's father is my father's son.' Who is in the photo?", "options": ["A) Himself", "B) His Son", "C) His Father", "D) His Nephew"], "correct": "B", "p_obj": 0.30}
]

guardian = EpistemicGuardian()
guardian.run_session(questions[:5], mode="control")
guardian.run_session(questions[5:], mode="experimental")
guardian.print_final_report()