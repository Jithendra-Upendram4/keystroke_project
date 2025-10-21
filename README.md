Project: Keystroke Dynamics Authentication

Description: Behavioral biometric using typing rhythm. We capture per-key timings (dwell and flight times), store a profile for a password, and compare mean absolute differences to authenticate.

Implementation: Python. This workspace contains an Option B implementation (real timings using pynput) with a `--demo` mode for automated demonstration.

Files:

Quick start (Windows PowerShell):
# Keystroke Dynamics Authentication

Short: behavioral biometric demo that captures typing rhythm (dwell and flight times) for a fixed password, saves a timing profile, and authenticates using mean absolute timing differences.

This repository contains a Python implementation with two modes:
- Interactive (uses `pynput` to capture real keystrokes)
- Demo (`--demo`) — simulated recordings so you can run the project non-interactively.

Files:
- `keystroke_auth.py` — main script (interactive and demo modes).
- `profiles.json` — created when profiles are saved.
- `requirements.txt` — Python dependencies for interactive capture.

Quick start (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python keystroke_auth.py    # interactive mode (needs a keyboard)
python keystroke_auth.py --demo  # run non-interactive demo
```

Notes:
- Interactive mode requires `pynput` and captures real key press/release events.
- Demo mode simulates registration and tests so you can run a reproducible example without hardware capture.

Notes:
- Interactive mode requires `pynput` and captures real key press/release events.
- Demo mode simulates registration and tests so you can run a reproducible example without hardware capture.
