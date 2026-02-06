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


def aurora_animation(midi_out, should_run, current_animation):
    """Aurora borealis effect with flowing green-blue waves."""
    import colorsys
    from ..hardware.launchpad import clear_all, set_color
    
    phase = 0
    
    while should_run() and current_animation() == 'aurora':
        clear_all(midi_out)
        
        for y in range(9):
            for x in range(9):
                # Create wave pattern
                wave1 = math.sin((x + phase) * 0.3) * 0.5 + 0.5
                wave2 = math.sin((y + phase * 0.7) * 0.4) * 0.5 + 0.5
                wave3 = math.sin((x + y + phase * 0.5) * 0.2) * 0.5 + 0.5
                
                # Combine waves for aurora effect
                intensity = (wave1 + wave2 + wave3) / 3
                
                # Aurora colors: green to cyan to blue
                hue = 0.4 + (intensity * 0.2)  # Green to cyan range
                saturation = 0.8 + (intensity * 0.2)
                value = 0.3 + (intensity * 0.7)
                
                r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
                set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        
        phase += 0.5
        time.sleep(0.08)


def galaxy_animation(midi_out, should_run, current_animation):
    """Spiral galaxy effect with rotating arms."""
    import colorsys
    from ..hardware.launchpad import clear_all, set_color
    
    center_x, center_y = 4, 4
    rotation = 0
    
    while should_run() and current_animation() == 'galaxy':
        clear_all(midi_out)
        
        for y in range(9):
            for x in range(9):
                # Calculate angle and distance from center
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:
                    angle = math.atan2(dy, dx) + rotation
                    # Create spiral pattern
                    spiral_angle = angle + distance * 0.8
                    
                    # Create galaxy arm pattern
                    arm_intensity = (math.sin(spiral_angle * 2) + 1) / 2
                    distance_factor = 1.0 / (1.0 + distance * 0.3)
                    intensity = arm_intensity * distance_factor
                    
                    # Galaxy colors: purple to blue to white
                    hue = 0.7 - (distance * 0.1)  # Purple to blue
                    saturation = 0.6 + (intensity * 0.4)
                    value = 0.2 + (intensity * 0.8)
                    
                    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
                    set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        
        rotation += 0.1
        time.sleep(0.1)


def neon_grid_animation(midi_out, should_run, current_animation):
    """Neon grid pattern with pulsing lines."""
    from ..hardware.launchpad import clear_all, set_color
    
    phase = 0
    
    while should_run() and current_animation() == 'neon_grid':
        clear_all(midi_out)
        
        # Calculate pulse intensity
        pulse = (math.sin(phase) + 1) / 2
        
        # Draw horizontal and vertical grid lines
        for i in range(9):
            # Horizontal lines
            intensity_h = (math.sin(phase + i * 0.5) + 1) / 2
            for x in range(9):
                r = int(0 * intensity_h * pulse)
                g = int(255 * intensity_h * pulse)
                b = int(255 * intensity_h * pulse)
                set_color(midi_out, x, i, r, g, b)
            
            # Vertical lines
            intensity_v = (math.sin(phase + i * 0.7) + 1) / 2
            for y in range(9):
                r = int(255 * intensity_v * pulse)
                g = int(0 * intensity_v * pulse)
                b = int(255 * intensity_v * pulse)
                set_color(midi_out, i, y, r, g, b)
        
        # Add intersection highlights
        for x in range(9):
            for y in range(9):
                if x % 2 == 0 and y % 2 == 0:
                    highlight = (math.sin(phase + x + y) + 1) / 2
                    r = int(255 * highlight)
                    g = int(255 * highlight)
                    b = int(255 * highlight)
                    set_color(midi_out, x, y, r, g, b)
        
        phase += 0.15
        time.sleep(0.08)


def lava_lamp_animation(midi_out, should_run, current_animation):
    """Lava lamp effect with rising blobs."""
    import colorsys
    from ..hardware.launchpad import clear_all, set_color
    
    blobs = []
    for _ in range(3):
        blobs.append({
            'x': random.uniform(1, 7),
            'y': random.uniform(1, 7),
            'size': random.uniform(1.5, 2.5),
            'speed': random.uniform(0.02, 0.05),
            'hue': random.uniform(0.0, 1.0)
        })
    
    frame = 0
    
    while should_run() and current_animation() == 'lava_lamp':
        clear_all(midi_out)
        
        # Base color (dark background)
        base_hue = 0.1
        for y in range(9):
            for x in range(9):
                r, g, b = colorsys.hsv_to_rgb(base_hue, 0.8, 0.2)
                set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        
        # Update and draw blobs
        for blob in blobs:
            # Move blob up (lava rising)
            blob['y'] -= blob['speed']
            
            # Reset if blob reaches top
            if blob['y'] < -1:
                blob['y'] = 8
                blob['x'] = random.uniform(1, 7)
                blob['hue'] = random.uniform(0.0, 1.0)
            
            # Slight horizontal drift
            blob['x'] += math.sin(frame * 0.1) * 0.02
            
            # Draw blob
            for y in range(9):
                for x in range(9):
                    dx = x - blob['x']
                    dy = y - blob['y']
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance < blob['size']:
                        # Soft edge
                        intensity = 1.0 - (distance / blob['size'])
                        intensity = max(0, min(1, intensity))
                        
                        # Lava lamp colors (warm hues)
                        hue = blob['hue']
                        saturation = 0.9
                        value = 0.3 + (intensity * 0.7)
                        
                        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
                        set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        
        frame += 1
        time.sleep(0.1)


def prism_animation(midi_out, should_run, current_animation):
    """Prism effect with rainbow refraction."""
    import colorsys
    from ..hardware.launchpad import clear_all, set_color
    
    phase = 0
    
    while should_run() and current_animation() == 'prism':
        clear_all(midi_out)
        
        # Create light beam from left
        beam_x = int((math.sin(phase * 0.3) + 1) * 4)
        
        for y in range(9):
            # Create rainbow refraction effect
            for x in range(9):
                # Distance from beam
                distance = abs(x - beam_x)
                
                # Refraction angle based on distance
                refraction = distance * 0.2
                
                # Create rainbow spectrum
                hue = (phase + refraction + y * 0.1) % 1.0
                saturation = 1.0
                value = max(0.3, 1.0 - (distance * 0.15))
                
                r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
                set_color(midi_out, x, y, int(r * 255), int(g * 255), int(b * 255))
        
        # Add prism highlight
        for y in range(9):
            highlight = (math.sin(phase + y * 0.5) + 1) / 2
            r = int(255 * highlight)
            g = int(255 * highlight)
            b = int(255 * highlight)
            set_color(midi_out, beam_x, y, r, g, b)
        
        phase += 0.2
        time.sleep(0.08)
