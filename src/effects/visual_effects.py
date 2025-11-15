"""Visual effects for button presses and interactions."""

import time
import math


def create_explosion_effect(midi_out, center_x, center_y, color=(255, 255, 255), duration=0.1, max_radius=3):
    """Creates a temporary explosion effect around a pressed key.

    Args:
        midi_out: MIDI output device
        center_x: X coordinate of explosion center
        center_y: Y coordinate of explosion center
        color: RGB color tuple for explosion
        duration: Duration of effect in seconds
        max_radius: Maximum radius of explosion
    """
    start_time = time.time()

    while time.time() - start_time < duration:
        progress = (time.time() - start_time) / duration
        current_radius = progress * max_radius

        # Draw the explosion effect
        for y in range(max(0, int(center_y - max_radius)), min(9, int(center_y + max_radius + 1))):
            for x in range(max(0, int(center_x - max_radius)), min(9, int(center_x + max_radius + 1))):
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx*dx + dy*dy)

                if distance <= current_radius:
                    # Calculate intensity based on distance and time
                    intensity = (1.0 - distance/max_radius) * (1.0 - progress)
                    r = int(color[0] * intensity)
                    g = int(color[1] * intensity)
                    b = int(color[2] * intensity)

                    from ..hardware.launchpad import set_color
                    set_color(midi_out, x, y, r, g, b)

        time.sleep(0.01)
