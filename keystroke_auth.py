"""
Keystroke Dynamics Authentication (improved for VS Code)

This version:
 - Uses pynput if available and working.
 - Falls back to a VS-Code/terminal-friendly per-character input recorder
   when pynput cannot capture keys in your environment.
 - Keeps demo mode and JSON profile storage.

Usage:
  python keystroke_auth.py        # interactive
  python keystroke_auth.py --demo # run simulated demo (no pynput required)
"""
import argparse
import json
import os
import time
from statistics import mean
import random
import sys

PROFILE_FILE = "profiles.json"
PASSWORD = "secret"  # exact password for interactive capture

# Try to import pynput (may fail or be ineffective in some terminals)
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except Exception:
    PYNPUT_AVAILABLE = False

# --- Real capture globals (for pynput) ---
press_times = []
release_times = []
pressed_sequence = []
recording = False

def on_press(key):
    global recording
    try:
        k = key.char
    except AttributeError:
        k = str(key)
    if recording:
        press_times.append(time.time())
        pressed_sequence.append(k)

def on_release(key):
    global recording
    if recording:
        release_times.append(time.time())
        # stop recording when Enter released
        if key == keyboard.Key.enter:
            return False

def record_keystrokes_pynput(prompt):
    """
    Use pynput listener to record press and release times.
    Blocks until Enter key release is detected.
    """
    global press_times, release_times, pressed_sequence, recording
    press_times = []
    release_times = []
    pressed_sequence = []
    print(prompt)
    print(f"Type the password then press Enter. Password must be exactly: '{PASSWORD}'")
    input("Press Enter to start recording in the background...")
    recording = True
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    recording = False
    typed = "".join(ch for ch in pressed_sequence if len(ch) == 1)
    if typed.endswith('\r') or typed.endswith('\n'):
        typed = typed[:-1]
    # return copies to be safe
    return typed, press_times[:], release_times[:]

# --- Fallback recorder (works reliably in VS Code / any terminal) ---
# Replace the existing record_keystrokes_fallback in keystroke_auth.py with this version.

import sys
import time

# Try to import msvcrt (Windows). If not available, we'll use the old per-character input fallback.
try:
    import msvcrt
    MSVCRT_AVAILABLE = True
except Exception:
    MSVCRT_AVAILABLE = False

def record_keystrokes_fallback(prompt):
    """
    Terminal-friendly recorder that:
     - On Windows uses msvcrt.getwch() to capture real-time key presses in the terminal.
       (User presses Enter to start, then types the full password, then presses Enter to stop.)
     - On non-Windows (or if msvcrt unavailable) falls back to per-character input with Enter after each char.
    Returns: typed_string, press_times_list, release_times_list
    """
    print(prompt)
    print("FALLBACK MODE (terminal-friendly).")
    print("You can type the whole password continuously when prompted, then press Enter to finish.")
    print(f"Password to enter: '{PASSWORD}'")
    input("Press Enter to begin recording...")

    # --- Windows real-time capture using msvcrt ---
    if MSVCRT_AVAILABLE and sys.platform.startswith("win"):
        print("Recording... (type the password and press Enter when done)")
        press_times_local = []
        release_times_local = []
        pressed_chars = []
        dwell_estimate = 0.08  # we still estimate dwell (release = press + dwell)

        while True:
            ch = msvcrt.getwch()  # reads a single wide char without needing Enter
            now = time.time()
            # Enter (carriage return) signals end of input
            if ch == '\r' or ch == '\n':
                break
            # Handle Backspace: remove last char if any
            if ch == '\x08':
                if pressed_chars:
                    pressed_chars.pop()
                    if press_times_local:
                        press_times_local.pop()
                # Echo backspace for user
                # In most terminals the backspace will already remove characters visually.
                continue
            # Append char and its absolute press time
            pressed_chars.append(ch)
            press_times_local.append(now)
            # continue capturing until Enter
        # derive release times as press + dwell_estimate
        release_times_local = [t + dwell_estimate for t in press_times_local]
        typed = "".join(pressed_chars)
        return typed, press_times_local, release_times_local

    # --- Non-Windows fallback: per-character Enter-based recording (reliable) ---
    print("msvcrt not available — using per-character Enter fallback.")
    times = []
    pressed_chars = []
    input("Press Enter to begin the per-character recording...")
    prev = time.time()
    for expected_char in PASSWORD:
        s = input(f"Type '{expected_char}' then press Enter: ")
        now = time.time()
        ch = s[0] if s else ''
        pressed_chars.append(ch)
        times.append(now - prev)
        prev = now
    # build press/release times from intervals
    press_times_local = []
    release_times_local = []
    dwell_estimate = 0.08
    base = time.time()
    cumulative = base
    for interval in times:
        cumulative += interval
        press_times_local.append(cumulative)
        release_times_local.append(cumulative + dwell_estimate)
    typed = "".join(pressed_chars)
    return typed, press_times_local, release_times_local

def extract_features(typed, press_times, release_times):
    """
    Returns a feature vector: [dwell_0...dwell_n, flight_1...flight_n]
    Dwell = release[i] - press[i]
    Flight = press[i] - press[i-1] (for i>=1)
    """
    if typed != PASSWORD:
        return None
    n = len(PASSWORD)
    # Ensure we have at least n press and n release times; otherwise fail
    if len(press_times) < n or len(release_times) < n:
        return None
    dwell = [release_times[i] - press_times[i] for i in range(n)]
    flight = [press_times[i] - press_times[i-1] for i in range(1, n)]
    return dwell + flight

def save_profile(name, features):
    data = {}
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
    data[name] = features
    with open(PROFILE_FILE, "w") as f:
        json.dump(data, f)

def load_profile(name):
    if not os.path.exists(PROFILE_FILE):
        return None
    with open(PROFILE_FILE, "r") as f:
        try:
            return json.load(f).get(name)
        except Exception:
            return None

def compare_features(f1, f2):
    if f1 is None or f2 is None or len(f1) != len(f2):
        return float('inf')
    diffs = [abs(a-b) for a,b in zip(f1,f2)]
    return mean(diffs)

# --- Utilities for demo/simulation (unchanged) ---
def jittered_sample_from_profile(base_features, jitter=0.03):
    return [max(0.0, v + random.gauss(0, jitter)) for v in base_features]

def average_samples(samples):
    if not samples:
        return None
    length = len(samples[0])
    for s in samples:
        if len(s) != length:
            return None
    return [mean(col) for col in zip(*samples)]

def interactive_register(name):
    """
    Register by recording 3 samples and averaging.
    Chooses pynput or fallback automatically.
    """
    print(f"Registering profile '{name}' — will record 3 samples and average them.")
    samples = []
    for i in range(3):
        print(f"Recording sample {i+1}/3")
        # Choose recorder
        if should_use_pynput():
            typed, press, rel = record_keystrokes_pynput(f"Recording sample {i+1}/3")
        else:
            typed, press, rel = record_keystrokes_fallback(f"Recording sample {i+1}/3")
        features = extract_features(typed, press, rel)
        if features is None:
            print("Typed text did not match password. Aborting registration.")
            return False
        samples.append(features)
        print(f"Captured sample {i+1}")
    avg = average_samples(samples)
    save_profile(name, avg)
    print("Saved averaged profile for", name)
    return True

def interactive_test(name, threshold=0.10):
    stored = load_profile(name)
    if stored is None:
        print("Profile not found.")
        return
    # choose recorder
    if should_use_pynput():
        typed, press, rel = record_keystrokes_pynput("Recording test pattern")
    else:
        typed, press, rel = record_keystrokes_fallback("Recording test pattern")
    features = extract_features(typed, press, rel)
    if features is None:
        print("Typed text did not match password. Try again.")
        return
    score = compare_features(stored, features)
    print(f"Mean absolute feature difference = {score:.4f} seconds")
    if score <= threshold:
        print("✅ Access Granted")
    else:
        print("❌ Access Denied")

def run_demo():
    random.seed(1)
    base_dwell = [0.08, 0.09, 0.07, 0.10, 0.09, 0.08]
    base_flight = [0.12, 0.11, 0.10, 0.14, 0.13]
    base_profile = base_dwell + base_flight
    reg_samples = [jittered_sample_from_profile(base_profile, jitter=0.02) for _ in range(3)]
    avg_profile = average_samples(reg_samples)
    save_profile("demo_user", avg_profile)
    print("Demo: saved averaged registration profile for 'demo_user'")

    genuine = jittered_sample_from_profile(avg_profile, jitter=0.02)
    score_genuine = compare_features(avg_profile, genuine)

    impostor_base = [v*1.3 for v in base_profile]
    impostor = jittered_sample_from_profile(impostor_base, jitter=0.03)
    score_impostor = compare_features(avg_profile, impostor)

    print(f"Genuine mean diff = {score_genuine:.4f} s")
    print(f"Impostor mean diff = {score_impostor:.4f} s")
    threshold = 0.10
    print(f"Using threshold = {threshold:.3f}")
    print("Genuine ->", "ACCEPT" if score_genuine <= threshold else "REJECT")
    print("Impostor ->", "ACCEPT" if score_impostor <= threshold else "REJECT")

# --- Environment detection ---
def running_in_vscode():
    # Common env var in VS Code integrated terminal
    return ("VSCODE_PID" in os.environ) or (os.environ.get("TERM_PROGRAM","").lower() == "vscode")

def should_use_pynput():
    """
    Decide whether to use pynput listener.
    We only use it when pynput is available and we are not in known terminals that block hooks.
    """
    if not PYNPUT_AVAILABLE:
        return False
    # If running in VS Code integrated terminal, prefer fallback because pynput often fails there
    if running_in_vscode():
        return False
    # Otherwise attempt to use pynput
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true', help='Run non-interactive demo (no pynput required)')
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    print("Keystroke Dynamics (Real) — password:", PASSWORD)
    mode = input("Choose: (r)egister or (t)est: ").lower()
    if mode == 'r':
        name = input("Enter profile name to register: ")
        interactive_register(name)
    else:
        name = input("Which profile to test? ")
        interactive_test(name)

if __name__ == '__main__':
    main()
