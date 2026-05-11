# GTOC

Gesture-driven CAD navigation prototype built with Python, MediaPipe Hands, OpenCV, and an NX integration bridge.

## Overview

This repository experiments with translating webcam hand gestures into CAD viewport actions such as rotate and pan. The project is split into:

- a real-time hand-tracking loop in `src/hand_tracking.py`
- a rule-based gesture detector in `src/Gestures.py`
- a motion smoothing helper in `src/pan_stabilizer.py`
- an NX adapter layer in `Bridge/`

## Current capabilities

- Detects single-hand and two-hand gesture states from MediaPipe landmarks
- Maps gestures to CAD-oriented intents such as `ROTATE_X`, `ROTATE_Y`, `ROTATE_Z`, and directional movement
- Smooths open-hand panning signals before display or downstream control
- Provides a dry-run NX bridge for testing command dispatch without a live NX session
- Logs gesture detections to a timestamped file in `Log/`

## Gesture mapping

Current gesture handling implemented in the codebase:

| Gesture | Intent |
| --- | --- |
| One open hand moving up/down/left/right | `MOVE_UP`, `MOVE_DOWN`, `MOVE_LEFT`, `MOVE_RIGHT` |
| Index finger only | `ROTATE_Z` |
| Index + middle fingers | `ROTATE_X` |
| Thumbs-up | `ROTATE_Y` |
| Two open hands held for ~3 seconds | `MANIPULATION_ACTIVE` |

## Repository layout

```text
GTOC/
├── Bridge/
│   ├── adapter.py
│   ├── nx_bridge.py
│   └── README.md
├── Documents/
│   ├── Gesture → Intent spec.txt
│   └── Plan.txt
├── src/
│   ├── Gestures.py
│   ├── hand_tracking.py
│   └── pan_stabilizer.py
├── requirements.txt
└── LICENSE
```

## Requirements

- Python 3
- Webcam
- MediaPipe and OpenCV dependencies
- Optional: Siemens NX / NX Open session for real command execution

Install the listed dependencies from the repository root:

```bash
pip install -r requirements.txt
```

> `requirements.txt` currently pins `mediapipe==0.10.14`. OpenCV is also required by the source code and may need to be installed separately if it is not already present in your environment.

## Running the project

### Live gesture tracking

```bash
python src/hand_tracking.py
```

This opens the default webcam, detects hand landmarks, overlays the active gesture label, and writes logs to the `Log/` directory.

### NX bridge dry-run checks

```bash
python Bridge/nx_bridge.py
python Bridge/adapter.py
```

Both scripts exercise the bridge in dry-run mode and are useful for validating intent dispatch without an NX session.

## Notes

- `src/hand_tracking.py` uses `cv2.CAP_DSHOW`, which is typically intended for Windows camera capture.
- The root project is an early prototype; some documentation in `Documents/` describes broader planned gesture support than the code currently implements.
- The NX bridge is structured for direct NX Open API calls and intentionally avoids keyboard or mouse simulation.

## Additional documentation

- NX bridge details: `Bridge/README.md`
- Gesture specification: `Documents/Gesture → Intent spec.txt`
- High-level project plan: `Documents/Plan.txt`
