"""Animation system for Launchpad MK2.

This module contains all LED animation functions and related utilities.
"""

from .basic import (
    rainbow_wave,
    matrix_rain,
    pulse_rings,
    random_sparkle,
    color_wipe,
    snake,
    fireworks,
    rain,
    wave_collision
)

from .genre_based import (
    electronic_animation,
    classical_animation,
    rock_animation,
    jazz_animation,
    ambient_animation
)

from .mood_based import (
    synthwave_animation,
    lofi_animation,
    meditation_animation,
    party_animation,
    focus_animation
)

from .visualizers import (
    equalizer_animation,
    equalizer_animation_microphone
)

from .artistic import (
    starfield_animation,
    geometric_animation,
    sunset_animation,
    heartbeat_animation,
    bloom_animation
)

from .spectrum import (
    spotify_spectrum_analyzer,
    energy_bars,
    tempo_pulse
)

from .adaptive import (
    adaptive_rainbow,
    adaptive_pulse,
    adaptive_sparkle,
    adaptive_matrix,
    auto_select_animation
)

# Animation registry - all available animations
ANIMATIONS = {
    'rainbow': rainbow_wave,
    'matrix': matrix_rain,
    'pulse': pulse_rings,
    'sparkle': random_sparkle,
    'wipe': color_wipe,
    'snake': snake,
    'fireworks': fireworks,
    'rain': rain,
    'wave': wave_collision,
    'equalizer': equalizer_animation,
    'equalizer_microphone': equalizer_animation_microphone,

    # Genre-based animations
    'electronic': electronic_animation,
    'classical': classical_animation,
    'rock': rock_animation,
    'jazz': jazz_animation,
    'ambient': ambient_animation,

    # Mood-based animations
    'synthwave': synthwave_animation,
    'lofi': lofi_animation,
    'meditation': meditation_animation,
    'party': party_animation,
    'focus': focus_animation,

    # Artistic animations
    'starfield': starfield_animation,
    'geometric': geometric_animation,
    'sunset': sunset_animation,
    'heartbeat': heartbeat_animation,
    'bloom': bloom_animation,

    # Spotify-powered spectrum animations
    'spotify_spectrum': spotify_spectrum_analyzer,
    'energy_bars': energy_bars,
    'tempo_pulse': tempo_pulse,

    # Adaptive animations (respond to audio features)
    'adaptive_rainbow': adaptive_rainbow,
    'adaptive_pulse': adaptive_pulse,
    'adaptive_sparkle': adaptive_sparkle,
    'adaptive_matrix': adaptive_matrix,
    'auto_select': auto_select_animation
}

__all__ = [
    'ANIMATIONS',
    'rainbow_wave',
    'matrix_rain',
    'pulse_rings',
    'random_sparkle',
    'color_wipe',
    'snake',
    'fireworks',
    'rain',
    'wave_collision',
    'electronic_animation',
    'classical_animation',
    'rock_animation',
    'jazz_animation',
    'ambient_animation',
    'synthwave_animation',
    'lofi_animation',
    'meditation_animation',
    'party_animation',
    'focus_animation',
    'equalizer_animation',
    'equalizer_animation_microphone',
    'starfield_animation',
    'geometric_animation',
    'sunset_animation',
    'heartbeat_animation',
    'bloom_animation',
    'spotify_spectrum_analyzer',
    'energy_bars',
    'tempo_pulse',
    'adaptive_rainbow',
    'adaptive_pulse',
    'adaptive_sparkle',
    'adaptive_matrix',
    'auto_select_animation'
]
