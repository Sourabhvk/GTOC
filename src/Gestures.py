import math


class GestureDetector:
    """
    Gesture layer only.

    Input:
        - One MediaPipe hand_landmarks object
        OR
        - results.multi_hand_landmarks list

    Output:
        Dictionary with:
            state
            gesture
            intent
            values
            display
    """

    def __init__(self):
        self.state = "IDLE"

        # One-hand grab reference
        self.ref_wrist = None
        self.ref_yaw = None

        # Two-hand reference
        self.ref_two_hand_distance = None
        self.ref_two_hand_centroid = None

        # Thresholds
        self.yaw_deadzone_deg = 5.0
        self.pitch_deadzone = 0.025
        self.zoom_deadzone = 0.025
        self.pan_deadzone = 0.025

        # Output gains
        self.pitch_gain = 180.0
        self.pan_gain = 1.0
        self.zoom_gain = 5.0

    # -------------------------
    # Public API
    # -------------------------

    def detect(self, hand_input):
        """
        Main function to call from your camera loop.

        Recommended:
            gesture_result = gesture_detector.detect(results.multi_hand_landmarks)

        If only one hand is passed:
            gesture_result = gesture_detector.detect(hand_landmarks)
        """

        hands = self._normalize_input(hand_input)

        if len(hands) == 0:
            return self._no_hand_result()

        if len(hands) >= 2:
            return self._detect_two_hand(hands[0], hands[1])

        return self._detect_one_hand(hands[0])

    # -------------------------
    # One-hand logic
    # -------------------------

    def _detect_one_hand(self, hand):
        # reset two-hand references when only one hand is active
        self.ref_two_hand_distance = None
        self.ref_two_hand_centroid = None

        if self.is_open_hand(hand):
            if self.state in ["GRAB", "MANIPULATE"]:
                self._reset_one_hand_reference()
                self.state = "IDLE"

                return self._result(
                    state="RELEASE",
                    gesture="OPEN_HAND",
                    intent="RELEASE",
                    values={},
                    display="RELEASE"
                )

            self.state = "IDLE"

            return self._result(
                state="IDLE",
                gesture="OPEN_HAND",
                intent=None,
                values={},
                display="OPEN_HAND / IDLE"
            )

        if self.is_fist(hand):
            wrist = self._point(hand, 0)
            yaw = self._palm_yaw(hand)

            # Re-lock one-hand references when state changed from two-hand mode.
            if self.state == "IDLE" or self.ref_wrist is None or self.ref_yaw is None:
                self.state = "GRAB"
                self.ref_wrist = wrist
                self.ref_yaw = yaw

                return self._result(
                    state="GRAB",
                    gesture="FIST",
                    intent="GRAB_LOCKED",
                    values={},
                    display="GRAB LOCKED"
                )

            yaw_delta_deg = self._angle_delta_deg(self.ref_yaw, yaw)
            pitch_delta_raw = -(wrist["y"] - self.ref_wrist["y"])

            if (
                abs(yaw_delta_deg) > self.yaw_deadzone_deg
                or abs(pitch_delta_raw) > self.pitch_deadzone
            ):
                self.state = "MANIPULATE"

                return self._result(
                    state="MANIPULATE",
                    gesture="FIST",
                    intent="ROTATE_VIEW",
                    values={
                        "yaw_delta": yaw_delta_deg,
                        "pitch_delta": pitch_delta_raw * self.pitch_gain,
                        "mode": "absolute_from_grab_reference"
                    },
                    display="ROTATE_VIEW"
                )

            return self._result(
                state="GRAB",
                gesture="FIST",
                intent="GRAB_LOCKED",
                values={},
                display="GRAB HOLD"
            )

        return self._result(
            state=self.state,
            gesture="UNKNOWN",
            intent=None,
            values={},
            display="UNKNOWN"
        )

    # -------------------------
    # Two-hand logic
    # -------------------------

    def _detect_two_hand(self, hand_a, hand_b):
        # Two-hand mode overrides one-hand grab
        self.state = "MANIPULATE"
        self._reset_one_hand_reference()

        wrist_a = self._point(hand_a, 0)
        wrist_b = self._point(hand_b, 0)

        distance = self._distance(wrist_a, wrist_b)
        centroid = self._centroid(wrist_a, wrist_b)

        both_open = self.is_open_hand(hand_a) and self.is_open_hand(hand_b)
        both_fist = self.is_fist(hand_a) and self.is_fist(hand_b)

        if both_open:
            self._reset_two_hand_reference()
            self.state = "IDLE"

            return self._result(
                state="RELEASE",
                gesture="TWO_OPEN_HANDS",
                intent="RELEASE",
                values={},
                display="TWO HAND RELEASE"
            )

        if self.ref_two_hand_distance is None:
            self.ref_two_hand_distance = distance
            self.ref_two_hand_centroid = centroid

            return self._result(
                state="GRAB",
                gesture="TWO_HAND_READY",
                intent="TWO_HAND_REFERENCE_LOCKED",
                values={},
                display="TWO HAND REF LOCKED"
            )

        distance_delta = distance - self.ref_two_hand_distance

        centroid_dx = centroid["x"] - self.ref_two_hand_centroid["x"]
        centroid_dy = centroid["y"] - self.ref_two_hand_centroid["y"]

        # Two hands moving apart/together = zoom
        if abs(distance_delta) > self.zoom_deadzone:
            return self._result(
                state="MANIPULATE",
                gesture="TWO_HAND_PINCH_SPREAD",
                intent="ZOOM_VIEW",
                values={
                    "zoom_delta": distance_delta * self.zoom_gain,
                    "mode": "absolute_from_two_hand_reference"
                },
                display="ZOOM_VIEW"
            )

        # Two fists moving together = pan
        if both_fist and (
            abs(centroid_dx) > self.pan_deadzone
            or abs(centroid_dy) > self.pan_deadzone
        ):
            return self._result(
                state="MANIPULATE",
                gesture="TWO_FIST_MOVE",
                intent="PAN_VIEW",
                values={
                    "dx": centroid_dx * self.pan_gain,
                    "dy": centroid_dy * self.pan_gain,
                    "mode": "absolute_from_two_hand_reference"
                },
                display="PAN_VIEW"
            )

        if both_fist:
            return self._result(
                state="GRAB",
                gesture="TWO_FIST",
                intent="TWO_HAND_GRAB_LOCKED",
                values={},
                display="TWO HAND GRAB"
            )

        return self._result(
            state="MANIPULATE",
            gesture="TWO_HANDS_VISIBLE",
            intent=None,
            values={},
            display="TWO HAND READY"
        )

    # -------------------------
    # Gesture classification
    # -------------------------

    def get_finger_states(self, hand):
        """
        Returns open/closed state for 4 fingers.
        Thumb is ignored for now because thumb detection depends heavily on hand orientation.
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

    def is_open_hand(self, hand):
        fingers = self.get_finger_states(hand)
        open_count = sum(1 for is_open in fingers.values() if is_open)

        return open_count >= 3

    def is_fist(self, hand):
        fingers = self.get_finger_states(hand)
        open_count = sum(1 for is_open in fingers.values() if is_open)

        return open_count == 0

    # -------------------------
    # Geometry helpers
    # -------------------------

    def _point(self, hand, index):
        lm = hand.landmark[index]

        return {
            "x": lm.x,
            "y": lm.y,
            "z": lm.z
        }

    def _distance(self, p1, p2):
        dx = p1["x"] - p2["x"]
        dy = p1["y"] - p2["y"]
        dz = p1["z"] - p2["z"]

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _centroid(self, p1, p2):
        return {
            "x": (p1["x"] + p2["x"]) / 2.0,
            "y": (p1["y"] + p2["y"]) / 2.0,
            "z": (p1["z"] + p2["z"]) / 2.0
        }

    def _palm_yaw(self, hand):
        """
        Approximate palm yaw using the palm normal.

        Landmarks:
            0  = wrist
            5  = index MCP
            17 = pinky MCP
        """

        wrist = self._point(hand, 0)
        index_mcp = self._point(hand, 5)
        pinky_mcp = self._point(hand, 17)

        v1 = {
            "x": index_mcp["x"] - wrist["x"],
            "y": index_mcp["y"] - wrist["y"],
            "z": index_mcp["z"] - wrist["z"]
        }

        v2 = {
            "x": pinky_mcp["x"] - wrist["x"],
            "y": pinky_mcp["y"] - wrist["y"],
            "z": pinky_mcp["z"] - wrist["z"]
        }

        normal = self._cross(v1, v2)

        yaw = math.atan2(normal["x"], normal["z"])

        return yaw

    def _cross(self, a, b):
        return {
            "x": a["y"] * b["z"] - a["z"] * b["y"],
            "y": a["z"] * b["x"] - a["x"] * b["z"],
            "z": a["x"] * b["y"] - a["y"] * b["x"]
        }

    def _angle_delta_deg(self, start_angle, current_angle):
        delta = current_angle - start_angle

        while delta > math.pi:
            delta -= 2 * math.pi

        while delta < -math.pi:
            delta += 2 * math.pi

        return math.degrees(delta)

    # -------------------------
    # State helpers
    # -------------------------

    def _reset_one_hand_reference(self):
        self.ref_wrist = None
        self.ref_yaw = None

    def _reset_two_hand_reference(self):
        self.ref_two_hand_distance = None
        self.ref_two_hand_centroid = None

    def _no_hand_result(self):
        self.state = "IDLE"
        self._reset_one_hand_reference()
        self._reset_two_hand_reference()

        return self._result(
            state="IDLE",
            gesture="NO_HAND",
            intent=None,
            values={},
            display="NO HAND"
        )

    def _normalize_input(self, hand_input):
        if hand_input is None:
            return []

        if isinstance(hand_input, list):
            return hand_input

        if isinstance(hand_input, tuple):
            return list(hand_input)

        return [hand_input]

    def _result(self, state, gesture, intent, values, display):
        return {
            "state": state,
            "gesture": gesture,
            "intent": intent,
            "values": values,
            "display": display
        }