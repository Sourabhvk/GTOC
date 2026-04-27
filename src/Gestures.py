class GestureDetector:
    # Lightweight heuristic gesture detector.
    def is_open_hand(self, hand_landmarks):
        fingers = []

        # Tips and PIP indices for index→pinky.
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]

        for tip, pip in zip(tips, pips):
            tip_y = hand_landmarks.landmark[tip].y
            pip_y = hand_landmarks.landmark[pip].y

            # True when fingertip is above the PIP joint (extended).
            fingers.append(tip_y < pip_y)

        # Open when all four fingers are extended.
        return all(fingers)

    def detect(self, hand_landmarks):
        # Map checks to gesture labels.
        if self.is_open_hand(hand_landmarks):
            return "OPEN_HAND"

        return "UNKNOWN"