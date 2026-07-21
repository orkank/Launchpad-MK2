"""Spotify status monitoring for automatic animation changes."""

import random
import threading
import time

from ..animations import ANIMATIONS
from ..services.spotify_manager import format_track_info, is_auth_failure

# Never auto-pick these for "random song" fallback
_RANDOM_ANIMATION_EXCLUDE = {
    'equalizer_microphone',
    # Spotify audio-features dependent (often 403 / disabled)
    'spotify_spectrum',
    'energy_bars',
    'tempo_pulse',
    'adaptive_rainbow',
    'adaptive_pulse',
    'adaptive_sparkle',
    'adaptive_matrix',
    'auto_select',
}


class StatusMonitor:
    """Monitors Spotify playback status and updates animations accordingly."""

    def __init__(self, spotify_manager, animation_controller, playlist_manager):
        self.spotify_manager = spotify_manager
        self.animation_controller = animation_controller
        self.playlist_manager = playlist_manager
        self.should_run = True
        self.monitor_thread = None

    def start(self):
        """Start the status monitoring thread."""
        self.should_run = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """Stop the status monitoring thread."""
        self.should_run = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
            self.monitor_thread = None

    def _monitor_loop(self):
        """Main monitoring loop."""
        last_track_id = None
        last_is_playing = None
        last_playlist_id = object()  # sentinel so first context always "changes"

        while self.should_run:
            try:
                # Wait quietly while auth is broken instead of spamming API errors
                if (not self.spotify_manager or
                        self.spotify_manager.needs_reauth or
                        not self.spotify_manager.spotify):
                    time.sleep(2)
                    continue

                current = self.spotify_manager.get_current_playback()

                if current:
                    track_id = current['item']['id'] if current.get('item') else None
                    is_playing = bool(current.get('is_playing'))
                    playlist_id = self._playlist_id_from_context(current.get('context'))

                    track_changed = track_id != last_track_id
                    play_state_changed = is_playing != last_is_playing
                    context_changed = playlist_id != last_playlist_id

                    if track_changed and current.get('item'):
                        print(f"Now playing: {format_track_info(current['item'], current['progress_ms'])}")

                    if play_state_changed:
                        print(f"Playback {'resumed' if is_playing else 'paused'}")

                    if not is_playing:
                        if self.animation_controller.current_animation:
                            self.animation_controller.stop_animation()
                    else:
                        self._sync_animation_for_playback(
                            playlist_id=playlist_id,
                            context_changed=context_changed,
                            play_state_changed=play_state_changed,
                        )

                    last_track_id = track_id
                    last_is_playing = is_playing
                    last_playlist_id = playlist_id

                time.sleep(1)  # Poll every second

            except Exception as e:
                from ..services.spotify_manager import is_transient_token_error
                if is_auth_failure(e):
                    self.spotify_manager.mark_auth_failed(e)
                    continue
                if is_transient_token_error(e):
                    time.sleep(1)
                    continue
                print(f"Status monitor error: {e}")
                time.sleep(5)  # Wait longer on error

    def _playlist_id_from_context(self, context):
        """Return Spotify playlist id from playback context, or None."""
        if not context or context.get('type') != 'playlist':
            return None
        uri = context.get('uri') or ''
        if not uri:
            return None
        return uri.split(':')[-1]

    def _sync_animation_for_playback(self, playlist_id, context_changed, play_state_changed):
        """Ensure the right animation runs for mapped playlist vs random fallback."""
        ac = self.animation_controller
        if getattr(ac, 'auth_lockout', False):
            return

        mapped_animation = self._get_playlist_animation(playlist_id) if playlist_id else None

        if mapped_animation:
            # Mapped playlist: switch when context changes, resumes, or nothing is running
            if context_changed or play_state_changed or not ac.current_animation:
                if ac.current_animation != mapped_animation:
                    if ac.set_animation(mapped_animation):
                        print(f"Changed animation to: {mapped_animation}")
            return

        # Unmapped: album / radio / liked songs / playlist without mapping
        if context_changed:
            # Left a mapped playlist (or entered non-playlist playback) → new random
            self._start_random_animation()
            return

        if not ac.current_animation:
            # Resume after pause: prefer last animation; otherwise pick random
            if play_state_changed and ac.last_animation:
                if ac.set_animation(ac.last_animation):
                    print(f"Resumed animation: {ac.last_animation}")
            else:
                self._start_random_animation()

    def _start_random_animation(self):
        """Pick and start a random animation (for unmapped playback)."""
        ac = self.animation_controller
        if getattr(ac, 'auth_lockout', False):
            return

        choices = [
            name for name in ANIMATIONS.keys()
            if name not in _RANDOM_ANIMATION_EXCLUDE
        ]
        if not choices:
            return

        name = random.choice(choices)
        if ac.set_animation(name):
            print(f"Started random animation: {name}")

    def _get_playlist_animation(self, playlist_id):
        """Get animation for playlist if configured.

        Args:
            playlist_id: Spotify playlist ID

        Returns:
            str: Animation name or None
        """
        try:
            playlist = self.spotify_manager.api_call('playlist', playlist_id, quiet=True)
            if not playlist:
                return None
            playlist_name = playlist['name']

            # Check if this playlist exists in our mappings
            for mapping in self.playlist_manager.mappings.values():
                if mapping['name'] == playlist_name and mapping.get('animation'):
                    return mapping['animation']
        except Exception as e:
            if is_auth_failure(e):
                self.spotify_manager.mark_auth_failed(e)
            else:
                print(f"Error getting playlist animation: {e}")
        return None
