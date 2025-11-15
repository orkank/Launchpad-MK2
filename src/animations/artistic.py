"""Artistic and creative animation patterns."""

import time
import math
import random


def starfield_animation(midi_out, should_run, current_animation):
    """Starfield effect with twinkling stars."""
    colors = [(255, 255, 255), (200, 200, 255), (150, 150, 255),
              (100, 100, 200), (50, 50, 150)]
    from ..hardware.launchpad import clear_all
    clear_all(midi_out)

    for _ in range(40):
        if current_animation() != 'starfield':
            break

        # Create 3-5 new stars
        for _ in range(random.randint(3, 5)):
            x, y = random.randint(0, 7), random.randint(0, 7)
            color = random.choice(colors)
            from ..hardware.launchpad import set_color
            set_color(midi_out, x, y, *color)

        time.sleep(0.15)

        # Dim some random stars
        for _ in range(random.randint(2, 4)):
            x, y = random.randint(0, 7), random.randint(0, 7)
            from ..hardware.launchpad import set_color
            set_color(midi_out, x, y, 0, 0, 0)


def geometric_animation(midi_out, should_run, current_animation):
    """Geometric shapes forming and transforming - faster version."""
    from ..hardware.launchpad import clear_all, set_color
    clear_all(midi_out)

    # Draw square - faster transitions
    for size in range(1, 5):
        if current_animation() != 'geometric':
            break
        for i in range(size):
            # Top and bottom edges
            set_color(midi_out, 4-size//2+i, 4-size//2, 255, 0, 255)
            set_color(midi_out, 4-size//2+i, 4+size//2-1, 255, 0, 255)
            # Left and right edges
            set_color(midi_out, 4-size//2, 4-size//2+i, 255, 0, 255)
            set_color(midi_out, 4+size//2-1, 4-size//2+i, 255, 0, 255)
        time.sleep(0.15)  # Faster transition (was 0.3)
        clear_all(midi_out)

    # Draw diamond - faster transitions
    for size in range(1, 5):
        if current_animation() != 'geometric':
            break
        set_color(midi_out, 4, 4-size, 0, 255, 255)
        set_color(midi_out, 4+size, 4, 0, 255, 255)
        set_color(midi_out, 4, 4+size, 0, 255, 255)
        set_color(midi_out, 4-size, 4, 0, 255, 255)
        time.sleep(0.15)  # Faster transition (was 0.3)
        clear_all(midi_out)

    # Add rapid triangle rotation
    for angle in range(0, 360, 45):
        if current_animation() != 'geometric':
            break
        rad = math.radians(angle)
        for r in range(1, 4):
            for i in range(3):
                ang = rad + i * 2 * math.pi / 3
                x = int(4 + r * math.cos(ang))
                y = int(4 + r * math.sin(ang))
                if 0 <= x < 8 and 0 <= y < 8:
                    set_color(midi_out, x, y, 255, 255, 0)
        time.sleep(0.1)
        clear_all(midi_out)


def sunset_animation(midi_out, should_run, current_animation):
    """Gradient animation mimicking a sunset - faster version."""
    from ..hardware.launchpad import clear_all, set_color
    clear_all(midi_out)

    # Sunset colors from top to bottom
    colors = [
        (255, 100, 0),  # Orange
        (255, 50, 0),   # Dark orange
        (200, 0, 50),   # Reddish
        (150, 0, 100),  # Purple
        (100, 0, 150),  # Dark purple
        (50, 0, 150),   # Deep blue
        (0, 0, 100),    # Dark blue
        (0, 0, 50)      # Night blue
    ]

    # Full sunset - shorter display time
    for y in range(8):
        if current_animation() != 'sunset':
            break
        for x in range(8):
            set_color(midi_out, x, y, *colors[7-y])
    time.sleep(0.5)  # Shorter time (was 2.0)

    # Fade to night - fewer steps, faster transition
    for step in range(5):  # Fewer steps (was 10)
        if current_animation() != 'sunset':
            break
        for y in range(8):
            for x in range(8):
                r, g, b = colors[7-y]
                factor = 1.0 - (step / 5.0)
                set_color(midi_out, x, y, int(r*factor), int(g*factor), int(b*factor))
        time.sleep(0.1)  # Faster transition (was 0.2)

    # Add rapid sunrise effect
    for step in range(5):
        if current_animation() != 'sunset':
            break
        for y in range(8):
            for x in range(8):
                r, g, b = colors[7-y]
                factor = step / 5.0
                set_color(midi_out, x, y, int(r*factor), int(g*factor), int(b*factor))
        time.sleep(0.1)


def heartbeat_animation(midi_out, should_run, current_animation):
    """Pulsing animation that mimics a heartbeat rhythm."""
    heart_shape = [
        (2, 1), (3, 1), (5, 1), (6, 1),
        (1, 2), (4, 2), (7, 2),
        (1, 3), (7, 3),
        (2, 4), (6, 4),
        (3, 5), (5, 5),
        (4, 6)
    ]

    for _ in range(3):  # 3 heartbeats
        if current_animation() != 'heartbeat':
            break

        # First pulse (stronger)
        for intensity in range(0, 255, 25):
            if current_animation() != 'heartbeat':
                break
            for x, y in heart_shape:
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, intensity, 0, 0)
            time.sleep(0.03)

        time.sleep(0.1)  # Short pause

        # Second pulse (weaker)
        for intensity in range(0, 180, 20):
            if current_animation() != 'heartbeat':
                break
            for x, y in heart_shape:
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, intensity, 0, 0)
            time.sleep(0.03)

        # Fade out slowly
        for intensity in range(180, 0, -10):
            if current_animation() != 'heartbeat':
                break
            for x, y in heart_shape:
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, intensity, 0, 0)
            time.sleep(0.05)

        time.sleep(0.6)  # Pause between beats


def bloom_animation(midi_out, should_run, current_animation):
    """Flower-like pattern that blooms from the center - faster version."""
    from ..hardware.launchpad import clear_all, set_color
    clear_all(midi_out)

    # Define flower growth pattern (coordinates from center)
    petals = [
        [],  # Center
        [(0, 0)],  # Stage 1
        [(0, 1), (1, 0), (0, -1), (-1, 0)],  # Stage 2
        [(1, 1), (1, -1), (-1, -1), (-1, 1)],  # Stage 3
        [(0, 2), (2, 0), (0, -2), (-2, 0)]  # Stage 4
    ]

    # Colors for each stage (green stem to pink flower)
    colors = [
        (0, 0, 0),
        (50, 200, 50),  # Green center
        (255, 150, 200),  # Pink petals
        (255, 100, 150),  # Darker pink
        (255, 50, 100)   # Deep pink
    ]

    # Bloom - faster transition
    for stage in range(1, len(petals)):
        if current_animation() != 'bloom':
            break
        for dx, dy in petals[stage]:
            set_color(midi_out, 4+dx, 4+dy, *colors[stage])
        time.sleep(0.2)  # Faster bloom (was 0.4)

    # Add rapid pulse effect
    for _ in range(3):
        if current_animation() != 'bloom':
            break
        # Pulsate
        for intensity in [0.7, 1.0, 0.7, 0.5]:
            if current_animation() != 'bloom':
                break
            for stage in range(1, len(petals)):
                for dx, dy in petals[stage]:
                    r, g, b = colors[stage]
                    set_color(midi_out, 4+dx, 4+dy, int(r*intensity), int(g*intensity), int(b*intensity))
            time.sleep(0.15)  # Faster transition (was 0.3)
