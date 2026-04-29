"""
Integration example: Connecting gesture detection to NX bridge.

This module demonstrates how to wire the gesture detector output
through the NX bridge dispatcher to execute NX axis rotation and
panning commands.
"""

import sys
import logging
from pathlib import Path

# Add src directory to path for imports
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from Gestures import GestureDetector
from nx_bridge import NXBridge, CommandDispatcher


class GestureToNXAdapter:
    """
    Runtime adapter connecting gesture detection pipeline to NX execution.
    
    Manages:
    - Gesture detector initialization
    - NX bridge initialization
    - Intent dispatch pipeline
    - Logging and diagnostics
    """
    
    def __init__(self, nxopen_session=None):
        """
        Initialize the gesture-to-NX adapter.
        
        Args:
            nxopen_session: NX.Session object from NX Open. 
                          If None, runs in dry-run/test mode.
        """
        self.gesture_detector = GestureDetector()
        self.nx_bridge = NXBridge(nxopen_session)
        self.dispatcher = CommandDispatcher(self.nx_bridge)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("GestureToNXAdapter initialized")
    
    def process_hand_landmarks(self, hand_landmarks, handedness=None):
        """
        Process MediaPipe hand landmarks and dispatch any resulting commands to NX.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks (single hand or list)
            handedness: Optional handedness info
        
        Returns:
            Dict with detection info and execution status
        """
        # Step 1: Detect gesture from hand landmarks
        detection = self.gesture_detector.detect(hand_landmarks, handedness)
        
        if not detection:
            return {"success": False, "reason": "No detection"}
        
        # Step 2: Extract intent from detection
        intent = detection.get("intent")
        if not intent:
            return {
                "success": False,
                "reason": "No intent",
                "detection": detection
            }
        
        # Step 3: Dispatch intent to NX bridge
        dispatch_result = self.dispatcher.dispatch_intent(detection)
        
        return {
            "success": dispatch_result,
            "detection": detection,
            "intent": intent
        }
    
    def process_batch_detections(self, detection_list):
        """
        Process multiple gesture detections (useful for logging/testing).
        
        Args:
            detection_list: List of detection dicts from gesture detector
        
        Returns:
            List of dispatch results
        """
        results = []
        for detection in detection_list:
            result = self.dispatcher.dispatch_intent(detection)
            results.append(result)
        return results


# Example usage for testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(name)s - %(message)s"
    )
    
    # Initialize adapter in dry-run mode (no NX session)
    adapter = GestureToNXAdapter()
    
    # Simulate some gesture detections
    print("=== Example: Processing gesture intents ===\n")
    
    # Example 1: Rotate Z (1-finger gesture)
    example_detection_1 = {
        "intent": "ROTATE_Z",
        "values": {"axis": "Z", "direction": "CLOCKWISE"},
        "gesture": "1_FINGER",
        "state": "ROTATING",
        "display": "1-FINGER CLOCKWISE - ROTATE Z"
    }
    
    result = adapter.dispatcher.dispatch_intent(example_detection_1)
    print(f"ROTATE_Z command: {result}")
    print()
    
    # Example 2: Rotate X (2-finger gesture)
    example_detection_2 = {
        "intent": "ROTATE_X",
        "values": {"axis": "X", "direction": "COUNTERCLOCKWISE"},
        "gesture": "2_FINGER",
        "state": "ROTATING",
        "display": "2-FINGER COUNTERCLOCKWISE - ROTATE X"
    }
    
    result = adapter.dispatcher.dispatch_intent(example_detection_2)
    print(f"ROTATE_X command: {result}")
    print()
    
    # Example 3: Pan left (open hand motion)
    example_detection_3 = {
        "intent": "MOVE_LEFT",
        "values": {"dx": -0.05, "direction": "LEFT"},
        "gesture": "ONE_HAND_OPEN",
        "state": "TRACKING",
        "display": "MOVE LEFT"
    }
    
    result = adapter.dispatcher.dispatch_intent(example_detection_3)
    print(f"MOVE_LEFT command: {result}")
    print()
    
    # Example 4: Manipulation active (two hands)
    example_detection_4 = {
        "intent": "MANIPULATION_ACTIVE",
        "values": {"elapsed_sec": 3.5},
        "gesture": "TWO_OPEN_HANDS",
        "state": "MANIPULATION",
        "display": "TWO OPEN - ACTIVE"
    }
    
    result = adapter.dispatcher.dispatch_intent(example_detection_4)
    print(f"MANIPULATION_ACTIVE command: {result}")
