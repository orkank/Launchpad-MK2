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
    bloom_animation,
    aurora_animation,
    galaxy_animation,
    neon_grid_animation,
    lava_lamp_animation,
    prism_animation
)

from .spectrum import (
    spotify_spectrum_analyzer,
    energy_bars,
    tempo_pulse
)

from .extra import (
    checker_pulse,
    spiral_trail,
    meteor_shower,
    plasma_field,
    binary_cascade,
    orbital_dots,
    scan_sweep,
    ember_rise,
    ripple_pool,
    vortex_spin,
)

# Adaptive animations are disabled — Spotify audio-features often 403;
# kept in adaptive.py but not registered for selection.

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
    'aurora': aurora_animation,
    'galaxy': galaxy_animation,
    'neon_grid': neon_grid_animation,
    'lava_lamp': lava_lamp_animation,
    'prism': prism_animation,

    # Extra pack
    'checker_pulse': checker_pulse,
    'spiral_trail': spiral_trail,
    'meteor_shower': meteor_shower,
    'plasma_field': plasma_field,
    'binary_cascade': binary_cascade,
    'orbital_dots': orbital_dots,
    'scan_sweep': scan_sweep,
    'ember_rise': ember_rise,
    'ripple_pool': ripple_pool,
    'vortex_spin': vortex_spin,

    # Spotify-powered spectrum animations
    'spotify_spectrum': spotify_spectrum_analyzer,
    'energy_bars': energy_bars,
    'tempo_pulse': tempo_pulse,
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
    'aurora_animation',
    'galaxy_animation',
    'neon_grid_animation',
    'lava_lamp_animation',
    'prism_animation',
    'checker_pulse',
    'spiral_trail',
    'meteor_shower',
    'plasma_field',
    'binary_cascade',
    'orbital_dots',
    'scan_sweep',
    'ember_rise',
    'ripple_pool',
    'vortex_spin',
    'spotify_spectrum_analyzer',
    'energy_bars',
    'tempo_pulse',
]
