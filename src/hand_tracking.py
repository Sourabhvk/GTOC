import cv2
import mediapipe as mp
import time

from Gestures import GestureDetector
from pan_stabilizer import PanSignalStabilizer

# Use legacy `mp.solutions` API (requires mediapipe==0.10.14)
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Initialize the Hands processor and gesture detector.
hands = mp_hands.Hands()
gesture_detector = GestureDetector()
pan_stabilizer = PanSignalStabilizer()

# Open default camera.
# Higher capture size can expose more of the sensor area on some webcams.
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
current_display_text = ""
last_console_signature = None
last_console_time = 0.0
last_display_time = 0.0
console_interval_sec = 0.5
display_interval_sec = 0.2

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
        # Draw landmarks for each detected hand.
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2),
            )

        # Call the detector once with all detected hands; it returns a dict.
        detection = gesture_detector.detect(
            result.multi_hand_landmarks,
            handedness_list=getattr(result, "multi_handedness", None)
        )
    else:
        detection = gesture_detector.detect(None)

    now = time.monotonic()
    display_text = detection.get("display") if detection else ""

    intent = detection.get("intent") if detection else None

    if isinstance(intent, str) and intent.startswith("MOVE_"):
        values = detection.get("values", {})
        smoothed_pan = pan_stabilizer.update(values.get("dx", 0.0), values.get("dy", 0.0))
        if smoothed_pan["stable"]:
            current_display_text = f"PAN {smoothed_pan['direction']}"
            display_text = current_display_text
        else:
            display_text = detection.get("display")
    else:
        pan_stabilizer.reset()

    if display_text:
        if (
            display_text != current_display_text
            and (now - last_display_time) >= display_interval_sec
        ):
            current_display_text = display_text
            last_display_time = now
    else:
        current_display_text = ""

    # Display the human-friendly label when one is available.
    if current_display_text:
        cv2.putText(
            frame,
            current_display_text,
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    console_signature = (
        detection.get("state"),
        detection.get("gesture"),
        detection.get("intent"),
        detection.get("display"),
    )

    if (
        console_signature != last_console_signature
        and (now - last_console_time) >= console_interval_sec
    ):
        print(
            f"{detection.get('display')} | state={detection.get('state')} "
            f"gesture={detection.get('gesture')} intent={detection.get('intent')}"
        )
        last_console_signature = console_signature
        last_console_time = now

    # Show frame.
    cv2.imshow("Hand Tracking", frame)

    # Exit on Esc.
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Cleanup.
cap.release()
cv2.destroyAllWindows()