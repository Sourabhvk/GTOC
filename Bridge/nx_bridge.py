"""
NX Bridge: Adapter for translating abstract gesture commands to NX CAD operations.

This module receives abstract commands (ROTATE_VIEW, PAN_VIEW, ZOOM_VIEW, etc.)
and translates them into NX Open viewport operations using the NX API.

No keyboard or mouse simulation - direct NX Open API calls only.
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any


class CommandType(Enum):
    """Abstract command types that come from gesture interpretation."""
    ROTATE_VIEW = "ROTATE_VIEW"
    PAN_VIEW = "PAN_VIEW"
    ZOOM_VIEW = "ZOOM_VIEW"
    ZOOM_TO_FIT = "ZOOM_TO_FIT"
    VIEW_FRONT = "VIEW_FRONT"
    VIEW_TOP = "VIEW_TOP"
    VIEW_ISO = "VIEW_ISO"


class NXBridge:
    """
    Thin adapter between gesture-derived commands and NX viewport operations.
    
    Initialize with an NX session. Each command maps to a specific NX API call.
    """
    
    def __init__(self, nxopen_session=None):
        """
        Initialize the NX bridge.
        
        Args:
            nxopen_session: NX.Session object from NX Open API.
                           If None, bridge operates in dry-run mode for testing.
        """
        self.session = nxopen_session
        self.logger = logging.getLogger(__name__)
        
        # Track rotation state for incremental operations
        self.last_rotation_matrix = None
        
    def execute_command(self, command: CommandType, values: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute an abstract command in NX.
        
        Args:
            command: The CommandType to execute
            values: Dict with command-specific parameters:
                   - ROTATE_VIEW: {dx, dy} - rotation deltas in degrees
                   - PAN_VIEW: {dx, dy} - pan distance in model units
                   - ZOOM_VIEW: {zoom_delta} - positive = zoom in, negative = zoom out
                   - One-shot commands: no values needed
        
        Returns:
            True if successful, False if failed or no NX session
        """
        if not self.session:
            self.logger.warning(f"No NX session; dry-run: {command.value}")
            return True
        
        try:
            if command == CommandType.ROTATE_VIEW:
                return self._rotate_view(values.get("dx", 0), values.get("dy", 0))
            elif command == CommandType.PAN_VIEW:
                return self._pan_view(values.get("dx", 0), values.get("dy", 0))
            elif command == CommandType.ZOOM_VIEW:
                return self._zoom_view(values.get("zoom_delta", 0))
            elif command == CommandType.ZOOM_TO_FIT:
                return self._zoom_to_fit()
            elif command == CommandType.VIEW_FRONT:
                return self._set_view_front()
            elif command == CommandType.VIEW_TOP:
                return self._set_view_top()
            elif command == CommandType.VIEW_ISO:
                return self._set_view_isometric()
            else:
                self.logger.error(f"Unknown command: {command}")
                return False
        except Exception as e:
            self.logger.error(f"Error executing {command.value}: {e}")
            return False
    
    def _rotate_view(self, dx: float, dy: float) -> bool:
        """
        Rotate the view by the given deltas.
        
        Args:
            dx: Horizontal rotation delta (degrees)
            dy: Vertical rotation delta (degrees)
        
        Returns:
            True if successful
        """
        try:
            # Get the active display
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            # Get the view to rotate
            view = display.view
            if not view:
                self.logger.error("No active view")
                return False
            
            # Apply rotation using NX API
            # dx typically maps to Y-axis rotation (pan left/right)
            # dy typically maps to X-axis rotation (pan up/down)
            view.rotate(dx, dy, 0)
            
            self.logger.debug(f"Rotated view: dx={dx}, dy={dy}")
            return True
        except Exception as e:
            self.logger.error(f"Rotation failed: {e}")
            return False
    
    def _pan_view(self, dx: float, dy: float) -> bool:
        """
        Pan the view by the given deltas in model space.
        
        Args:
            dx: Horizontal pan distance
            dy: Vertical pan distance
        
        Returns:
            True if successful
        """
        try:
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            view = display.view
            if not view:
                self.logger.error("No active view")
                return False
            
            # Pan using NX viewport translation
            view.pan(dx, dy)
            
            self.logger.debug(f"Panned view: dx={dx}, dy={dy}")
            return True
        except Exception as e:
            self.logger.error(f"Pan failed: {e}")
            return False
    
    def _zoom_view(self, zoom_delta: float) -> bool:
        """
        Zoom the view by the given delta.
        
        Args:
            zoom_delta: Positive value zooms in, negative zooms out.
                       Typically normalized 0-1 range or percentage.
        
        Returns:
            True if successful
        """
        try:
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            view = display.view
            if not view:
                self.logger.error("No active view")
                return False
            
            # NX expects zoom as a scale factor
            # Positive delta = zoom in (scale > 1)
            # Negative delta = zoom out (scale < 1)
            scale_factor = 1.0 + zoom_delta
            
            view.zoom(scale_factor)
            
            self.logger.debug(f"Zoomed view: delta={zoom_delta}, scale={scale_factor}")
            return True
        except Exception as e:
            self.logger.error(f"Zoom failed: {e}")
            return False
    
    def _zoom_to_fit(self) -> bool:
        """
        Fit all objects in view (zoom to extent).
        
        Returns:
            True if successful
        """
        try:
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            view = display.view
            if not view:
                self.logger.error("No active view")
                return False
            
            # NX API call to fit all objects
            view.fit_all()
            
            self.logger.info("Zoom to fit executed")
            return True
        except Exception as e:
            self.logger.error(f"Zoom to fit failed: {e}")
            return False
    
    def _set_view_front(self) -> bool:
        """Set view to Front (XY plane, looking along Z)."""
        try:
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            view = display.view
            if not view:
                self.logger.error("No active view")
                return False
            
            # Set to front view
            view.set_standard_view("FRONT")
            
            self.logger.info("Set to front view")
            return True
        except Exception as e:
            self.logger.error(f"Set front view failed: {e}")
            return False
    
    def _set_view_top(self) -> bool:
        """Set view to Top (XZ plane, looking along Y)."""
        try:
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            view = display.view
            if not view:
                self.logger.error("No active view")
                return False
            
            # Set to top view
            view.set_standard_view("TOP")
            
            self.logger.info("Set to top view")
            return True
        except Exception as e:
            self.logger.error(f"Set top view failed: {e}")
            return False
    
    def _set_view_isometric(self) -> bool:
        """Set view to Isometric (trimetric view)."""
        try:
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            view = display.view
            if not view:
                self.logger.error("No active view")
                return False
            
            # Set to isometric view
            view.set_standard_view("ISOMETRIC")
            
            self.logger.info("Set to isometric view")
            return True
        except Exception as e:
            self.logger.error(f"Set isometric view failed: {e}")
            return False


class CommandDispatcher:
    """
    Helper class to dispatch gesture intent dictionaries to the NX bridge.
    
    Bridges the gap between the gesture detector output and the NX bridge input.
    """
    
    def __init__(self, nx_bridge: NXBridge):
        """
        Initialize the dispatcher.
        
        Args:
            nx_bridge: The NXBridge instance to dispatch commands to
        """
        self.bridge = nx_bridge
        self.logger = logging.getLogger(__name__)
    
    def dispatch_intent(self, intent_dict: Dict[str, Any]) -> bool:
        """
        Dispatch a gesture intent to the NX bridge.
        
        Args:
            intent_dict: Dict from gesture detector with keys:
                        - 'intent': Intent name (e.g., 'ROTATE_VIEW')
                        - 'values': Dict with command parameters
                        - Other gesture info (state, gesture, display, etc.)
        
        Returns:
            True if dispatch was successful
        """
        try:
            intent_name = intent_dict.get("intent")
            if not intent_name:
                return False
            
            # Map intent name to CommandType
            try:
                command = CommandType[intent_name]
            except KeyError:
                self.logger.warning(f"Unknown intent: {intent_name}")
                return False
            
            values = intent_dict.get("values", {})
            success = self.bridge.execute_command(command, values)
            
            if not success:
                self.logger.warning(f"Command execution failed: {intent_name}")
            
            return success
        except Exception as e:
            self.logger.error(f"Dispatch error: {e}")
            return False


if __name__ == "__main__":
    # Example usage (dry-run without NX session)
    logging.basicConfig(level=logging.DEBUG)
    
    bridge = NXBridge()  # No session = dry-run mode
    dispatcher = CommandDispatcher(bridge)
    
    # Test dispatching a rotate command
    test_intent = {
        "intent": "ROTATE_VIEW",
        "values": {"dx": 5.0, "dy": 10.0},
        "gesture": "ONE_HAND_OPEN",
        "state": "TRACKING"
    }
    
    print("Testing dispatcher with rotate command:")
    result = dispatcher.dispatch_intent(test_intent)
    print(f"Result: {result}\n")
    
    # Test a zoom command
    test_intent = {
        "intent": "ZOOM_VIEW",
        "values": {"zoom_delta": 0.1},
        "gesture": "TWO_OPEN_HANDS"
    }
    
    print("Testing dispatcher with zoom command:")
    result = dispatcher.dispatch_intent(test_intent)
    print(f"Result: {result}")
