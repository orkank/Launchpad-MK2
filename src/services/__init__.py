"""Service modules for external integrations.

This module contains service integrations for Spotify, playlist management, and other external APIs.
"""

from .spotify_manager import (
    SpotifyManager,
    initialize_spotify,
    get_current_audio_features,
    format_track_info
)

from .playlist_manager import (
    PlaylistManager,
    load_playlist_mappings,
    generate_playlist_mappings,
    randomize_animations,
    show_playlist_animation_preview
)

from .audio_analyzer import AudioAnalyzer, create_audio_analyzer

__all__ = [
    'SpotifyManager',
    'initialize_spotify',
    'get_current_audio_features',
    'format_track_info',
    'PlaylistManager',
    'load_playlist_mappings',
    'generate_playlist_mappings',
    'randomize_animations',
    'show_playlist_animation_preview',
    'AudioAnalyzer',
    'create_audio_analyzer'
]
