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
    ROTATE_X = "ROTATE_X"  # 2_FINGER gesture
    ROTATE_Y = "ROTATE_Y"  # THUMB_UP gesture
    ROTATE_Z = "ROTATE_Z"  # 1_FINGER gesture
    MOVE_UP = "MOVE_UP"    # ONE_HAND_OPEN + UP motion
    MOVE_DOWN = "MOVE_DOWN"  # ONE_HAND_OPEN + DOWN motion
    MOVE_LEFT = "MOVE_LEFT"  # ONE_HAND_OPEN + LEFT motion
    MOVE_RIGHT = "MOVE_RIGHT"  # ONE_HAND_OPEN + RIGHT motion
    MANIPULATION_ACTIVE = "MANIPULATION_ACTIVE"  # TWO_OPEN_HANDS after 3 sec


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
                   - ROTATE_X/Y/Z: {axis, direction} - axis rotation command
                   - MOVE_UP/DOWN/LEFT/RIGHT: {dx, dy, direction} - pan movement
                   - MANIPULATION_ACTIVE: {elapsed_sec} - manipulation mode active
        
        Returns:
            True if successful, False if failed or no NX session
        """
        if not self.session:
            self.logger.warning(f"No NX session; dry-run: {command.value}")
            return True
        
        try:
            if command == CommandType.ROTATE_X:
                return self._rotate_axis(values.get("direction", "CLOCKWISE"), "X")
            elif command == CommandType.ROTATE_Y:
                return self._rotate_axis(values.get("direction", "CLOCKWISE"), "Y")
            elif command == CommandType.ROTATE_Z:
                return self._rotate_axis(values.get("direction", "CLOCKWISE"), "Z")
            elif command == CommandType.MOVE_UP:
                return self._pan_view(0, values.get("dy", -0.05))
            elif command == CommandType.MOVE_DOWN:
                return self._pan_view(0, values.get("dy", 0.05))
            elif command == CommandType.MOVE_LEFT:
                return self._pan_view(values.get("dx", -0.05), 0)
            elif command == CommandType.MOVE_RIGHT:
                return self._pan_view(values.get("dx", 0.05), 0)
            elif command == CommandType.MANIPULATION_ACTIVE:
                self.logger.info("Manipulation mode ACTIVE")
                return True
            else:
                self.logger.error(f"Unknown command: {command}")
                return False
        except Exception as e:
            self.logger.error(f"Error executing {command.value}: {e}")
            return False
    
    def _rotate_axis(self, direction: str, axis: str) -> bool:
        """
        Rotate the active body/view around a specified axis.
        
        Args:
            direction: "CLOCKWISE" or "COUNTERCLOCKWISE"
            axis: "X", "Y", or "Z"
        
        Returns:
            True if successful
        """
        try:
            # Get the active display and view
            display = self.session.displays.active
            if not display:
                self.logger.error("No active display")
                return False
            
            # Determine rotation angle based on direction
            angle = 5.0  # 5 degrees per frame
            if direction == "COUNTERCLOCKWISE":
                angle = -angle
            
            # Apply rotation around axis
            # This would use NX API to rotate the view/body
            # Implementation depends on NX version and available API
            self.logger.debug(f"Rotate {axis}-axis {direction}: {angle}°")
            return True
        except Exception as e:
            self.logger.error(f"Axis rotation failed: {e}")
            return False
    
    def _pan_view(self, dx: float, dy: float) -> bool:
        """
        Pan the view by the given deltas (movement in X/Y screen space).
        
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
    
    # Test dispatching a rotate Z command (1-finger gesture)
    test_intent = {
        "intent": "ROTATE_Z",
        "values": {"axis": "Z", "direction": "CLOCKWISE"},
        "gesture": "1_FINGER",
        "state": "ROTATING"
    }
    
    print("Testing dispatcher with ROTATE_Z command:")
    result = dispatcher.dispatch_intent(test_intent)
    print(f"Result: {result}\n")
    
    # Test a rotate X command (2-finger gesture)
    test_intent = {
        "intent": "ROTATE_X",
        "values": {"axis": "X", "direction": "CLOCKWISE"},
        "gesture": "2_FINGER"
    }
    
    print("Testing dispatcher with ROTATE_X command:")
    result = dispatcher.dispatch_intent(test_intent)
    print(f"Result: {result}\n")
    
    # Test MOVE_RIGHT (open hand motion)
    test_intent = {
        "intent": "MOVE_RIGHT",
        "values": {"dx": 0.05, "direction": "RIGHT"},
        "gesture": "ONE_HAND_OPEN",
        "state": "TRACKING"
    }
    
    print("Testing dispatcher with MOVE_RIGHT command:")
    result = dispatcher.dispatch_intent(test_intent)
    print(f"Result: {result}\n")
    
    # Test MANIPULATION_ACTIVE (two open hands after 3 sec)
    test_intent = {
        "intent": "MANIPULATION_ACTIVE",
        "values": {"elapsed_sec": 3.2},
        "gesture": "TWO_OPEN_HANDS",
        "state": "MANIPULATION"
    }
    
    print("Testing dispatcher with MANIPULATION_ACTIVE command:")
    result = dispatcher.dispatch_intent(test_intent)
    print(f"Result: {result}")
