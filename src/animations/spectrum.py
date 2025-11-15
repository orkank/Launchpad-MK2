"""Spectrum-based animations using Spotify audio analysis."""

import time
import math
import colorsys
from typing import Optional


def spotify_spectrum_analyzer(midi_out, should_run, current_animation, audio_analyzer=None, spotify_manager=None):
    """Spectrum analyzer using Spotify's audio analysis data."""
    if not audio_analyzer or not spotify_manager:
        # Fallback to basic pattern if no audio data
        return basic_spectrum_fallback(midi_out, should_run, current_animation)

    last_update_time = 0
    spectrum_data = [0] * 8  # 8 frequency bands for 8 columns
    peak_data = [0] * 8

    while should_run() and current_animation() == 'spotify_spectrum':
        try:
            current_time = time.time()

            # Get current playback info
            current = spotify_manager.spotify.current_playback()
            if not current or not current['is_playing'] or not current['item']:
                # Show idle pattern
                basic_spectrum_fallback(midi_out, should_run, current_animation, idle=True)
                time.sleep(0.1)
                continue

            progress_ms = current['progress_ms']

            # Update spectrum data every 100ms
            if current_time - last_update_time > 0.1:
                spectrum_info = audio_analyzer.get_spectrum_data(progress_ms)

                if spectrum_info:
                    # Convert Spotify's 12-tone chroma to 8 bands
                    pitches = spectrum_info['pitches']
                    timbre = spectrum_info['timbre']
                    loudness = spectrum_info['loudness_max']

                    # Map 12 pitches to 8 columns
                    for i in range(8):
                        # Combine pitch and timbre data
                        pitch_idx = int(i * 12 / 8)
                        pitch_val = pitches[pitch_idx] if pitch_idx < len(pitches) else 0
                        timbre_val = timbre[i] if i < len(timbre) else 0

                        # Normalize and combine
                        combined = (pitch_val + abs(timbre_val) / 100) * 0.5

                        # Apply loudness scaling
                        loudness_factor = max(0, (loudness + 60) / 60)  # -60dB to 0dB -> 0 to 1

                        spectrum_data[i] = min(8, max(0, combined * 8 * loudness_factor))

                        # Update peaks
                        if spectrum_data[i] > peak_data[i]:
                            peak_data[i] = spectrum_data[i]
                        else:
                            peak_data[i] *= 0.95  # Decay peaks

                    last_update_time = current_time
                else:
                    # Use audio features for fallback
                    features = audio_analyzer.get_current_features()
                    if features:
                        energy = features.get('energy', 0.5)
                        danceability = features.get('danceability', 0.5)
                        valence = features.get('valence', 0.5)

                        # Create pattern based on features
                        for i in range(8):
                            base_height = energy * 4 + 1
                            variation = math.sin(current_time * 2 + i) * danceability * 2
                            spectrum_data[i] = max(0, min(8, base_height + variation))

            # Draw spectrum
            from ..hardware.launchpad import clear_all, set_color
            clear_all(midi_out)

            for x in range(8):
                height = int(spectrum_data[x])
                peak_height = int(peak_data[x])

                # Draw spectrum bars
                for y in range(height):
                    # Color based on height and music characteristics
                    intensity = (y + 1) / 8.0

                    # Get audio parameters for color
                    params = audio_analyzer.get_animation_parameters()
                    color_shift = params.get('color_shift', 0.5)

                    # Calculate color
                    if intensity < 0.33:
                        # Low frequencies - blue to green
                        hue = 0.5 + color_shift * 0.2  # Cyan to green range
                        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.8, intensity)]
                    elif intensity < 0.66:
                        # Mid frequencies - green to yellow
                        hue = 0.2 + color_shift * 0.1  # Green to yellow range
                        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
                    else:
                        # High frequencies - yellow to red
                        hue = color_shift * 0.1  # Yellow to red range
                        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]

                    set_color(midi_out, x, y, r, g, b)

                # Draw peak dot
                if peak_height > height and peak_height < 8:
                    set_color(midi_out, x, int(peak_height), 255, 255, 255)

            time.sleep(0.05)  # ~20fps

        except Exception as e:
            print(f"Spotify spectrum error: {e}")
            time.sleep(0.1)


def energy_bars(midi_out, should_run, current_animation, audio_analyzer=None, spotify_manager=None):
    """Energy bars that respond to track characteristics."""
    if not audio_analyzer:
        return basic_spectrum_fallback(midi_out, should_run, current_animation)

    bar_heights = [0] * 8
    target_heights = [0] * 8

    while should_run() and current_animation() == 'energy_bars':
        try:
            # Get current track features
            features = audio_analyzer.get_current_features()
            params = audio_analyzer.get_animation_parameters()

            if features:
                energy = features.get('energy', 0.5)
                danceability = features.get('danceability', 0.5)
                valence = features.get('valence', 0.5)
                tempo = features.get('tempo', 120)
                loudness = features.get('loudness', -30)

                # Calculate target heights for each bar based on different characteristics
                target_heights[0] = energy * 8  # Pure energy
                target_heights[1] = danceability * 8  # Danceability
                target_heights[2] = valence * 8  # Mood/valence
                target_heights[3] = min(8, (tempo / 200) * 8)  # Tempo (normalized to ~200 BPM max)
                target_heights[4] = max(0, (loudness + 60) / 60 * 8)  # Loudness (-60dB to 0dB)
                target_heights[5] = features.get('acousticness', 0.5) * 8  # Acousticness
                target_heights[6] = features.get('instrumentalness', 0.5) * 8  # Instrumentalness
                target_heights[7] = (energy + danceability) / 2 * 8  # Combined energy

                # Add tempo-based pulsing
                pulse = (math.sin(time.time() * tempo / 60 * 2) + 1) / 2
                for i in range(8):
                    target_heights[i] += pulse * 1.5
                    target_heights[i] = min(8, max(0, target_heights[i]))

            # Smooth animation towards targets
            speed = params.get('speed', 1.0) * 0.1
            for i in range(8):
                diff = target_heights[i] - bar_heights[i]
                bar_heights[i] += diff * speed
                bar_heights[i] = max(0, min(8, bar_heights[i]))

            # Draw bars
            from ..hardware.launchpad import clear_all, set_color
            clear_all(midi_out)

            colors = [
                (255, 0, 0),    # Energy - Red
                (0, 255, 0),    # Danceability - Green
                (255, 255, 0),  # Valence - Yellow
                (0, 0, 255),    # Tempo - Blue
                (255, 0, 255),  # Loudness - Magenta
                (0, 255, 255),  # Acousticness - Cyan
                (255, 165, 0),  # Instrumentalness - Orange
                (255, 255, 255) # Combined - White
            ]

            for x in range(8):
                height = int(bar_heights[x])
                r, g, b = colors[x]

                for y in range(height):
                    # Fade intensity based on height
                    intensity = (y + 1) / height if height > 0 else 1
                    set_color(midi_out, x, y, int(r * intensity), int(g * intensity), int(b * intensity))

            time.sleep(0.05)

        except Exception as e:
            print(f"Energy bars error: {e}")
            time.sleep(0.1)


def tempo_pulse(midi_out, should_run, current_animation, audio_analyzer=None):
    """Pulse animation synchronized to track tempo."""
    if not audio_analyzer:
        return basic_spectrum_fallback(midi_out, should_run, current_animation)

    while should_run() and current_animation() == 'tempo_pulse':
        try:
            tempo = audio_analyzer.get_tempo()
            energy = audio_analyzer.get_energy_level()
            valence = audio_analyzer.get_valence()

            # Calculate pulse timing
            beat_duration = 60.0 / tempo  # seconds per beat
            pulse_phase = (time.time() % beat_duration) / beat_duration

            # Create pulsing effect
            pulse_intensity = (math.sin(pulse_phase * 2 * math.pi) + 1) / 2
            pulse_intensity = pulse_intensity ** 2  # Sharper pulse

            # Color based on valence
            hue = valence * 0.8  # Map valence to hue (0-0.8 for good color range)
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, pulse_intensity * energy)]

            # Draw pulsing pattern
            from ..hardware.launchpad import clear_all, set_color
            clear_all(midi_out)

            center_x, center_y = 4, 4
            max_radius = int(6 * pulse_intensity * energy)

            for y in range(8):
                for x in range(8):
                    distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                    if distance <= max_radius:
                        intensity = max(0, 1 - distance / max_radius) * pulse_intensity
                        set_color(midi_out, x, y, int(r * intensity), int(g * intensity), int(b * intensity))

            time.sleep(0.02)  # High refresh rate for smooth pulse

        except Exception as e:
            print(f"Tempo pulse error: {e}")
            time.sleep(0.1)


def basic_spectrum_fallback(midi_out, should_run, current_animation, idle=False):
    """Fallback spectrum when no audio data is available."""
    while should_run() and current_animation() in ['spotify_spectrum', 'energy_bars', 'tempo_pulse']:
        from ..hardware.launchpad import clear_all, set_color
        clear_all(midi_out)

        if idle:
            # Simple idle pattern
            for x in range(8):
                height = int(2 + math.sin(time.time() * 2 + x) * 1.5)
                for y in range(max(0, height)):
                    intensity = 0.3
                    set_color(midi_out, x, y, int(50 * intensity), int(100 * intensity), int(150 * intensity))

        time.sleep(0.1)



