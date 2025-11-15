"""MIDI message handler for Launchpad button presses."""

import time
import random
from ..effects.visual_effects import create_explosion_effect
from ..services.spotify_manager import get_active_or_default_device, format_track_info
from ..services.playlist_manager import get_playlist_id_by_name


class MidiHandler:
    """Handles MIDI input messages from Launchpad."""

    def __init__(self, animation_controller, spotify_manager, playlist_manager):
        self.animation_controller = animation_controller
        self.spotify_manager = spotify_manager
        self.playlist_manager = playlist_manager
        self.button_states = {}

    def on_midi_message(self, message, time_stamp):
        """Handle incoming MIDI messages.

        Args:
            message: MIDI message tuple (status, note, velocity)
            time_stamp: Message timestamp
        """
        status_byte, note, velocity = message[0]

        # Calculate button coordinates
        if note >= 104:  # Top row
            x = note - 104
            y = 8
        elif note % 10 == 9:  # Right column
            x = 8
            y = (note - 19) // 10
        else:  # Main grid
            x = (note - 11) % 10
            y = (note - 11) // 10

        button_id = f"{x},{y}"

        # Handle button press and release
        if velocity > 0:  # Button press
            # Skip if button is already pressed
            if button_id in self.button_states and self.button_states[button_id]:
                return

            # Mark button as pressed
            self.button_states[button_id] = True

            print(f"Button pressed - x: {x}, y: {y}, velocity: {velocity}")

            # Create explosion effect
            if self.animation_controller.launchpad.midi_out:
                create_explosion_effect(self.animation_controller.launchpad.midi_out, x, y)

            self._handle_button_press(x, y)

        else:  # Button release (velocity = 0)
            # Mark button as released
            self.button_states[button_id] = False

    def _handle_button_press(self, x, y):
        """Handle specific button press logic.

        Args:
            x: X coordinate of pressed button
            y: Y coordinate of pressed button
        """
        # Session button (4,8) - Toggle animation selection mode
        if x == 4 and y == 8:
            mode = self.animation_controller.toggle_animation_select_mode()
            if mode:
                self._show_animation_selection_guide()
            else:
                print("Exited animation selection mode")
            return

        # Handle animation selection mode
        if self.animation_controller.animation_select_mode:
            selected = self.animation_controller.select_animation_by_position(x, y)
            if selected:
                print(f"Selected animation: {selected}")
            return

        # Mixer button (7,8) for random playlist
        if x == 7 and y == 8:
            self._play_random_playlist()
            return

        # Control buttons (top row)
        if y == 8:
            self._handle_control_button(x)
        else:  # Regular playlist buttons
            self._play_playlist_for_button(x, y)

    def _show_animation_selection_guide(self):
        """Display animation selection guide in terminal."""
        print("\n=== ANIMATION SELECTION MODE ===")
        print("Tap a button to select an animation:")

        # Get sorted list of animations
        anim_list = sorted(self.animation_controller.get_available_animations())

        # Display animations grid mapping
        for i, anim_name in enumerate(anim_list):
            if i < 64:  # We have 64 buttons available (8x8 grid)
                # Calculate grid position (0,7 to 7,0)
                x = i % 8
                y = 7 - (i // 8)
                print(f"Button ({x},{y}): {anim_name}")

        print("\nTap session button (4,8) again to exit animation selection mode")
        print("================================")

    def _handle_control_button(self, x):
        """Handle control button presses in top row.

        Args:
            x: X coordinate of control button
        """
        if not self.spotify_manager or not self.spotify_manager.spotify:
            print("Spotify not available")
            return

        spotify = self.spotify_manager.spotify

        if x == 0:  # Volume Up
            try:
                device_id = get_active_or_default_device(spotify)
                if device_id:
                    current = spotify.current_playback()
                    if current and current['device']:
                        volume = min(100, current['device']['volume_percent'] + 10)
                        spotify.volume(volume, device_id=device_id)
                        print(f"Volume up: {volume}%")
            except Exception as e:
                print(f"Error adjusting volume: {e}")

        elif x == 1:  # Volume Down
            try:
                device_id = get_active_or_default_device(spotify)
                if device_id:
                    current = spotify.current_playback()
                    if current and current['device']:
                        volume = max(0, current['device']['volume_percent'] - 10)
                        spotify.volume(volume, device_id=device_id)
                        print(f"Volume down: {volume}%")
            except Exception as e:
                print(f"Error adjusting volume: {e}")

        elif x == 2:  # Previous Track
            try:
                device_id = get_active_or_default_device(spotify)
                if device_id:
                    spotify.previous_track(device_id=device_id)
                    time.sleep(0.1)
                    current = spotify.current_playback()
                    if current and current['item']:
                        print(f"Previous track: {format_track_info(current['item'], current['progress_ms'])}")
            except Exception as e:
                print(f"Error: {e}")

        elif x == 3:  # Next Track
            try:
                device_id = get_active_or_default_device(spotify)
                if device_id:
                    spotify.next_track(device_id=device_id)
                    time.sleep(0.1)
                    current = spotify.current_playback()
                    if current and current['item']:
                        print(f"Next track: {format_track_info(current['item'], current['progress_ms'])}")
            except Exception as e:
                print(f"Error: {e}")

        elif x == 5:  # Play/Pause
            try:
                device_id = get_active_or_default_device(spotify)
                if not device_id:
                    print("No active device found")
                    return

                current = spotify.current_playback()
                if current and current['is_playing']:
                    spotify.pause_playback(device_id=device_id)
                    print("Playback paused")
                    self.animation_controller.stop_animation()
                else:
                    spotify.start_playback(device_id=device_id)
                    print("Playback started")
                    if self.animation_controller.last_animation:
                        self.animation_controller.set_animation(self.animation_controller.last_animation)
            except Exception as e:
                print(f"Error toggling playback: {e}")

    def _play_playlist_for_button(self, x, y):
        """Handle playlist button press.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self.spotify_manager or not self.spotify_manager.spotify:
            print("Spotify not initialized")
            return

        mapping = self.playlist_manager.get_mapping(x, y)
        if not mapping:
            return

        playlist_name = mapping['name']
        spotify = self.spotify_manager.spotify

        try:
            # Get device
            device_id = get_active_or_default_device(spotify)
            if not device_id:
                print("No active device found")
                return

            # Handle animation if specified
            if mapping.get('animation'):
                if self.animation_controller.set_animation(mapping['animation']):
                    print(f"Changed animation to: {mapping['animation']}")

            # Play the playlist
            playlist_id = get_playlist_id_by_name(playlist_name)
            if playlist_id:
                spotify.start_playback(
                    device_id=device_id,
                    context_uri=f'spotify:playlist:{playlist_id}'
                )
                # Wait briefly for playback to start
                time.sleep(0.1)
                current = spotify.current_playback()
                if current and current['item']:
                    print(f"Playing: {format_track_info(current['item'], current['progress_ms'])}")
                print(f"Playing playlist: {playlist_name}")
            else:
                print(f"Playlist not found: {playlist_name}")

        except Exception as e:
            print(f"Error playing playlist: {str(e)}")

    def _play_random_playlist(self):
        """Play a random playlist from the mapped playlists."""
        if not self.spotify_manager or not self.spotify_manager.spotify:
            print("Spotify not initialized")
            return

        try:
            # Get all mapped playlists
            playlists = [mapping['name'] for mapping in self.playlist_manager.mappings.values()]

            if not playlists:
                print("No playlists mapped!")
                return

            # Select random playlist
            random_playlist = random.choice(playlists)
            print(f"\nRandomly selected: {random_playlist}")

            # Get device and play
            device_id = get_active_or_default_device(self.spotify_manager.spotify)
            if device_id:
                playlist_id = get_playlist_id_by_name(random_playlist)
                if playlist_id:
                    self.spotify_manager.spotify.start_playback(
                        device_id=device_id,
                        context_uri=f'spotify:playlist:{playlist_id}'
                    )
                    # Wait briefly for playback to start
                    time.sleep(0.1)
                    current = self.spotify_manager.spotify.current_playback()
                    if current and current['item']:
                        print(f"Playing: {format_track_info(current['item'], current['progress_ms'])}")
                    print(f"Playing playlist: {random_playlist}")

                    # Update animation if specified
                    for mapping in self.playlist_manager.mappings.values():
                        if mapping['name'] == random_playlist and mapping.get('animation'):
                            self.animation_controller.set_animation(mapping['animation'])
                            print(f"Changed animation to: {mapping['animation']}")
                            break

        except Exception as e:
            print(f"Error playing random playlist: {e}")
