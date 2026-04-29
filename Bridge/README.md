# NX Bridge: Gesture Command Translator

This module provides a clean adapter layer between gesture-based commands and NX CAD viewport operations.

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
         NX Viewport
```

## Components

### `NXBridge`
Low-level adapter that translates `CommandType` enum commands into NX Open API calls.

**Key Features:**
- No keyboard or mouse simulation
- Direct NX Open API calls only
- Supports 7 viewport operations: rotate, pan, zoom, zoom-to-fit, and 3 standard views
- Dry-run mode when no NX session provided (useful for testing)
- Comprehensive logging and error handling

**Commands:**
- `ROTATE_VIEW(dx, dy)` - Rotate view by delta degrees
- `PAN_VIEW(dx, dy)` - Pan view in model space
- `ZOOM_VIEW(zoom_delta)` - Zoom with scale factor (0.1 = +10%, -0.1 = -10%)
- `ZOOM_TO_FIT()` - Fit all objects in view
- `VIEW_FRONT()` - Set to front standard view
- `VIEW_TOP()` - Set to top standard view
- `VIEW_ISO()` - Set to isometric standard view

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
    "intent": "ROTATE_VIEW",
    "values": {"dx": 5.0, "dy": 10.0}
}

success = dispatcher.dispatch_intent(detection)
```

### Test/Dry-Run Mode (no NX required)
```python
bridge = NXBridge()  # No session argument
dispatcher = CommandDispatcher(bridge)

# Test dispatch
dispatcher.dispatch_intent({"intent": "VIEW_ISO"})
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
- `view.rotate(dx, dy, dz)` - Rotational transform
- `view.pan(dx, dy)` - Translational transform
- `view.zoom(scale_factor)` - Scale-based zoom
- `view.fit_all()` - Zoom to extent
- `view.set_standard_view(view_name)` - Standard view presets

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
