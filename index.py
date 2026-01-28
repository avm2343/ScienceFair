import time
import math
import sys

# Raw Input Handler
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
        self.weights = {'w1': 0.6, 'w2': 0.2, 'w3': 0.2} 
        self.nudge_threshold = 0.35 
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
        total_time = time.time() - start_time
        latency = (first_key_time - start_time) if first_key_time else total_time
        velocity = keystrokes / total_time if total_time > 0 else 0
        return "".join(chars).strip().upper(), latency, velocity, revisions

    def run_phase(self, questions, mode):
        print(f"\n{'='*50}\nPHASE: {mode.upper()}\n{'='*50}")
        for i, q in enumerate(questions):
            print(f"\nQ{i+1}: {q['text']}")
            for opt in q['options']: print(opt)
            print("\n[Input A, B, C, or D + Enter]")
            ans, lat, vel, rev = self.tracked_input()

            inv_lat_hist = [1/l for l in self.personal_stats['latency']] if self.personal_stats['latency'] else []
            z_lat = self.calculate_z_score(1/lat if lat > 0 else 0, inv_lat_hist)
            z_vel = self.calculate_z_score(vel, self.personal_stats['velocity'])
            z_rev = self.calculate_z_score(rev, self.personal_stats['revisions'])

            raw_bci = (self.weights['w1'] * z_lat) + (self.weights['w2'] * z_vel) - (self.weights['w3'] * z_rev)
            bci = 1 / (1 + math.exp(-raw_bci))
            delta_c = bci - q['p_obj']
            is_correct = 1 if ans == q['correct'] else 0

            print(f"--- DEBUG: BCI: {bci:.2f} | P_obj: {q['p_obj']:.2f} | Delta_C: {delta_c:.2f} ---")

            if mode == "experimental" and delta_c > self.nudge_threshold:
                self.nudges_triggered += 1
                print("\n⚠️  [COGNITIVE NUDGE]: Overconfidence detected.")
                time.sleep(3)
                print("RE-EVALUATE: Enter your final answer:")
                final_ans, _, _, _ = self.tracked_input()
                if final_ans == q['correct'] and is_correct == 0: self.corrections += 1
                is_correct = 1 if final_ans == q['correct'] else 0

            entry = {'bci': bci, 'outcome': is_correct, 'is_trap': q['p_obj'] < 0.4}
            if mode == "control": self.results_control.append(entry)
            elif mode == "experimental": self.results_exp.append(entry)
            
            self.personal_stats['latency'].append(lat)
            self.personal_stats['velocity'].append(vel)
            self.personal_stats['revisions'].append(rev)

    def print_final_report(self):
        print(f"\n{'='*50}\nFINAL ISEF PERFORMANCE REPORT\n{'='*50}")
        def get_acc(res_list):
            traps = [r['outcome'] for r in res_list if r['is_trap']]
            return sum(traps) / len(traps) if traps else 0
        def brier(res_list):
            return sum((r['bci'] - r['outcome'])**2 for r in res_list) / len(res_list) if res_list else 0

        print(f"Brier Score: Control: {brier(self.results_control):.4f} | Exp: {brier(self.results_exp):.4f}")
        print(f"Trap Accuracy: Control: {get_acc(self.results_control)*100:.1f}% | Exp: {get_acc(self.results_exp)*100:.1f}%")
        eta = self.corrections / self.nudges_triggered if self.nudges_triggered > 0 else 0
        print(f"Efficiency (η): {eta:.2f} | Nudges: {self.nudges_triggered} | Prevented: {self.corrections}")

# --- EXPANDED QUESTION DATABASE ---
calibration_qs = [
    {"text": "2 + 2?", "options": ["A) 3", "B) 4", "C) 5", "D) 6"], "correct": "B", "p_obj": 0.99},
    {"text": "Opposite of 'Hot'?", "options": ["A) Cold", "B) Warm", "C) Spicy", "D) Dry"], "correct": "A", "p_obj": 0.99},
]

control_qs = [
    {"text": "Bat and ball cost $1.10. Bat is $1 more than ball. Ball cost?", "options": ["A) $0.10", "B) $0.05", "C) $0.01", "D) $0.15"], "correct": "B", "p_obj": 0.15},
    {"text": "Is 1 a prime number?", "options": ["A) Yes", "B) No"], "correct": "B", "p_obj": 0.35},
    {"text": "Emily's father has 3 daughters: April, May, and...?", "options": ["A) June", "B) Emily", "C) Sarah", "D) Jane"], "correct": "B", "p_obj": 0.25},
    {"text": "A farmer has 17 sheep. All but 9 die. How many are left?", "options": ["A) 8", "B) 9", "C) 17", "D) 0"], "correct": "B", "p_obj": 0.30},
    {"text": "How many months have 28 days?", "options": ["A) 1", "B) 6", "C) 12", "D) 0"], "correct": "C", "p_obj": 0.20},
    {"text": "Which is heavier: 1kg of lead or 1kg of feathers?", "options": ["A) Lead", "B) Feathers", "C) Neither", "D) Lead (density)"], "correct": "C", "p_obj": 0.80},
    {"text": "A doctor gives you 3 pills and tells you to take one every half hour. How long do they last?", "options": ["A) 1.5 hours", "B) 1 hour", "C) 30 mins", "D) 2 hours"], "correct": "B", "p_obj": 0.25},
    {"text": "How many 0.5cm slices can you cut from a 25cm bread loaf?", "options": ["A) 50", "B) 25", "C) 12.5", "D) 100"], "correct": "A", "p_obj": 0.40},
    {"text": "A plane crashes on the border of US and Canada. Where are survivors buried?", "options": ["A) US", "B) Canada", "C) Border", "D) Not buried"], "correct": "D", "p_obj": 0.15},
    {"text": "What is the next prime after 7?", "options": ["A) 9", "B) 11", "C) 13", "D) 8"], "correct": "B", "p_obj": 0.70},
]

experimental_qs = [
    {"text": "5 machines, 5 widgets, 5 mins. 100 machines, 100 widgets, how long?", "options": ["A) 100m", "B) 5m", "C) 50m", "D) 20m"], "correct": "B", "p_obj": 0.25},
    {"text": "Lily pads double daily. Cover lake in 48 days. Cover half in...?", "options": ["A) 24d", "B) 47d", "C) 12d", "D) 36d"], "correct": "B", "p_obj": 0.20},
    {"text": "Some months have 31 days. How many have 28?", "options": ["A) 1", "B) 12", "C) 0", "D) 6"], "correct": "B", "p_obj": 0.25},
    {"text": "If you overtake the 2nd person in a race, what place are you in?", "options": ["A) 1st", "B) 2nd", "C) 3rd", "D) Last"], "correct": "B", "p_obj": 0.30},
    {"text": "A clerk in a butcher shop is 5'10'' tall and wears size 11 shoes. What does he weigh?", "options": ["A) 180 lbs", "B) Meat", "C) 210 lbs", "D) Size 11"], "correct": "B", "p_obj": 0.15},
    {"text": "Divide 30 by 1/2 and add 10. What is the result?", "options": ["A) 25", "B) 70", "C) 40", "D) 50"], "correct": "B", "p_obj": 0.20},
    {"text": "If a red house is made of red bricks, what is a green house made of?", "options": ["A) Green bricks", "B) Grass", "C) Glass", "D) Wood"], "correct": "C", "p_obj": 0.15},
    {"text": "How many animals of each sex did Moses take on the Ark?", "options": ["A) 1", "B) 2", "C) 0", "D) 7"], "correct": "C", "p_obj": 0.10},
    {"text": "If you have 3 apples and you take away 2, how many apples do you have?", "options": ["A) 1", "B) 2", "C) 3", "D) 0"], "correct": "B", "p_obj": 0.30},
    {"text": "What color is a black box in a commercial airplane?", "options": ["A) Black", "B) Orange", "C) Silver", "D) Yellow"], "correct": "B", "p_obj": 0.40},
]

guardian = EpistemicGuardian()
guardian.run_phase(calibration_qs, mode="calibration")
guardian.run_phase(control_qs, mode="control")
guardian.run_phase(experimental_qs, mode="experimental")
guardian.print_final_report()