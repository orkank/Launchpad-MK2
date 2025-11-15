"""Basic animation patterns."""

import time
import colorsys
import math
import random


def rainbow_wave(midi_out, should_run, current_animation):
    """Rainbow wave animation spreading from center."""
    while should_run() and current_animation() == 'rainbow':
        for offset in range(0, 100, 2):
            if current_animation() != 'rainbow':
                break
            for y in range(9):
                for x in range(9):
                    center_x, center_y = 3.5, 3.5
                    distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                    hue = (offset + distance * 10) % 100 / 100.0
                    r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
                    from ..hardware.launchpad import set_color
                    set_color(midi_out, x, y, r, g, b)
            time.sleep(0.05)


def matrix_rain(midi_out, should_run, current_animation):
    """Matrix-style falling code rain effect."""
    drops = []
    grid_width = 9
    grid_height = 9

    while should_run() and current_animation() == 'matrix':
        # Create new drops
        if random.random() < 0.3:
            drops.append({
                'x': random.randint(0, grid_width - 1),
                'y': grid_height - 1,
                'speed': random.uniform(0.2, 0.5)
            })

        # Clear grid
        from ..hardware.launchpad import clear_all
        clear_all(midi_out)

        # Update and draw drops
        new_drops = []
        for drop in drops:
            drop['y'] -= drop['speed']
            if drop['y'] > 0:
                x = int(drop['x'])
                y = int(drop['y'])
                if 0 <= x < grid_width and 0 <= y < grid_height:
                    intensity = min(255, int((1.0 - (drop['y'] / grid_height)) * 255))
                    from ..hardware.launchpad import set_color
                    set_color(midi_out, x, y, 0, intensity, 0)
                    new_drops.append(drop)

        drops = new_drops
        time.sleep(0.05)


def pulse_rings(midi_out, should_run, current_animation):
    """Pulsing rings from center."""
    center_x = 4
    center_y = 4
    max_radius = 8
    phase = 0

    while should_run() and current_animation() == 'pulse':
        # Clear grid
        from ..hardware.launchpad import clear_all
        clear_all(midi_out)

        # Calculate pulse intensity (0 to 1)
        pulse = (math.sin(phase / 10) + 1) / 2

        # Draw concentric rings
        for y in range(9):
            for x in range(9):
                # Calculate distance from center
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx*dx + dy*dy)

                # Calculate color intensity based on distance and pulse
                intensity = 1.0 - (distance / max_radius)
                if intensity < 0:
                    intensity = 0

                # Modulate intensity with pulse
                intensity *= pulse

                # Set color
                r = int(255 * intensity)
                g = int(100 * intensity)
                b = int(200 * intensity)

                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)

        phase += 1
        time.sleep(0.05)


def random_sparkle(midi_out, should_run, current_animation):
    """Random sparkling lights."""
    grid_width = 9
    grid_height = 9
    sparkles = []

    while should_run() and current_animation() == 'sparkle':
        # Add new sparkles
        if random.random() < 0.2:
            sparkles.append({
                'x': random.randint(0, grid_width - 1),
                'y': random.randint(0, grid_height - 1),
                'life': 1.0,
                'color': (
                    random.randint(100, 255),
                    random.randint(100, 255),
                    random.randint(100, 255)
                )
            })

        # Clear grid
        from ..hardware.launchpad import clear_all
        clear_all(midi_out)

        # Update and draw sparkles
        new_sparkles = []
        for sparkle in sparkles:
            if sparkle['life'] > 0:
                x = sparkle['x']
                y = sparkle['y']
                intensity = sparkle['life']
                r = int(sparkle['color'][0] * intensity)
                g = int(sparkle['color'][1] * intensity)
                b = int(sparkle['color'][2] * intensity)
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)

                sparkle['life'] -= 0.05
                if sparkle['life'] > 0:
                    new_sparkles.append(sparkle)

        sparkles = new_sparkles
        time.sleep(0.05)


def color_wipe(midi_out, should_run, current_animation):
    """Color wipe animation."""
    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
    ]

    while should_run() and current_animation() == 'wipe':
        for color in colors:
            if current_animation() != 'wipe':
                break
            for y in range(9):
                for x in range(9):
                    from ..hardware.launchpad import set_color
                    set_color(midi_out, x, y, *color)
                    time.sleep(0.02)
        time.sleep(0.5)


def snake(midi_out, should_run, current_animation):
    """Snake movement animation."""
    snake_body = [(0, 0)]
    direction = (1, 0)  # Start moving right

    while should_run() and current_animation() == 'snake':
        # Clear the grid
        from ..hardware.launchpad import clear_all
        clear_all(midi_out)

        # Draw snake
        for i, (x, y) in enumerate(snake_body):
            brightness = 255 - (i * 20)  # Fade tail
            if brightness < 0:
                brightness = 0
            from ..hardware.launchpad import set_color
            set_color(midi_out, x, y, 0, brightness, 0)

        # Move snake head
        head_x, head_y = snake_body[0]
        new_x = (head_x + direction[0]) % 9
        new_y = (head_y + direction[1]) % 9

        # Add new head
        snake_body.insert(0, (new_x, new_y))
        if len(snake_body) > 10:  # Limit snake length
            snake_body.pop()

        # Change direction randomly
        if random.random() < 0.1:  # 10% chance to change direction
            direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])

        time.sleep(0.1)


def fireworks(midi_out, should_run, current_animation):
    """Fireworks explosion animation."""
    while should_run() and current_animation() == 'fireworks':
        # Launch firework
        center_x = random.randint(2, 6)
        center_y = random.randint(2, 6)
        color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )

        # Explosion animation
        for radius in range(5):
            if current_animation() != 'fireworks':
                break
            from ..hardware.launchpad import clear_all
            clear_all(midi_out)

            # Draw explosion
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    x = center_x + dx
                    y = center_y + dy
                    if 0 <= x < 9 and 0 <= y < 9:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if abs(distance - radius) < 1:
                            brightness = 1.0 - (distance / 5)
                            if brightness < 0:
                                brightness = 0
                            r = int(color[0] * brightness)
                            g = int(color[1] * brightness)
                            b = int(color[2] * brightness)
                            from ..hardware.launchpad import set_color
                            set_color(midi_out, x, y, r, g, b)

            time.sleep(0.1)
        time.sleep(0.2)


def rain(midi_out, should_run, current_animation):
    """Rain falling animation."""
    drops = []
    while should_run() and current_animation() == 'rain':
        # Create new drops
        if random.random() < 0.3:  # 30% chance to create new drop
            drops.append({
                'x': random.randint(0, 8),
                'y': 8,
                'speed': random.uniform(0.2, 0.5)
            })

        # Clear grid
        from ..hardware.launchpad import clear_all
        clear_all(midi_out)

        # Update and draw drops
        new_drops = []
        for drop in drops:
            drop['y'] -= drop['speed']
            if drop['y'] > 0:
                x = int(drop['x'])
                y = int(drop['y'])
                intensity = min(255, int((1.0 - (drop['y'] / 9)) * 255))
                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, 0, 0, intensity)
                new_drops.append(drop)

        drops = new_drops
        time.sleep(0.05)


def wave_collision(midi_out, should_run, current_animation):
    """Wave collision animation."""
    center_x = 4
    center_y = 4
    grid_width = 9
    grid_height = 9
    phase = 0

    while should_run() and current_animation() == 'wave':
        for y in range(grid_height):
            for x in range(grid_width):
                # Calculate distances from center
                dx1 = x - center_x
                dy1 = y - center_y
                dx2 = x - (grid_width - center_x - 1)
                dy2 = y - (grid_height - center_y - 1)

                # Create two waves from opposite corners
                dist1 = math.sqrt(dx1*dx1 + dy1*dy1)
                dist2 = math.sqrt(dx2*dx2 + dy2*dy2)

                wave1 = math.sin(phase/10.0 + dist1/2.0)
                wave2 = math.sin(phase/10.0 + dist2/2.0)

                # Combine waves
                combined = (wave1 + wave2) / 2.0

                # Create color based on interference
                intensity = (combined + 1) / 2.0  # Normalize to 0-1
                r = int(255 * intensity * abs(math.sin(phase/25.0)))
                g = int(255 * intensity * abs(math.sin(phase/20.0)))
                b = int(255 * intensity * abs(math.sin(phase/15.0)))

                from ..hardware.launchpad import set_color
                set_color(midi_out, x, y, r, g, b)

        phase += 1
        time.sleep(0.05)
