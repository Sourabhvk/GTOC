import cv2
import mediapipe as mp

from Gestures import GestureDetector

# Use legacy `mp.solutions` API (requires mediapipe==0.10.14)
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Initialize the Hands processor and gesture detector.
hands = mp_hands.Hands()
gesture_detector = GestureDetector()

# Open default camera.
cap = cv2.VideoCapture(0)

# Main loop: capture, detect, annotate, display.
while True:
    # Read camera frame.
    ret, frame = cap.read()
    if not ret:
        break

    # Mirror frame.
    frame = cv2.flip(frame, 1)

    # BGR → RGB for MediaPipe.
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect hand landmarks.
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            # Draw landmarks and connections.
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2),
            )

            # Detect gesture label from landmarks.
            gesture = gesture_detector.detect(hand_landmarks)

            # Overlay gesture text when available.
            if gesture:
                cv2.putText(
                    frame,
                    gesture,
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )

    # Show frame.
    cv2.imshow("Hand Tracking", frame)

    # Exit on Esc.
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Cleanup.
cap.release()
cv2.destroyAllWindows()