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
        # Configuration
        self.nudge_threshold = 0.30 
        self.min_processing_time = 0.5 # Fastest possible human response
        
        self.personal_stats = {'latency': []}
        self.results_control = []
        self.results_exp = []
        self.nudges_triggered = 0
        self.corrections = 0

    def calculate_scaled_bci(self, lat):
        """
        Scales BCI from 1.0 (at min_processing_time) 
        downward based on the personal average.
        """
        if not self.personal_stats['latency']:
            return 0.5 # Default if no calibration
            
        avg_lat = sum(self.personal_stats['latency']) / len(self.personal_stats['latency'])
        
        # Linear Decay Formula: 
        # If lat <= min_processing_time, BCI = 1.0
        # If lat >= avg_lat, BCI approaches 0.0 (or a baseline)
        if lat <= self.min_processing_time:
            return 1.0
        
        # Calculate how far between "instant" and "average" the user is
        # BCI = 1 - ((current - min) / (average - min))
        slope_range = max(1.0, avg_lat - self.min_processing_time)
        bci = 1.0 - ((lat - self.min_processing_time) / slope_range)
        
        return max(0.0, min(1.0, bci))

    def tracked_input(self):
        chars = []
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
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            else:
                chars.append(char)
                sys.stdout.write(char)
                sys.stdout.flush()
        
        total_time = time.time() - start_time
        return "".join(chars).strip().lower(), total_time

    def run_phase(self, questions, mode):
        print(f"\n{'='*50}\nPHASE: {mode.upper()}\n{'='*50}")
        for i, q in enumerate(questions):
            print(f"\nQ{i+1}: {q['text']}")
            ans, lat = self.tracked_input()

            # Logic: BCI scales from 1.0 down based on time
            bci = self.calculate_scaled_bci(lat)
            delta_c = bci - q['p_obj']
            is_correct = 1 if any(ext in ans for ext in q['correct_keywords']) else 0

            print(f"--- [Metrics] Latency: {lat:.2f}s | BCI: {bci:.4f} | Delta_C: {delta_c:.2f} ---")

            if mode == "experimental" and delta_c > self.nudge_threshold:
                self.nudges_triggered += 1
                print("\n⚠️  [NUDGE]: Overconfidence detected.")
                time.sleep(3)
                print("RE-EVALUATE: Enter your final answer:")
                final_ans, _ = self.tracked_input()
                if any(ext in final_ans for ext in q['correct_keywords']) and is_correct == 0:
                    self.corrections += 1
                is_correct = 1 if any(ext in final_ans for ext in q['correct_keywords']) else 0

            entry = {'bci': bci, 'outcome': is_correct, 'is_trap': q['p_obj'] < 0.4}
            if mode == "control": self.results_control.append(entry)
            elif mode == "experimental": self.results_exp.append(entry)
            
            if mode == "calibration":
                self.personal_stats['latency'].append(lat)

    def print_final_report(self):
        print(f"\n{'='*50}\nISEF PERFORMANCE REPORT\n{'='*50}")
        def get_acc(res_list):
            traps = [r['outcome'] for r in res_list if r['is_trap']]
            return (sum(traps) / len(traps) * 100) if traps else 0
        
        acc_c = get_acc(self.results_control)
        acc_e = get_acc(self.results_exp)

        print(f"Trap Accuracy (Control): {acc_c:.1f}%")
        print(f"Trap Accuracy (Experimental): {acc_e:.1f}%")
        print(f"Improvement: {acc_e - acc_c:+.1f}%")
        
        eta = self.corrections / self.nudges_triggered if self.nudges_triggered > 0 else 0
        print(f"\nNudges Triggered: {self.nudges_triggered}")
        print(f"Errors Prevented: {self.corrections}")
        print(f"Nudge Efficiency (η): {eta:.2f}")

# Database (Same as previous for consistency)
calibration_qs = [
    {"text": "10 + 10?", "correct_keywords": ["20"], "p_obj": 0.99},
    {"text": "Opposite of 'up'?", "correct_keywords": ["down"], "p_obj": 0.99},
    {"text": "Color of a strawberry?", "correct_keywords": ["red"], "p_obj": 0.95},
    {"text": "How many legs on a dog?", "correct_keywords": ["4", "four"], "p_obj": 0.99},
    {"text": "5 x 5?", "correct_keywords": ["25"], "p_obj": 0.95},
    {"text": "Capital of France?", "correct_keywords": ["paris"], "p_obj": 0.95},
    {"text": "Freeze point of water (C)?", "correct_keywords": ["0", "zero"], "p_obj": 0.90},
    {"text": "What do bees make?", "correct_keywords": ["honey"], "p_obj": 0.98},
    {"text": "What is the sun?", "correct_keywords": ["star"], "p_obj": 0.95},
    {"text": "Opposite of 'black'?", "correct_keywords": ["white"], "p_obj": 0.99},
]

control_qs = [
    {"text": "A bat and ball cost $1.10. Bat is $1 more. Ball cost in cents?", "correct_keywords": ["5", "five"], "p_obj": 0.15},
    {"text": "Emily's father has 3 daughters: April, May, and...?", "correct_keywords": ["emily"], "p_obj": 0.25},
    {"text": "How many months have 28 days?", "correct_keywords": ["12", "twelve", "all"], "p_obj": 0.20},
    {"text": "Is 1 a prime number?", "correct_keywords": ["no"], "p_obj": 0.35},
    {"text": "Divide 30 by 0.5 and add 10. Result?", "correct_keywords": ["70"], "p_obj": 0.20},
]

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