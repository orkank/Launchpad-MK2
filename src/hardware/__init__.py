"""Hardware interface modules for Launchpad MK2.

This module contains hardware-specific code for MIDI communication, audio input, and device management.
"""

from .launchpad import (
    initialize_launchpad,
    set_color,
    clear_all,
    LaunchpadManager
)

from .audio import initialize_audio

__all__ = [
    'initialize_launchpad',
    'set_color',
    'clear_all',
    'LaunchpadManager',
    'initialize_audio'
]
