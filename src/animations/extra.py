"""Additional distinct LED animations (batch added in 2.3.x)."""

import colorsys
import math
import random
import time

from ..hardware.launchpad import clear_all, set_color


def checker_pulse(midi_out, should_run, current_animation):
    """Alternating checkerboard that breathes in warm amber / cool teal."""
    name = 'checker_pulse'
    phase = 0.0
    while should_run() and current_animation() == name:
        clear_all(midi_out)
        pulse = (math.sin(phase) + 1) * 0.5
        for y in range(9):
            for x in range(9):
                cell = (x + y + int(phase * 2)) % 2
                if cell == 0:
                    r, g, b = int(255 * pulse), int(140 * pulse), 20
                else:
                    r, g, b = 10, int(180 * (1 - pulse * 0.4)), int(200 * (1 - pulse * 0.3))
                set_color(midi_out, x, y, r, g, b)
        phase += 0.12
        time.sleep(0.06)


def spiral_trail(midi_out, should_run, current_animation):
    """Single bright head spiraling inward/outward with a fading trail."""
    name = 'spiral_trail'
    # Spiral order on 8x8-ish grid including top/right edges (9x9)
    cells = []
    left, right, top, bottom = 0, 8, 0, 8
    while left <= right and top <= bottom:
        for x in range(left, right + 1):
            cells.append((x, top))
        top += 1
        for y in range(top, bottom + 1):
            cells.append((right, y))
        right -= 1
        if top <= bottom:
            for x in range(right, left - 1, -1):
                cells.append((x, bottom))
            bottom -= 1
        if left <= right:
            for y in range(bottom, top - 1, -1):
                cells.append((left, y))
            left += 1

    head = 0
    trail_len = 18
    while should_run() and current_animation() == name:
        clear_all(midi_out)
        for i in range(trail_len):
            idx = (head - i) % len(cells)
            x, y = cells[idx]
            fade = 1.0 - (i / trail_len)
            hue = (head * 0.02 + i * 0.03) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.9, fade)
            set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        head = (head + 1) % len(cells)
        time.sleep(0.045)


def meteor_shower(midi_out, should_run, current_animation):
    """Diagonal meteors streaking across the pad."""
    name = 'meteor_shower'
    meteors = []
    while should_run() and current_animation() == name:
        if random.random() < 0.35:
            meteors.append({
                'x': random.uniform(-2, 8),
                'y': 8.5,
                'speed': random.uniform(0.35, 0.7),
                'hue': random.random(),
                'len': random.randint(3, 5),
            })
        clear_all(midi_out)
        alive = []
        for m in meteors:
            m['x'] += m['speed'] * 0.7
            m['y'] -= m['speed']
            if m['y'] > -2 and m['x'] < 10:
                for i in range(m['len']):
                    x = int(m['x'] - i * 0.7)
                    y = int(m['y'] + i * 0.7)
                    if 0 <= x <= 8 and 0 <= y <= 8:
                        fade = 1.0 - i / m['len']
                        r, g, b = colorsys.hsv_to_rgb(m['hue'], 0.55, fade)
                        set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
                alive.append(m)
        meteors = alive
        time.sleep(0.05)


def plasma_field(midi_out, should_run, current_animation):
    """Classic plasma / lava-noise color field."""
    name = 'plasma_field'
    t = 0.0
    while should_run() and current_animation() == name:
        for y in range(9):
            for x in range(9):
                v = (
                    math.sin(x * 0.45 + t)
                    + math.sin(y * 0.55 - t * 1.2)
                    + math.sin((x + y) * 0.35 + t * 0.7)
                    + math.sin(math.hypot(x - 4, y - 4) * 0.5 - t)
                )
                hue = (v + 4) / 8.0
                r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.85, 0.9)
                set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        t += 0.18
        time.sleep(0.055)


def binary_cascade(midi_out, should_run, current_animation):
    """Blue/cyan cascading columns (distinct from green matrix rain)."""
    name = 'binary_cascade'
    cols = [{'y': random.uniform(0, 9), 'speed': random.uniform(0.25, 0.55), 'hue': random.uniform(0.5, 0.7)} for _ in range(9)]
    while should_run() and current_animation() == name:
        clear_all(midi_out)
        for x, col in enumerate(cols):
            col['y'] -= col['speed']
            if col['y'] < -1:
                col['y'] = 9.5
                col['speed'] = random.uniform(0.25, 0.55)
                col['hue'] = random.uniform(0.5, 0.7)
            for trail in range(4):
                y = int(col['y'] + trail)
                if 0 <= y <= 8:
                    fade = 1.0 - trail * 0.22
                    r, g, b = colorsys.hsv_to_rgb(col['hue'], 0.95, fade)
                    set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        time.sleep(0.05)


def orbital_dots(midi_out, should_run, current_animation):
    """Several dots orbiting the center at different radii/speeds."""
    name = 'orbital_dots'
    angle = 0.0
    orbits = [
        {'r': 1.2, 'speed': 1.4, 'hue': 0.05},
        {'r': 2.4, 'speed': -1.0, 'hue': 0.55},
        {'r': 3.5, 'speed': 0.7, 'hue': 0.8},
        {'r': 3.5, 'speed': -0.7, 'hue': 0.35},
    ]
    while should_run() and current_animation() == name:
        clear_all(midi_out)
        # Dim core
        set_color(midi_out, 4, 4, 40, 40, 60)
        for orb in orbits:
            a = angle * orb['speed']
            x = int(round(4 + math.cos(a) * orb['r']))
            y = int(round(4 + math.sin(a) * orb['r']))
            if 0 <= x <= 8 and 0 <= y <= 8:
                r, g, b = colorsys.hsv_to_rgb(orb['hue'], 0.9, 1.0)
                set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
                # soft trail
                x2 = int(round(4 + math.cos(a - 0.35) * orb['r']))
                y2 = int(round(4 + math.sin(a - 0.35) * orb['r']))
                if 0 <= x2 <= 8 and 0 <= y2 <= 8:
                    set_color(midi_out, x2, y2, int(r * 120), int(g * 120), int(b * 120))
        angle += 0.14
        time.sleep(0.05)


def scan_sweep(midi_out, should_run, current_animation):
    """Cylon / scanner bar sweeping with a cool white trail."""
    name = 'scan_sweep'
    pos = 0.0
    direction = 1
    while should_run() and current_animation() == name:
        clear_all(midi_out)
        # Background grid tint
        for y in range(9):
            for x in range(9):
                set_color(midi_out, x, y, 5, 8, 18)
        cx = int(pos)
        for y in range(9):
            set_color(midi_out, cx, y, 255, 40, 40)
            if 0 <= cx - 1 <= 8:
                set_color(midi_out, cx - 1, y, 120, 20, 30)
            if 0 <= cx + 1 <= 8:
                set_color(midi_out, cx + 1, y, 120, 20, 30)
        pos += direction * 0.45
        if pos >= 8 or pos <= 0:
            direction *= -1
            pos = max(0, min(8, pos))
        time.sleep(0.05)


def ember_rise(midi_out, should_run, current_animation):
    """Hot embers rising through a dark red bed of coals."""
    name = 'ember_rise'
    embers = []
    while should_run() and current_animation() == name:
        if random.random() < 0.5:
            embers.append({
                'x': random.uniform(0, 8),
                'y': -0.5,
                'speed': random.uniform(0.15, 0.4),
                'heat': random.uniform(0.6, 1.0),
            })
        clear_all(midi_out)
        # Coal bed
        for y in range(3):
            for x in range(9):
                flicker = 0.3 + 0.2 * math.sin(time.time() * 6 + x + y)
                set_color(midi_out, x, y, int(180 * flicker), int(40 * flicker), 5)
        alive = []
        for e in embers:
            e['y'] += e['speed']
            if e['y'] <= 8.5:
                x, y = int(e['x']), int(e['y'])
                if 0 <= x <= 8 and 0 <= y <= 8:
                    h = e['heat'] * (1.0 - e['y'] / 10)
                    set_color(midi_out, x, y, int(255 * h), int(160 * h * h), int(20 * h))
                alive.append(e)
        embers = alive
        time.sleep(0.055)


def ripple_pool(midi_out, should_run, current_animation):
    """Expanding ripples from random drop points."""
    name = 'ripple_pool'
    drops = [{'x': 4, 'y': 4, 'r': 0.0, 'hue': 0.55}]
    while should_run() and current_animation() == name:
        if random.random() < 0.08:
            drops.append({
                'x': random.randint(0, 8),
                'y': random.randint(0, 8),
                'r': 0.0,
                'hue': random.uniform(0.45, 0.85),
            })
        clear_all(midi_out)
        alive = []
        for d in drops:
            d['r'] += 0.28
            if d['r'] < 10:
                for y in range(9):
                    for x in range(9):
                        dist = math.hypot(x - d['x'], y - d['y'])
                        band = abs(dist - d['r'])
                        if band < 0.85:
                            intensity = 1.0 - band / 0.85
                            intensity *= max(0.0, 1.0 - d['r'] / 10)
                            r, g, b = colorsys.hsv_to_rgb(d['hue'], 0.75, intensity)
                            # Additive-ish: keep brighter of current write in this frame
                            set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
                alive.append(d)
        drops = alive or [{'x': 4, 'y': 4, 'r': 0.0, 'hue': 0.55}]
        time.sleep(0.05)


def vortex_spin(midi_out, should_run, current_animation):
    """Rotating color vortex around the center."""
    name = 'vortex_spin'
    angle = 0.0
    while should_run() and current_animation() == name:
        for y in range(9):
            for x in range(9):
                dx, dy = x - 4, y - 4
                dist = math.hypot(dx, dy) + 0.001
                theta = math.atan2(dy, dx) + angle + dist * 0.55
                hue = (theta / (2 * math.pi) + 1) % 1.0
                value = max(0.15, 1.0 - dist / 6.5)
                r, g, b = colorsys.hsv_to_rgb(hue, 0.95, value)
                set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        angle += 0.16
        time.sleep(0.05)
