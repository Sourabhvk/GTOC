# NX Bridge: Gesture Command Translator

This module provides a clean adapter layer between gesture-based commands and NX CAD operations.

## Architecture

```
Gesture Detector (src/Gestures.py)
              ↓
        Intent Dictionary
              ↓
    CommandDispatcher (this package)
              ↓
          NXBridge
              ↓
      NX Open API Calls
              ↓
         NX Viewport/Model
```

## Supported Gestures & Commands

| Hand Gesture | Intent Name | NX Operation |
|--------------|-------------|--------------|
| 1 finger extended (index) | `ROTATE_Z` | Rotate around Z-axis (clockwise/counterclockwise) |
| 2 fingers extended (index + middle) | `ROTATE_X` | Rotate around X-axis |
| Thumb up (all fingers closed) | `ROTATE_Y` | Rotate around Y-axis |
| Open hand + move LEFT | `MOVE_LEFT` | Pan left |
| Open hand + move RIGHT | `MOVE_RIGHT` | Pan right |
| Open hand + move UP | `MOVE_UP` | Pan up |
| Open hand + move DOWN | `MOVE_DOWN` | Pan down |
| Two open hands (held 3+ sec) | `MANIPULATION_ACTIVE` | Manipulation mode active |

## Components

### `CommandType` Enum
Maps gesture intents to executable NX commands:
- `ROTATE_X`, `ROTATE_Y`, `ROTATE_Z` - Axis rotations
- `MOVE_UP`, `MOVE_DOWN`, `MOVE_LEFT`, `MOVE_RIGHT` - Panning
- `MANIPULATION_ACTIVE` - Two-hand manipulation mode

### `NXBridge`
Low-level adapter that translates commands to NX Open API calls.

**Key Features:**
- No keyboard or mouse simulation
- Direct NX Open API calls only
- Axis rotation support (with clockwise/counterclockwise direction)
- Panning support (screen-space translation)
- Dry-run mode when no NX session provided (useful for testing)
- Comprehensive logging and error handling

**Command Methods:**
- `_rotate_axis(direction, axis)` - Rotate around X, Y, or Z axis
- `_pan_view(dx, dy)` - Pan the view in 2D screen space

### `CommandDispatcher`
Bridge between gesture intent dictionaries and the NX bridge. Handles:
- Intent name → CommandType mapping
- Value extraction from gesture detections
- Dispatch to NXBridge
- Error handling and logging

### `GestureToNXAdapter` (in adapter.py)
High-level integration class for full pipeline:
- Gesture detection
- Intent dispatch
- Error recovery
- Batch processing support

## Usage

### Basic Integration (with real NX session)
```python
import NX  # NX Open SDK

session = NX.open_session()
bridge = NXBridge(session)
dispatcher = CommandDispatcher(bridge)

# From gesture detector output
detection = {
    "intent": "ROTATE_Z",
    "values": {"axis": "Z", "direction": "CLOCKWISE"}
}

success = dispatcher.dispatch_intent(detection)
```

### Test/Dry-Run Mode (no NX required)
```python
bridge = NXBridge()  # No session argument
dispatcher = CommandDispatcher(bridge)

# Test dispatch
dispatcher.dispatch_intent({"intent": "ROTATE_Z", "values": {"direction": "CLOCKWISE"}})
```

### Full Pipeline Integration
```python
adapter = GestureToNXAdapter(nxopen_session)

# In main loop:
for hand_landmarks in mediapipe_results:
    result = adapter.process_hand_landmarks(hand_landmarks)
```

## NX Open API Notes

The bridge uses these NX API concepts:
- `session.displays.active` - Get active viewport
- `display.view` - Viewport object with transformation methods
- `view.rotate(dx, dy, dz)` - Rotational transform around axes
- `view.pan(dx, dy)` - Translational transform in screen space

## Error Handling

All bridge methods:
- Return `True/False` for success
- Log errors with context
- Continue on exception (no crashes)
- Support graceful degradation in dry-run mode

## Testing

Run the module directly for dry-run testing:
```bash
python nx_bridge.py
python adapter.py
```

Both print example dispatch results to verify logic without NX.

## Future Extensions

Potential additions:
- Selection commands (CLICK, BOX_SELECT)
- Modeling commands (CREATE_SKETCH, EXTRUDE)
- View attributes (field of view, perspective)
- Multi-viewport support
- Command queueing and throttling
