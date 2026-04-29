import math
import time


class GestureDetector:
    """
    Simplified CAD Navigation Gesture Detector.

    Input:
        - One MediaPipe hand_landmarks object
        OR
        - results.multi_hand_landmarks list
        - (Optional) handedness list for left/right detection

    Output:
        Dictionary with:
            state
            gesture
            intent
            values
            display

    Gestures:
        1. NO_HAND - no hands detected
        2. TWO_OPEN_HANDS - both hands open, timer-based activation
        3. ONE_HAND_OPEN - single open hand tracking direction
        4. 1_FINGER - index only, rotates Z-axis
        5. 2_FINGER - index+middle, rotates X-axis
        6. THUMB_UP - thumb raised, rotates Y-axis

    Rotation direction:
        - LEFT hand: clockwise incremental
        - RIGHT hand: counterclockwise incremental
    """

    def __init__(self):
        self.state = "IDLE"
        
        # Two-hand open hands timer for manipulation mode
        self.two_hand_open_start_time = None
        self.two_hand_open_threshold_sec = 3.0
        
        # One-hand open motion tracking
        self.open_hand_prev_pos = None
        self.motion_threshold = 0.015  # Normalized distance to register motion (lowered for sensitivity)

    # -------------------------
    # Public API
    # -------------------------

    def detect(self, hand_input, handedness_list=None):
        """
        Main detection function.

        Args:
            hand_input: landmarks list or single landmark object
            handedness_list: optional list of Handedness objects from MediaPipe

        Returns:
            Dictionary with state, gesture, intent, values, display
        """
        hands = self._normalize_input(hand_input)

        if len(hands) == 0:
            self.state = "IDLE"
            self.two_hand_open_start_time = None
            self.open_hand_prev_pos = None

            return self._result(
                state="IDLE",
                gesture="NO_HAND",
                intent=None,
                values={},
                display="NO HAND"
            )

        if len(hands) == 1:
            return self._detect_one_hand(hands[0], handedness_list)

        if len(hands) >= 2:
            return self._detect_two_hand(
                hands[0], hands[1], handedness_list
            )

    # -------------------------
    # One-hand logic
    # -------------------------

    def _detect_one_hand(self, hand, handedness_list=None):
        """
        Single hand detection.
        Resets two-hand timer.
        Routes to open-hand motion or finger-counting rotation.
        """
        self.two_hand_open_start_time = None

        if self.is_open_hand(hand):
            return self._detect_open_hand_motion(hand)

        # Thumb-up rotation gesture replaces the old 3-finger path.
        if self.is_thumb_up(hand):
            return self._detect_thumb_rotation(hand, handedness_list)

        # Finger-counting rotation gestures
        open_finger_count = self._count_open_fingers(hand)

        if open_finger_count in [1, 2]:
            return self._detect_finger_rotation(
                hand, open_finger_count, handedness_list
            )

        # Fallback
        self.open_hand_prev_pos = None
        return self._result(
            state="IDLE",
            gesture="UNKNOWN",
            intent=None,
            values={},
            display="UNKNOWN"
        )

    def _detect_open_hand_motion(self, hand):
        """
        One open hand: track motion direction (UP/DOWN/LEFT/RIGHT).
        """
        wrist = self._point(hand, 0)

        if self.open_hand_prev_pos is None:
            self.open_hand_prev_pos = wrist
            return self._result(
                state="TRACKING",
                gesture="ONE_HAND_OPEN",
                intent="READY",
                values={},
                display="OPEN - TRACKING READY"
            )

        # Calculate motion delta
        dx = wrist["x"] - self.open_hand_prev_pos["x"]
        dy = wrist["y"] - self.open_hand_prev_pos["y"]

        motion_mag = math.sqrt(dx * dx + dy * dy)

        if motion_mag < self.motion_threshold:
            return self._result(
                state="TRACKING",
                gesture="ONE_HAND_OPEN",
                intent="STILL",
                values={},
                display="OPEN - STILL"
            )

        # Determine dominant direction
        abs_dx = abs(dx)
        abs_dy = abs(dy)

        if abs_dx > abs_dy:
            direction = "RIGHT" if dx > 0 else "LEFT"
        else:
            direction = "DOWN" if dy > 0 else "UP"

        self.open_hand_prev_pos = wrist

        return self._result(
            state="TRACKING",
            gesture="ONE_HAND_OPEN",
            intent=f"MOVE_{direction}",
            values={"dx": dx, "dy": dy, "direction": direction},
            display=f"MOVE {direction}"
        )

    def _detect_finger_rotation(self, hand, open_finger_count, handedness_list=None):
        """
        Finger-counting rotation: 1, 2, or 3 fingers extended.
        Left hand: clockwise rotation, Right hand: counterclockwise rotation.
        Each frame increments rotation_angle by rotation_speed.
        """
        self.open_hand_prev_pos = None

        hand_side = self._hand_side(handedness_list, 0)

        # Map finger count to axis
        axis_map = {
            1: "Z",
            2: "X",
            3: "Y"
        }
        axis = axis_map.get(open_finger_count, "Z")

        # Determine rotation direction and update angle
        if hand_side == "LEFT":
            direction = "CLOCKWISE"
        elif hand_side == "RIGHT":
            direction = "COUNTERCLOCKWISE"
        else:
            direction = "CLOCKWISE"

        gesture_name = f"{open_finger_count}_FINGER"
        intent_name = f"ROTATE_{axis}"

        return self._result(
            state="ROTATING",
            gesture=gesture_name,
            intent=intent_name,
            values={
                "axis": axis,
                "direction": direction,
                "fingers": open_finger_count
            },
            display=f"{open_finger_count}-FINGER {direction} - ROTATE {axis}"
        )

    def _detect_thumb_rotation(self, hand, handedness_list=None):
        """
        Thumb up: rotate Y-axis.
        Left hand = clockwise, Right hand = counterclockwise.
        """
        self.open_hand_prev_pos = None

        hand_side = self._hand_side(handedness_list, 0)

        axis = "Y"

        if hand_side == "LEFT":
            direction = "CLOCKWISE"
        elif hand_side == "RIGHT":
            direction = "COUNTERCLOCKWISE"
        else:
            direction = "CLOCKWISE"

        return self._result(
            state="ROTATING",
            gesture="THUMB_UP",
            intent="ROTATE_Y",
            values={
                "axis": axis,
                "direction": direction,
                "gesture": "THUMB_UP"
            },
            display=f"THUMB UP {direction} - ROTATE Y"
        )

    # -------------------------
    # Two-hand logic
    # -------------------------

    def _detect_two_hand(self, hand_a, hand_b, handedness_list=None):
        """
        Two-hand detection.
        Only detects: both open hands (waiting for 3-sec threshold).
        Mixed or other states reset the timer and return IDLE.
        """
        both_open = self.is_open_hand(hand_a) and self.is_open_hand(hand_b)

        if both_open:
            return self._detect_two_open_hands(hand_a, hand_b)

        # Any other two-hand state: reset timer and return IDLE
        self.two_hand_open_start_time = None
        return self._result(
            state="IDLE",
            gesture="TWO_HANDS_MIXED",
            intent=None,
            values={},
            display="TWO HANDS - NOT BOTH OPEN"
        )

    def _detect_two_open_hands(self, hand_a, hand_b):
        """
        Two open hands: start/stop manipulation mode timer.
        < 3 sec: waiting
        >= 3 sec: active manipulation
        """
        if self.two_hand_open_start_time is None:
            self.two_hand_open_start_time = time.time()

        elapsed = time.time() - self.two_hand_open_start_time

        if elapsed < self.two_hand_open_threshold_sec:
            return self._result(
                state="WAITING",
                gesture="TWO_OPEN_HANDS",
                intent="STABILIZING",
                values={"elapsed_sec": round(elapsed, 1)},
                display=f"TWO OPEN - {elapsed:.1f}s..."
            )
        else:
            return self._result(
                state="MANIPULATION",
                gesture="TWO_OPEN_HANDS",
                intent="MANIPULATION_ACTIVE",
                values={"elapsed_sec": round(elapsed, 1)},
                display="TWO OPEN - ACTIVE"
            )

    # -------------------------
    # Gesture classification
    # -------------------------

    def get_finger_states(self, hand):
        """
        Returns open/closed state for 4 fingers (index, middle, ring, pinky).
        Thumb is not included in this state; use separate thumb detection.
        """
        fingers = {}

        tips = {
            "index": 8,
            "middle": 12,
            "ring": 16,
            "pinky": 20
        }

        pips = {
            "index": 6,
            "middle": 10,
            "ring": 14,
            "pinky": 18
        }

        for finger in tips:
            tip_y = hand.landmark[tips[finger]].y
            pip_y = hand.landmark[pips[finger]].y

            fingers[finger] = tip_y < pip_y

        return fingers

    def is_thumb_up(self, hand):
        """
        Thumb up: thumb tip above thumb IP, with the other four fingers closed.
        """
        fingers = self.get_finger_states(hand)
        if any(fingers.values()):
            return False

        thumb_tip = self._point(hand, 4)
        thumb_ip = self._point(hand, 3)

        return thumb_tip["y"] < thumb_ip["y"]

    def _count_open_fingers(self, hand):
        """
        Count the number of open fingers (index, middle, ring, pinky).
        For rotation gestures, we need exact finger counts: 1, 2, or 3.
        Returns: 0, 1, 2, 3, or 4
        """
        fingers = self.get_finger_states(hand)
        open_count = sum(1 for is_open in fingers.values() if is_open)

        # Ensure thumb is not interfering with 3-finger detection
        # Check thumb extension separately
        thumb_tip = self._point(hand, 4)
        thumb_base = self._point(hand, 2)
        thumb_dist = self._distance(thumb_tip, thumb_base)
        thumb_extended = thumb_dist > 0.08

        # If 3 fingers are open AND thumb is extended, that's not a clean 3-finger gesture
        # Require thumb to be relatively closed for 3-finger rotation
        if open_count == 3 and thumb_extended:
            # This is likely a 4-finger open hand, not a 3-finger gesture
            return 4

        return open_count

    def is_open_hand(self, hand):
        """
        Open hand: all 4 fingers extended.
        """
        fingers = self.get_finger_states(hand)
        open_count = sum(1 for is_open in fingers.values() if is_open)

        return open_count == 4

    def is_fist(self, hand):
        """
        Closed fist: all 4 fingers closed.
        (Currently unused but kept for compatibility.)
        """
        fingers = self.get_finger_states(hand)
        open_count = sum(1 for is_open in fingers.values() if is_open)

        return open_count == 0

    # -------------------------
    # Geometry helpers
    # -------------------------

    def _point(self, hand, index):
        """Extract x, y, z from a landmark."""
        lm = hand.landmark[index]

        return {
            "x": lm.x,
            "y": lm.y,
            "z": lm.z
        }

    def _distance(self, p1, p2):
        """Euclidean distance between two points."""
        dx = p1["x"] - p2["x"]
        dy = p1["y"] - p2["y"]
        dz = p1["z"] - p2["z"]

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _centroid(self, p1, p2):
        """Midpoint between two points."""
        return {
            "x": (p1["x"] + p2["x"]) / 2.0,
            "y": (p1["y"] + p2["y"]) / 2.0,
            "z": (p1["z"] + p2["z"]) / 2.0
        }

    # -------------------------
    # State helpers
    # -------------------------

    def _normalize_input(self, hand_input):
        """Normalize hand input to a list of landmarks."""
        if hand_input is None:
            return []

        if isinstance(hand_input, list):
            return hand_input

        if isinstance(hand_input, tuple):
            return list(hand_input)

        return [hand_input]

    def _hand_side(self, handedness_list, index):
        """Return LEFT/RIGHT when MediaPipe handedness is available."""
        if not handedness_list or len(handedness_list) <= index:
            return "UNKNOWN"

        try:
            return handedness_list[index].classification[0].label.upper()
        except:
            return "UNKNOWN"

    def _result(self, state, gesture, intent, values, display):
        """Build a result dictionary."""
        return {
            "state": state,
            "gesture": gesture,
            "intent": intent,
            "values": values,
            "display": display
        }