"""Adaptive animations that respond to Spotify audio features."""

import time
import math
import colorsys
import random


def adaptive_rainbow(midi_out, should_run, current_animation, audio_analyzer=None):
    """Rainbow animation that adapts to tempo and energy."""
    if not audio_analyzer:
        # Fallback to regular rainbow
        from .basic import rainbow_wave
        return rainbow_wave(midi_out, should_run, current_animation)

    offset = 0
    while should_run() and current_animation() == 'adaptive_rainbow':
        try:
            params = audio_analyzer.get_animation_parameters()
            speed = params.get('speed', 1.0)
            intensity = params.get('intensity', 0.5)
            color_shift = params.get('color_shift', 0.0)

            # Adjust animation speed based on tempo
            increment = max(1, int(speed * 2))

            for y in range(9):
                for x in range(9):
                    center_x, center_y = 3.5, 3.5
                    distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)

                    # Apply color shift based on valence
                    hue = ((offset + distance * 10) % 100 / 100.0 + color_shift * 0.3) % 1.0
                    saturation = 0.8 + intensity * 0.2
                    value = 0.7 + intensity * 0.3

                    r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, saturation, value)]
                    from ..hardware.launchpad import set_color
                    set_color(midi_out, x, y, r, g, b)

            offset += increment
            time.sleep(max(0.02, 0.1 / speed))  # Faster updates for higher tempo

        except Exception as e:
            print(f"Adaptive rainbow error: {e}")
            time.sleep(0.1)


def adaptive_pulse(midi_out, should_run, current_animation, audio_analyzer=None):
    """Pulse animation synchronized to beat."""
    if not audio_analyzer:
        from .basic import pulse_rings
        return pulse_rings(midi_out, should_run, current_animation)

    phase = 0
    while should_run() and current_animation() == 'adaptive_pulse':
        try:
            tempo = audio_analyzer.get_tempo()
            energy = audio_analyzer.get_energy_level()
            valence = audio_analyzer.get_valence()
            danceability = audio_analyzer.get_danceability()

            # Calculate beat-synchronized pulse
            beat_duration = 60.0 / tempo
            beat_phase = (time.time() % beat_duration) / beat_duration
            pulse = (math.sin(beat_phase * 2 * math.pi) + 1) / 2

            # Energy affects pulse intensity and size
            max_radius = 6 + energy * 2
            pulse_intensity = energy * pulse

            from ..hardware.launchpad import clear_all, set_color
            clear_all(midi_out)

            center_x, center_y = 4, 4

            for y in range(9):
                for x in range(9):
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx*dx + dy*dy)

                    if distance <= max_radius:
                        # Distance-based intensity
                        intensity = max(0, 1.0 - (distance / max_radius)) * pulse_intensity

                        # Color based on valence
                        if valence > 0.6:  # Happy - warm colors
                            r = int(255 * intensity)
                            g = int((100 + valence * 155) * intensity)
                            b = int(50 * intensity)
                        elif valence < 0.4:  # Sad - cool colors
                            r = int(50 * intensity)
                            g = int(100 * intensity)
                            b = int(255 * intensity)
                        else:  # Neutral - purple/pink
                            r = int(200 * intensity)
                            g = int(100 * intensity)
                            b = int(200 * intensity)

                        set_color(midi_out, x, y, r, g, b)

            # Danceability affects update rate
            sleep_time = max(0.02, 0.1 / (1 + danceability))
            time.sleep(sleep_time)

        except Exception as e:
            print(f"Adaptive pulse error: {e}")
            time.sleep(0.1)


def adaptive_sparkle(midi_out, should_run, current_animation, audio_analyzer=None):
    """Sparkle animation that responds to energy and danceability."""
    if not audio_analyzer:
        from .basic import random_sparkle
        return random_sparkle(midi_out, should_run, current_animation)

    sparkles = []

    while should_run() and current_animation() == 'adaptive_sparkle':
        try:
            energy = audio_analyzer.get_energy_level()
            danceability = audio_analyzer.get_danceability()
            valence = audio_analyzer.get_valence()
            tempo = audio_analyzer.get_tempo()

            # Sparkle frequency based on energy and danceability
            spawn_rate = 0.1 + (energy * danceability) * 0.4

            # Add new sparkles
            if random.random() < spawn_rate:
                # More sparkles for higher energy
                num_new = 1 + int(energy * 3)
                for _ in range(num_new):
                    sparkles.append({
                        'x': random.randint(0, 8),
                        'y': random.randint(0, 8),
                        'life': 0.8 + energy * 0.4,  # Longer life for high energy
                        'color': _get_valence_color(valence),
                        'decay_rate': 0.03 + (tempo / 200) * 0.02  # Faster decay for fast tempo
                    })

            from ..hardware.launchpad import clear_all, set_color
            clear_all(midi_out)

            # Update and draw sparkles
            new_sparkles = []
            for sparkle in sparkles:
                if sparkle['life'] > 0:
                    x, y = sparkle['x'], sparkle['y']
                    intensity = sparkle['life']
                    r, g, b = sparkle['color']

                    set_color(midi_out, x, y,
                             int(r * intensity),
                             int(g * intensity),
                             int(b * intensity))

                    sparkle['life'] -= sparkle['decay_rate']
                    if sparkle['life'] > 0:
                        new_sparkles.append(sparkle)

            sparkles = new_sparkles

            # Update rate based on tempo
            sleep_time = max(0.02, 0.08 - (tempo - 60) / 180 * 0.03)
            time.sleep(sleep_time)

        except Exception as e:
            print(f"Adaptive sparkle error: {e}")
            time.sleep(0.1)


def adaptive_matrix(midi_out, should_run, current_animation, audio_analyzer=None):
    """Matrix rain that responds to track characteristics."""
    if not audio_analyzer:
        from .basic import matrix_rain
        return matrix_rain(midi_out, should_run, current_animation)

    drops = []

    while should_run() and current_animation() == 'adaptive_matrix':
        try:
            energy = audio_analyzer.get_energy_level()
            tempo = audio_analyzer.get_tempo()
            valence = audio_analyzer.get_valence()
            danceability = audio_analyzer.get_danceability()

            # Drop spawn rate based on energy
            spawn_rate = 0.2 + energy * 0.3

            # Create new drops
            if random.random() < spawn_rate:
                drops.append({
                    'x': random.randint(0, 8),
                    'y': 8,
                    'speed': 0.2 + (tempo / 200) * 0.4,  # Faster for higher tempo
                    'intensity': 0.5 + energy * 0.5,
                    'color_variant': valence  # Affects color
                })

            from ..hardware.launchpad import clear_all, set_color
            clear_all(midi_out)

            # Update and draw drops
            new_drops = []
            for drop in drops:
                drop['y'] -= drop['speed']
                if drop['y'] > 0:
                    x = int(drop['x'])
                    y = int(drop['y'])
                    if 0 <= x < 9 and 0 <= y < 9:
                        base_intensity = min(255, int((1.0 - (drop['y'] / 9)) * 255 * drop['intensity']))

                        # Color variation based on valence
                        if drop['color_variant'] > 0.6:
                            # Happy - add some blue/cyan
                            r, g, b = 0, base_intensity, int(base_intensity * 0.5)
                        elif drop['color_variant'] < 0.4:
                            # Sad - pure green (classic matrix)
                            r, g, b = 0, base_intensity, 0
                        else:
                            # Neutral - green with slight red
                            r, g, b = int(base_intensity * 0.2), base_intensity, 0

                        set_color(midi_out, x, y, r, g, b)
                        new_drops.append(drop)

            drops = new_drops

            # Update rate based on danceability
            sleep_time = max(0.03, 0.08 - danceability * 0.03)
            time.sleep(sleep_time)

        except Exception as e:
            print(f"Adaptive matrix error: {e}")
            time.sleep(0.1)


def _get_valence_color(valence):
    """Get color based on valence (mood)."""
    if valence > 0.7:  # Very happy - bright warm colors
        return (255, random.randint(150, 255), random.randint(0, 100))
    elif valence > 0.5:  # Happy - warm colors
        return (255, random.randint(100, 200), random.randint(0, 150))
    elif valence > 0.3:  # Neutral - mixed colors
        return (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
    else:  # Sad - cool colors
        return (random.randint(0, 150), random.randint(100, 200), 255)


def auto_select_animation(midi_out, should_run, current_animation, audio_analyzer=None):
    """Automatically select and switch animations based on audio features."""
    if not audio_analyzer:
        from .basic import rainbow_wave
        return rainbow_wave(midi_out, should_run, current_animation)

    last_suggestion = None
    last_switch_time = 0
    min_switch_interval = 10  # Minimum 10 seconds between switches

    while should_run() and current_animation() == 'auto_select':
        try:
            current_time = time.time()

            # Get suggested animation
            suggested = audio_analyzer.suggest_animation()

            # Switch animation if suggestion changed and enough time has passed
            if (suggested != last_suggestion and
                current_time - last_switch_time > min_switch_interval):

                print(f"🎵 Auto-switching to '{suggested}' animation based on track characteristics")
                last_suggestion = suggested
                last_switch_time = current_time

                # Import and run the suggested animation
                from ..animations import ANIMATIONS
                if suggested in ANIMATIONS:
                    # Note: This creates a nested animation call
                    # In a real implementation, we'd signal the main controller to switch
                    print(f"Would switch to: {suggested}")

            # For now, just show the current suggestion
            from ..hardware.launchpad import clear_all, set_color
            clear_all(midi_out)

            # Show a simple indicator of the current suggested animation
            # This is a placeholder - in real implementation, the main controller would handle switching
            features = audio_analyzer.get_current_features()
            if features:
                energy = features.get('energy', 0.5)
                for x in range(8):
                    height = int(energy * 8)
                    for y in range(height):
                        set_color(midi_out, x, y, 100, 150, 200)

            time.sleep(1)  # Check every second

        except Exception as e:
            print(f"Auto select error: {e}")
            time.sleep(1)



