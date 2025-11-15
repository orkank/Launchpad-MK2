"""Audio visualization animations."""

import time
import math
import numpy as np
from scipy.fft import fft


# Equalizer configuration
EQUALIZER_CONFIG = {
    'sensitivity': 2.5,  # Increase this for more height (try 1.0 to 5.0)
    'min_height': 1,    # Minimum bar height
    'smoothing': 0.7,   # Smoothing factor (0-1)
    'bass_boost': 1.8,  # Bass frequency boost
    'decay': 0.1,       # How quickly the bars fall (0.1-1.0, higher = slower fall)
    'peak_hold': 3,     # How many frames to hold the peak
}


def equalizer_animation_microphone(midi_out, should_run, current_animation):
    """Equalizer animation using microphone input."""
    from ..hardware.audio import initialize_audio

    CHUNK = 2048
    p, stream = initialize_audio()

    if not stream:
        return

    # Keep previous levels for smoothing and decay
    prev_levels = [0] * 8
    peak_levels = [0] * 8
    peak_hold_times = [0] * 8
    current_colors = [[0, 0, 0] for _ in range(8 * 8)]  # Store current LED colors

    try:
        while current_animation() == 'equalizer_microphone':
            try:
                # Read audio data
                data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.float32)

                # Perform FFT
                fft_data = fft(data)
                freq_magnitudes = np.abs(fft_data[:CHUNK//2])

                # Adjust frequency range and scaling
                freq_range = freq_magnitudes[:CHUNK//4]  # Focus on lower frequencies

                # Apply bass boost to lower frequencies
                freq_range[:len(freq_range)//4] *= EQUALIZER_CONFIG['bass_boost']

                # Apply logarithmic scaling and normalization with sensitivity
                freq_range = np.log10(freq_range + 1)
                max_val = np.max(freq_range) if np.max(freq_range) > 0 else 1
                freq_range = freq_range * (8 * EQUALIZER_CONFIG['sensitivity'] / max_val)

                # Map to 8 bands with smoothing and decay
                bands = np.array_split(freq_range, 8)
                current_levels = []

                for i, band in enumerate(bands):
                    # Get new level
                    new_level = np.mean(band)

                    # Apply smoothing with previous frame
                    smooth = EQUALIZER_CONFIG['smoothing']
                    level = (new_level * (1 - smooth) + prev_levels[i] * smooth)

                    # Apply decay if new level is lower
                    if level < prev_levels[i]:
                        level = max(level, prev_levels[i] * EQUALIZER_CONFIG['decay'])

                    # Update peak
                    if level > peak_levels[i]:
                        peak_levels[i] = level
                        peak_hold_times[i] = EQUALIZER_CONFIG['peak_hold']
                    else:
                        if peak_hold_times[i] > 0:
                            peak_hold_times[i] -= 1
                        else:
                            peak_levels[i] *= EQUALIZER_CONFIG['decay']

                    # Ensure minimum height and cap at 8
                    level = max(EQUALIZER_CONFIG['min_height'], min(8, int(level)))
                    current_levels.append(level)
                    prev_levels[i] = level

                # Update LEDs with enhanced colors and slower decay
                for x, level in enumerate(current_levels):
                    for y in range(8):
                        current_idx = x * 8 + y

                        if y < level:  # LED should be lit
                            # Calculate target color
                            intensity = (y + 1) / 8.0
                            if intensity < 0.33:
                                target_r = int(intensity * 3 * 255)
                                target_g = 255
                                target_b = 0
                            elif intensity < 0.66:
                                target_r = 255
                                target_g = int((1 - (intensity - 0.33) * 3) * 255)
                                target_b = 0
                            else:
                                target_r = 255
                                target_g = 0
                                target_b = int((intensity - 0.66) * 3 * 128)

                            # Immediately set to target color
                            current_colors[current_idx] = [target_r, target_g, target_b]
                        else:  # LED should fade
                            # Slowly decrease current color values
                            current_colors[current_idx] = [
                                int(max(0, c - (2 if c > 50 else 1)))  # Slower decay for dimmer colors
                                for c in current_colors[current_idx]
                            ]

                        # Set the color
                        r, g, b = current_colors[current_idx]
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, y, r, g, b)

                    # Draw peak dot with slower decay
                    peak_y = min(7, int(peak_levels[x]))
                    if peak_y >= level:
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, peak_y, 255, 255, 255)

                time.sleep(0.016)  # ~60fps

            except Exception as e:
                print(f"Equalizer error: {e}")
                time.sleep(0.1)

    finally:
        # Cleanup
        stream.stop_stream()
        stream.close()
        p.terminate()


def equalizer_animation(midi_out, should_run, current_animation):
    """Equalizer visualization based on Spotify audio features."""
    from ..services.spotify_manager import get_current_audio_features, format_track_info
    import spotipy

    last_track_id = None
    spotify = None  # This should be passed in or imported from a global state

    while should_run() and current_animation() == 'equalizer':
        try:
            if not spotify:
                # Show idle animation when not connected
                from ..hardware.launchpad import clear_all
                clear_all(midi_out)
                for x in range(9):
                    height = int(2 + math.sin(time.time() * 2 + x/2) * 2)
                    for y in range(height):
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, y, 0, 255, 100)
                time.sleep(0.1)
                continue

            current = spotify.current_playback()
            if not current or not current['is_playing']:
                # Show idle animation when not playing
                from ..hardware.launchpad import clear_all
                clear_all(midi_out)
                for x in range(9):
                    height = int(2 + math.sin(time.time() * 2 + x/2) * 2)
                    for y in range(height):
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, y, 0, 255, 100)
                time.sleep(0.1)
                continue

            track_id = current['item']['id']

            # Print track info when track changes
            if track_id != last_track_id:
                print(f"Now playing: {format_track_info(current['item'], current['progress_ms'])}")
                last_track_id = track_id

                # Get new features when track changes
                features = get_current_audio_features(spotify)
                if not features:
                    continue

                # Extract relevant features
                energy = features['energy']
                danceability = features['danceability']
                valence = features['valence']
                tempo = features['tempo']

                # Clear grid
                from ..hardware.launchpad import clear_all
                clear_all(midi_out)

                # Create visualization based on features
                # Energy (columns 0-2)
                height = int(energy * 8)
                for x in range(3):
                    for y in range(height):
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, y, 255, 0, 0)  # Red for energy

                # Danceability (columns 3-5)
                height = int(danceability * 8)
                for x in range(3, 6):
                    for y in range(height):
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, y, 0, 255, 0)  # Green for danceability

                # Valence (columns 6-8)
                height = int(valence * 8)
                for x in range(6, 9):
                    for y in range(height):
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, y, 0, 0, 255)  # Blue for valence

                # Add some animation based on tempo
                pulse_time = time.time() * (tempo / 60)  # Pulses per second
                pulse = (math.sin(pulse_time) + 1) / 2  # 0 to 1

                # Add pulsing overlay
                for x in range(9):
                    for y in range(8):
                        r, g, b = 255, 255, 255
                        intensity = pulse * 0.3  # 30% max intensity
                        from ..hardware.launchpad import set_color
                        set_color(midi_out, x, y,
                                int(r * intensity),
                                int(g * intensity),
                                int(b * intensity))

            time.sleep(0.05)  # Adjust for smoothness

        except Exception as e:
            print(f"Equalizer error: {e}")
            time.sleep(1)
