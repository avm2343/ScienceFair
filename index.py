import time
import math
import sys
import os
import csv

# --- INPUT HANDLER ---
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

class DataManager:
    def __init__(self, filename="control_results.csv"):
        self.filename = filename
        self.headers = ["participant_id", "q_id", "is_correct", "latency"]
        if not os.path.exists(self.filename):
            self.create_headers()

    def create_headers(self):
        with open(self.filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)

    def log_control_result(self, p_id, q_id, is_correct, lat):
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([p_id, q_id, is_correct, round(lat, 3)])

    def get_p_obj_map(self):
        p_obj_map = {}
        q_stats = {}
        if not os.path.exists(self.filename): return {}
        with open(self.filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                q_id, is_correct = row['q_id'], int(row['is_correct'])
                if q_id not in q_stats: q_stats[q_id] = []
                q_stats[q_id].append(is_correct)
        for q_id, results in q_stats.items():
            p_obj_map[q_id] = sum(results) / len(results)
        return p_obj_map

class EpistemicGuardian:
    def __init__(self, mode):
        self.mode = mode
        self.manager = DataManager()
        self.p_obj_map = self.manager.get_p_obj_map() if mode == "E" else {}
        self.nudge_threshold = 0.35
        self.tau = 25.0 
        self.nudges = 0
        self.corrections = 0

    def print_p_obj_summary(self):
        print(f"\n{'='*45}")
        print(f"{'Question ID':<15} | {'Group A Accuracy (P_obj)':<25}")
        print("-" * 45)
        for q_id in ["CRT_A", "CRT_B", "CRT_C", "CRT_D", "CRT_E"]:
            val = self.p_obj_map.get(q_id, 0.0)
            print(f"{q_id:<15} | {val:<25.2%}")
        print(f"{'='*45}\n")

    def calculate_bci(self, lat):
        # 1.0 at 0.5s, decreases as time increases.
        if lat <= 0.5: return 1.0
        return math.exp(-(lat - 0.5) / self.tau)

    def tracked_input(self):
        chars = []
        start_time = time.time()
        while True:
            char = get_key()
            if char in ('\r', '\n'):
                sys.stdout.write('\n'); break
            elif char in ('\x7f', '\x08'):
                if len(chars) > 0:
                    chars.pop(); sys.stdout.write('\b \b'); sys.stdout.flush()
            else:
                chars.append(char); sys.stdout.write(char); sys.stdout.flush()
        # Full case-insensitivity and whitespace stripping
        return "".join(chars).strip().lower(), (time.time() - start_time)

    def run_session(self, baseline_qs, target_qs):
        if self.mode == "C":
            p_id = input("Enter Control Participant ID: ")
            for q in target_qs:
                print(f"\nQ: {q['text']}")
                ans, lat = self.tracked_input()
                is_correct = 1 if ans == q['answer'] else 0
                self.manager.log_control_result(p_id, q['id'], is_correct, lat)
            print("\nControl data logged successfully.")

        else:
            self.print_p_obj_summary()
            print("\n--- PHASE 1: TRAP BASELINE (Cognitive Warmup) ---")
            for q in baseline_qs:
                print(f"\nQ: {q['text']}")
                self.tracked_input()

            print("\n--- PHASE 2: TARGET EXPERIMENT ---")
            for q in target_qs:
                p_obj = self.p_obj_map.get(q['id'], 0.5)
                print(f"\nQ: {q['text']}")
                ans, lat = self.tracked_input()
                is_correct = 1 if ans == q['answer'] else 0
                
                bci = self.calculate_bci(lat)
                delta_c = bci - p_obj

                if delta_c > self.nudge_threshold:
                    self.nudges += 1
                    print(f"\n⚠️ [AI NUDGE] High Confidence ({bci:.2f}) vs Difficulty ({p_obj:.2f})")
                    time.sleep(2)
                    print("RE-EVALUATE: Re-type your final answer:")
                    final_ans, _ = self.tracked_input()
                    if final_ans == q['answer'] and is_correct == 0:
                        self.corrections += 1
                    is_correct = 1 if final_ans == q['answer'] else 0
            
            print(f"\nNudges Triggered: {self.nudges} | Errors Prevented: {self.corrections}")

# --- 10 ALL-TRAP BASELINE QUESTIONS ---
baseline_qs = [
    {"text": "A man has 17 sheep. All but 9 die. How many are left?", "answer": "9"},
    {"text": "What color is the bear if a man walks 1 mile S, 1 mile E, 1 mile N and is back home?", "answer": "white"},
    {"text": "If a plane crashes on the border of USA and Canada, where do you bury survivors?", "answer": "none"},
    {"text": "How many of each animal did Moses take on the Ark?", "answer": "0"}, # Trap: It was Noah
    {"text": "If you are in a race and pass the person in last place, what place are you in?", "answer": "none"}, # Trap: Impossible
    {"text": "A doctor gives you 3 pills and tells you to take 1 every 30 mins. How long until they are gone?", "answer": "60"}, # Trap: People say 90
    {"text": "If you have 3 apples and take away 2, how many do YOU have?", "answer": "2"},
    {"text": "Divide 30 by 0.5 and add 10. What is the result?", "answer": "70"}, # Trap: People say 25
    {"text": "A father and son are in a car crash. The doctor says 'I can't operate, he is my son'. Who is the doctor?", "answer": "mother"},
    {"text": "How many months have 28 days?", "answer": "12"}
]

# --- THE TARGET RESEARCH QUESTIONS ---
target_qs = [
    {"id": "CRT_A", "text": "A bat and ball cost $1.10. The bat is $1.00 more than the ball. Ball cost (cents)?", "answer": "5"},
    {"id": "CRT_B", "text": "If 5 workers make 5 shirts in 5 mins, how long for 100 workers to make 100 shirts?", "answer": "5"},
    {"id": "CRT_C", "text": "Lily pads double daily. It takes 48 days to cover a lake. How many days for half?", "answer": "47"},
    {"id": "CRT_D", "text": "A clock strikes 6 in 5 seconds. How long does it take to strike 12?", "answer": "11"},
    {"id": "CRT_E", "text": "Sally has 3 brothers. Each brother has 2 sisters. How many sisters does Sally have?", "answer": "1"}
]

# --- MAIN ---
print("Mode C: Build your CSV with Group A data.")
print("Mode E: Use Group A data to nudge Group B.")
mode_choice = input("Select Mode (C/E): ").upper()

if mode_choice == "RESET": # Hidden command to clear data
    os.remove("control_results.csv")
    print("CSV Deleted.")
else:
    guardian = EpistemicGuardian(mode_choice)
    guardian.run_session(baseline_qs, target_qs)