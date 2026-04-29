import math


class PanSignalStabilizer:
    """
    PID-like stabilizer for pan-style motion signals.

    It smooths noisy dx/dy values, suppresses tiny movement near zero,
    and returns a stable direction label for display or downstream control.
    """

    def __init__(self, kp=0.65, ki=0.05, kd=0.18, deadzone=0.005, output_limit=1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.deadzone = deadzone
        self.output_limit = output_limit

        self._integral_x = 0.0
        self._integral_y = 0.0
        self._prev_error_x = 0.0
        self._prev_error_y = 0.0

    def reset(self):
        self._integral_x = 0.0
        self._integral_y = 0.0
        self._prev_error_x = 0.0
        self._prev_error_y = 0.0

    def update(self, dx, dy):
        """
        Return a smoothed pan vector and a direction label.

        Output keys:
            x, y, magnitude, direction, stable
        """
        if abs(dx) < self.deadzone:
            dx = 0.0
        if abs(dy) < self.deadzone:
            dy = 0.0

        error_x = dx
        error_y = dy

        self._integral_x = self._clamp(self._integral_x + error_x, -1.0, 1.0)
        self._integral_y = self._clamp(self._integral_y + error_y, -1.0, 1.0)

        derivative_x = error_x - self._prev_error_x
        derivative_y = error_y - self._prev_error_y

        output_x = (
            self.kp * error_x
            + self.ki * self._integral_x
            + self.kd * derivative_x
        )
        output_y = (
            self.kp * error_y
            + self.ki * self._integral_y
            + self.kd * derivative_y
        )

        self._prev_error_x = error_x
        self._prev_error_y = error_y

        output_x = self._clamp(output_x, -self.output_limit, self.output_limit)
        output_y = self._clamp(output_y, -self.output_limit, self.output_limit)

        magnitude = (output_x * output_x + output_y * output_y) ** 0.5
        stable = magnitude >= self.deadzone

        if not stable:
            direction = "STILL"
        else:
            direction = self._direction_from_vector(output_x, output_y)

        return {
            "x": output_x,
            "y": output_y,
            "magnitude": magnitude,
            "direction": direction,
            "stable": stable,
        }

    def _clamp(self, value, low, high):
        return max(low, min(high, value))

    def _direction_from_vector(self, x, y):
        angle = math.degrees(math.atan2(-y, x))

        if -22.5 <= angle < 22.5:
            return "RIGHT"
        if 22.5 <= angle < 67.5:
            return "TOP RIGHT"
        if 67.5 <= angle < 112.5:
            return "TOP"
        if 112.5 <= angle < 157.5:
            return "TOP LEFT"
        if angle >= 157.5 or angle < -157.5:
            return "LEFT"
        if -157.5 <= angle < -112.5:
            return "BOTTOM LEFT"
        if -112.5 <= angle < -67.5:
            return "BOTTOM"
        return "BOTTOM RIGHT"