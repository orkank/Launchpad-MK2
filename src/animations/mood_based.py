"""Mood-based animations for different emotional contexts."""

import time
import colorsys
import math
import random


def synthwave_animation(midi_out, should_run, current_animation):
    """Retro synthwave style animation with sunset colors."""
    while should_run() and current_animation() == 'synthwave':
        phase = time.time() * 0.5
        for y in range(9):
            for x in range(9):
                # Create sunset gradient (pink to purple to blue)
                height_factor = y / 8.0
                wave = math.sin(phase + x/3.0 + y/5.0) * 0.5 + 0.5

                # Sunset colors
                r = int((255 * (1 - height_factor) + 150 * height_factor) * wave)
                g = int((100 * (1 - height_factor) + 50 * height_factor) * wave)
                b = int((150 * (1 - height_factor) + 255 * height_factor) * wave)

                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)
        time.sleep(0.05)


def lofi_animation(midi_out, should_run, current_animation):
    """Calm, smooth transitions for lo-fi music."""
    points = [(4, 4)]  # Start with center point
    colors = [(70, 130, 180)]  # Soft blue

    while should_run() and current_animation() == 'lofi':
        from ..hardware.launchpad import clear_all
        clear_all(midi_out)

        # Slowly move points and create new ones
        if random.random() < 0.02:  # 2% chance to add new point
            points.append((random.randint(0, 8), random.randint(0, 8)))
            colors.append((
                random.randint(50, 150),  # Soft colors
                random.randint(50, 150),
                random.randint(50, 150)
            ))

            if len(points) > 4:  # Limit number of points
                points.pop(0)
                colors.pop(0)

        # Draw smooth gradients
        for i, (x, y) in enumerate(points):
            r, g, b = colors[i]
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < 9 and 0 <= new_y < 9:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance < 4:
                            intensity = (4 - distance) / 4
                            from ..hardware.launchpad import set_color
                            set_color(midi_out, new_x, new_y,
                                    int(r * intensity),
                                    int(g * intensity),
                                    int(b * intensity))

            # Slowly move points
            points[i] = ((x + random.uniform(-0.1, 0.1)) % 9,
                        (y + random.uniform(-0.1, 0.1)) % 9)

        time.sleep(0.1)


def meditation_animation(midi_out, should_run, current_animation):
    """Peaceful, breathing-like animation for meditation music."""
    while should_run() and current_animation() == 'meditation':
        phase = time.time() * 0.5  # Slow breathing rate
        breath = math.sin(phase) * 0.5 + 0.5  # 0 to 1

        for y in range(9):
            for x in range(9):
                # Calculate distance from center
                dx = x - 4
                dy = y - 4
                distance = math.sqrt(dx*dx + dy*dy)

                # Create breathing circle effect
                intensity = max(0, 1 - (distance / (4 * breath + 2)))

                # Peaceful colors (soft blue/green)
                r = int(20 * intensity)
                g = int(100 * intensity)
                b = int(150 * intensity)

                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)

        time.sleep(0.05)


def party_animation(midi_out, should_run, current_animation):
    """Energetic, colorful animation for party music."""
    while should_run() and current_animation() == 'party':
        # Create multiple moving light sources
        t = time.time() * 2
        sources = [
            (math.sin(t) * 4 + 4, math.cos(t) * 4 + 4),
            (math.sin(t * 1.5) * 4 + 4, math.cos(t * 1.5) * 4 + 4),
            (math.sin(t * 0.7) * 4 + 4, math.cos(t * 0.7) * 4 + 4)
        ]

        for y in range(9):
            for x in range(9):
                max_intensity = 0
                hue = 0

                # Calculate influence from each light source
                for i, (sx, sy) in enumerate(sources):
                    dx = x - sx
                    dy = y - sy
                    distance = math.sqrt(dx*dx + dy*dy)
                    intensity = max(0, 1 - distance/4)

                    if intensity > max_intensity:
                        max_intensity = intensity
                        hue = (t * 0.5 + i * 0.3) % 1.0

                # Convert HSV to RGB with full saturation
                r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, max_intensity)]
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)

        time.sleep(0.05)


def focus_animation(midi_out, should_run, current_animation):
    """Subtle, non-distracting animation for focus/study music."""
    phase = 0
    while should_run() and current_animation() == 'focus':
        # Create subtle moving gradient
        for y in range(9):
            for x in range(9):
                # Very subtle movement
                value = (math.sin(phase/10 + x/5) * math.cos(phase/15 + y/5) + 1) / 2

                # Cool, non-distracting colors (mainly blue with hints of purple)
                r = int(20 * value)
                g = int(40 * value)
                b = int(80 * value)

                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)

        phase += 0.1
        time.sleep(0.1)
