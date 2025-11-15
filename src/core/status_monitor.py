"""Spotify status monitoring for automatic animation changes."""

import threading
import time
from ..services.spotify_manager import format_track_info


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
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """Stop the status monitoring thread."""
        self.should_run = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

    def _monitor_loop(self):
        """Main monitoring loop."""
        last_track_id = None
        last_is_playing = None
        last_playlist_id = None

        while self.should_run:
            try:
                if not self.spotify_manager or not self.spotify_manager.spotify:
                    time.sleep(5)
                    continue

                current = self.spotify_manager.spotify.current_playback()

                if current:
                    # Track change detection
                    track_id = current['item']['id'] if current['item'] else None
                    if track_id != last_track_id:
                        last_track_id = track_id
                        if current['item']:
                            print(f"Now playing: {format_track_info(current['item'], current['progress_ms'])}")

                    # Play/Pause state change
                    is_playing = current['is_playing']
                    if is_playing != last_is_playing:
                        last_is_playing = is_playing
                        print(f"Playback {'resumed' if is_playing else 'paused'}")

                    if not is_playing:
                        self.animation_controller.stop_animation()
                    else:
                        if self.animation_controller.last_animation:
                            self.animation_controller.set_animation(self.animation_controller.last_animation)

                    # Playlist change detection
                    context = current.get('context')
                    if context and context['type'] == 'playlist':
                        playlist_id = context['uri'].split(':')[-1]
                        if playlist_id != last_playlist_id:
                            last_playlist_id = playlist_id
                            # Get playlist name
                            try:
                                playlist = self.spotify_manager.spotify.playlist(playlist_id)
                                print(f"Current playlist: {playlist['name']}")

                                # Handle animation if specified
                                playlist_animation = self._get_playlist_animation(playlist_id)
                                if playlist_animation:
                                    if self.animation_controller.set_animation(playlist_animation):
                                        print(f"Changed animation to: {playlist_animation}")
                            except:
                                pass

                time.sleep(1)  # Poll every second

            except Exception as e:
                print(f"Status monitor error: {e}")
                time.sleep(5)  # Wait longer on error

    def _get_playlist_animation(self, playlist_id):
        """Get animation for playlist if configured.

        Args:
            playlist_id: Spotify playlist ID

        Returns:
            str: Animation name or None
        """
        try:
            playlist = self.spotify_manager.spotify.playlist(playlist_id)
            playlist_name = playlist['name']

            # Check if this playlist exists in our mappings
            for mapping in self.playlist_manager.mappings.values():
                if mapping['name'] == playlist_name and mapping.get('animation'):
                    return mapping['animation']
        except Exception as e:
            print(f"Error getting playlist animation: {e}")
        return None
