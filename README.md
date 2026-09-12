# SCREAM VOLUME™

> **"Why use a slider when you have vocal cords?"**

SCREAM VOLUME™ is a fully offline Windows desktop app that sets your **real Windows master system volume** based on a 2.5-second scream.

## Features

- Futuristic dark-themed PySide6 interface
- Multi-screen flow: **Home → Screaming → Result → Calibration → Settings**
- Live microphone waveform + recording progress during scream capture
- RMS + peak loudness analysis (core functionality preserved)
- Real Windows system volume control using `pycaw` (Core Audio)
- Local calibration profile (your loudest comfortable scream = 100% reference)
- Settings for microphone selection, sensitivity, and min/max output volume
- Fully offline operation

---

## Windows Requirements

- Windows 10 or 11
- Python 3.10+ (recommended: 3.11 or 3.12)
- Working microphone configured in Windows sound settings

---

## Install (Windows)

Open **PowerShell** in the project folder:

```powershell
cd C:\path\to\mini-final
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell script execution is blocked, use Command Prompt:

```cmd
cd C:\path\to\mini-final
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Run

### Option A (Python)

```powershell
python scream_volume_manager.py
```

### Option B (Batch file)

Double-click `run_windows.bat`.

---

## How to Use

1. Open the app.
2. On **HOME**, check current system volume + calibration status.
3. Click **SET VOLUME**.
4. In **SCREAMING**, scream for the full recording window.
5. In **RESULT**, review scream percentage and final system volume.
6. Use **CALIBRATION** once for best results.
7. Use **SETTINGS** for microphone, sensitivity, and min/max output limits.

---

## Calibration Behavior

Calibration stores a local loudness reference in:

- `%APPDATA%\scream_volume\settings.json`

Your calibrated scream is treated as 100% baseline for future scream-to-volume mapping.

---

## Build a Windows EXE (optional)

If you want a standalone executable:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "SCREAM_VOLUME" scream_volume_manager.py
```

Output executable:

- `dist\SCREAM_VOLUME\SCREAM_VOLUME.exe`

---

## Notes

- This app intentionally avoids a traditional primary volume slider.
- The main control is the scream capture flow.
- On non-Windows systems, microphone capture may work, but Windows master volume control is unavailable by design.
