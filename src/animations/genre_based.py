"""Genre-based animations for different music styles."""

import time
import colorsys
import math
import random


def electronic_animation(midi_out, should_run, current_animation):
    """Fast, geometric patterns for electronic music."""
    center_x, center_y = 4, 4

    while should_run() and current_animation() == 'electronic':
        # Create expanding squares with rotation
        for size in range(5):
            if current_animation() != 'electronic':
                break
            from ..hardware.launchpad import clear_all
            clear_all(midi_out)

            # Draw expanding square with rotation
            angle = time.time() * 2  # Rotation angle
            for i in range(size + 1):
                for offset in range(8):
                    # Calculate rotated corner positions
                    x = center_x + i * math.cos(angle + offset * math.pi/4)
                    y = center_y + i * math.sin(angle + offset * math.pi/4)

                    # Convert to grid coordinates
                    grid_x = int(round(x))
                    grid_y = int(round(y))

                    if 0 <= grid_x < 9 and 0 <= grid_y < 9:
                        # Create color cycling effect
                        hue = (time.time() / 2 + i / 5) % 1.0
                        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, grid_x, grid_y, r, g, b)

            time.sleep(0.1)


def classical_animation(midi_out, should_run, current_animation):
    """Smooth, flowing waves for classical music."""
    while should_run() and current_animation() == 'classical':
        phase = time.time() * 2
        for y in range(9):
            for x in range(9):
                # Create gentle sine wave pattern
                wave = math.sin(phase + (x + y) / 4.0) * 0.5 + 0.5
                r = int(wave * 100)  # Soft red
                g = int(wave * 150)  # Medium green
                b = int(wave * 255)  # Strong blue
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)
        time.sleep(0.05)


def rock_animation(midi_out, should_run, current_animation):
    """Aggressive, flashing patterns for rock music."""
    patterns = [
        # Diagonal strikes
        [(x, x) for x in range(9)] + [(x, 8-x) for x in range(9)],
        # X pattern
        [(0,0), (1,1), (2,2), (3,3), (4,4), (5,5), (6,6), (7,7), (8,8),
         (0,8), (1,7), (2,6), (3,5), (4,4), (5,3), (6,2), (7,1), (8,0)],
        # Border flash
        [(x, 0) for x in range(9)] + [(x, 8) for x in range(9)] +
        [(0, y) for y in range(1, 8)] + [(8, y) for y in range(1, 8)],
        # Random explosion pattern
        [(random.randint(0, 8), random.randint(0, 8)) for _ in range(20)]
    ]

    while should_run() and current_animation() == 'rock':
        for pattern in patterns:
            if current_animation() != 'rock':
                break

            # Flash pattern in red/orange
            for intensity in [255, 100, 255, 50]:  # More varied intensity
                from ..hardware.launchpad import clear_all
                clear_all(midi_out)
                for x, y in pattern:
                    # Add some random variation to make it more dynamic
                    r = min(255, intensity + random.randint(-20, 20))
                    g = min(255, intensity//3 + random.randint(-10, 10))
                    b = min(255, intensity//6 + random.randint(-5, 5))
                    from ..hardware.launchpad import set_color
                    set_color(midi_out, x, y, r, g, b)
                time.sleep(0.05)

            # Add random sparks
            for _ in range(3):
                x, y = random.randint(0, 8), random.randint(0, 8)
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, 255, 200, 0)  # Bright flash
                time.sleep(0.02)

            time.sleep(0.1)


def jazz_animation(midi_out, should_run, current_animation):
    """Complex, evolving patterns for jazz music."""
    points = [(random.randint(0, 8), random.randint(0, 8)) for _ in range(5)]
    colors = [(random.randint(100, 255), random.randint(50, 150), random.randint(0, 100))
              for _ in range(5)]

    while should_run() and current_animation() == 'jazz':
        from ..hardware.launchpad import clear_all
        clear_all(midi_out)

        # Smooth movement of light points
        for i in range(len(points)):
            x, y = points[i]
            r, g, b = colors[i]

            # Draw smooth gradient around each point
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < 9 and 0 <= new_y < 9:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance < 2:
                            intensity = (2 - distance) / 2
                            from ..hardware.launchpad import set_color
                            set_color(midi_out, new_x, new_y,
                                    int(r * intensity),
                                    int(g * intensity),
                                    int(b * intensity))

            # Slowly move points
            points[i] = ((x + random.uniform(-0.2, 0.2)) % 9,
                        (y + random.uniform(-0.2, 0.2)) % 9)

        time.sleep(0.05)


def ambient_animation(midi_out, should_run, current_animation):
    """Slow, peaceful patterns for ambient music."""
    while should_run() and current_animation() == 'ambient':
        phase = time.time() * 0.5
        for y in range(9):
            for x in range(9):
                # Create very slow moving color pattern
                hue = (math.sin(phase + x/5.0) * math.cos(phase + y/5.0) + 1) / 2
                r, g, b = [int(c * 100) for c in colorsys.hsv_to_rgb(hue, 0.5, 0.8)]
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)
        time.sleep(0.1)
