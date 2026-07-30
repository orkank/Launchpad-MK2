"""MIDI message handler for Launchpad button presses."""

import time
import random
from ..effects.visual_effects import create_explosion_effect
from ..services.spotify_manager import get_active_or_default_device, format_track_info
from ..services.playlist_manager import get_playlist_id_by_name


class MidiHandler:
    """Handles MIDI input messages from Launchpad."""

    def __init__(
        self,
        animation_controller,
        spotify_manager,
        playlist_manager,
        user_action_manager=None,
        action_executor=None,
    ):
        self.animation_controller = animation_controller
        self.spotify_manager = spotify_manager
        self.playlist_manager = playlist_manager
        self.user_action_manager = user_action_manager
        self.action_executor = action_executor
        self.button_states = {}
        # Mapping capture: kind is 'playlist' | 'user1' | 'user2'
        self.mapping_mode = False
        self.mapping_kind = None
        self.pending_mapping = None
        self.last_mapping_message = None
        self.pending_confirmation = None

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
        # Handle mapping mode first (highest priority)
        if self.mapping_mode:
            self._handle_mapping_mode_button(x, y)
            return

        # Session button (4,8) - Toggle animation selection mode
        if x == 4 and y == 8:
            mode = self.animation_controller.toggle_animation_select_mode()
            if mode:
                self._show_animation_selection_guide()
            else:
                print("Exited animation selection mode")
            return

        # User 1 (5,8) / User 2 (6,8) - custom action modes
        if x == 5 and y == 8:
            active = self.animation_controller.toggle_user_mode('user1')
            print("Entered User 1 mode" if active else "Exited User 1 mode")
            return

        if x == 6 and y == 8:
            active = self.animation_controller.toggle_user_mode('user2')
            print("Entered User 2 mode" if active else "Exited User 2 mode")
            return

        # Play/Pause moved to right column (8,0)
        if x == 8 and y == 0:
            self._toggle_play_pause()
            return

        active_mode = self.animation_controller.active_mode

        # Handle animation selection mode
        if active_mode == 'session':
            selected = self.animation_controller.select_animation_by_position(x, y)
            if selected:
                print(f"Selected animation: {selected}")
            return

        # User action modes
        if active_mode in ('user1', 'user2'):
            self._run_user_action(active_mode, x, y)
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

    def _run_user_action(self, profile, x, y):
        """Run the mapped user action for a pad (grid only)."""
        if not (0 <= x < 8 and 0 <= y <= 7):
            return
        if not self.user_action_manager or not self.action_executor:
            print("User actions not configured")
            return

        action = self.user_action_manager.get(profile, x, y)
        if not action:
            return

        label = action.get('label') or action.get('type')
        print(f"User action [{profile}] ({x},{y}): {label}")
        self.action_executor.run(action)

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

    def _toggle_play_pause(self):
        """Toggle Spotify play/pause and related animation state."""
        if not self.spotify_manager or not self.spotify_manager.ensure_ready():
            return

        sm = self.spotify_manager
        try:
            device_id = get_active_or_default_device(sm.spotify, sm)
            if not device_id:
                print("No active device found")
                return

            current = sm.get_current_playback()
            if current and current['is_playing']:
                sm.api_call('pause_playback', device_id=device_id)
                print("Playback paused")
                self.animation_controller.stop_animation()
            else:
                sm.api_call('start_playback', device_id=device_id)
                print("Playback started")
                if self.animation_controller.last_animation:
                    self.animation_controller.set_animation(self.animation_controller.last_animation)
        except Exception as e:
            if not sm.handle_api_error(e):
                print(f"Error toggling playback: {e}")

    def _handle_control_button(self, x):
        """Handle control button presses in top row.

        Args:
            x: X coordinate of control button
        """
        if not self.spotify_manager or not self.spotify_manager.ensure_ready():
            return

        sm = self.spotify_manager

        if x == 0:  # Volume Up
            try:
                device_id = get_active_or_default_device(sm.spotify, sm)
                if device_id:
                    current = sm.get_current_playback()
                    if current and current['device']:
                        volume = min(100, current['device']['volume_percent'] + 10)
                        sm.api_call('volume', volume, device_id=device_id)
                        print(f"Volume up: {volume}%")
            except Exception as e:
                if not sm.handle_api_error(e):
                    print(f"Error adjusting volume: {e}")

        elif x == 1:  # Volume Down
            try:
                device_id = get_active_or_default_device(sm.spotify, sm)
                if device_id:
                    current = sm.get_current_playback()
                    if current and current['device']:
                        volume = max(0, current['device']['volume_percent'] - 10)
                        sm.api_call('volume', volume, device_id=device_id)
                        print(f"Volume down: {volume}%")
            except Exception as e:
                if not sm.handle_api_error(e):
                    print(f"Error adjusting volume: {e}")

        elif x == 2:  # Previous Track
            try:
                device_id = get_active_or_default_device(sm.spotify, sm)
                if device_id:
                    sm.api_call('previous_track', device_id=device_id)
                    time.sleep(0.1)
                    current = sm.get_current_playback()
                    if current and current['item']:
                        print(f"Previous track: {format_track_info(current['item'], current['progress_ms'])}")
            except Exception as e:
                if not sm.handle_api_error(e):
                    print(f"Error: {e}")

        elif x == 3:  # Next Track
            try:
                device_id = get_active_or_default_device(sm.spotify, sm)
                if device_id:
                    sm.api_call('next_track', device_id=device_id)
                    time.sleep(0.1)
                    current = sm.get_current_playback()
                    if current and current['item']:
                        print(f"Next track: {format_track_info(current['item'], current['progress_ms'])}")
            except Exception as e:
                if not sm.handle_api_error(e):
                    print(f"Error: {e}")

    def _play_playlist_for_button(self, x, y):
        """Handle playlist button press.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self.spotify_manager or not self.spotify_manager.ensure_ready():
            return

        mapping = self.playlist_manager.get_mapping(x, y)
        if not mapping:
            return

        playlist_name = mapping['name']
        sm = self.spotify_manager

        try:
            # Get device
            device_id = get_active_or_default_device(sm.spotify, sm)
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
                sm.api_call(
                    'start_playback',
                    device_id=device_id,
                    context_uri=f'spotify:playlist:{playlist_id}'
                )
                # Wait briefly for playback to start
                time.sleep(0.1)
                current = sm.get_current_playback()
                if current and current['item']:
                    print(f"Playing: {format_track_info(current['item'], current['progress_ms'])}")
                print(f"Playing playlist: {playlist_name}")
            else:
                print(f"Playlist not found: {playlist_name}")

        except Exception as e:
            if not self.spotify_manager.handle_api_error(e):
                print(f"Error playing playlist: {str(e)}")

    def _play_random_playlist(self):
        """Play a random playlist from the mapped playlists."""
        if not self.spotify_manager or not self.spotify_manager.ensure_ready():
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
            sm = self.spotify_manager
            device_id = get_active_or_default_device(sm.spotify, sm)
            if device_id:
                playlist_id = get_playlist_id_by_name(random_playlist)
                if playlist_id:
                    sm.api_call(
                        'start_playback',
                        device_id=device_id,
                        context_uri=f'spotify:playlist:{playlist_id}'
                    )
                    # Wait briefly for playback to start
                    time.sleep(0.1)
                    current = sm.get_current_playback()
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
            if not self.spotify_manager.handle_api_error(e):
                print(f"Error playing random playlist: {e}")

    def is_system_reserved(self, x, y):
        """Check if a button is system reserved and cannot be mapped.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            bool: True if button is system reserved
        """
        # Top row (y=8) is reserved for controls
        if y == 8:
            return True
        # Right column (x=8) is reserved
        if x == 8:
            return True
        return False

    def start_mapping_mode(self, playlist_name, animation_name=None):
        """Start mapping mode to capture button press for a playlist.

        Args:
            playlist_name: Name of playlist to map
            animation_name: Optional animation name

        Returns:
            bool: True if mapping mode started successfully
        """
        if self.mapping_mode:
            return False  # Already in mapping mode

        self.mapping_mode = True
        self.mapping_kind = 'playlist'
        self.pending_mapping = {
            'playlist': playlist_name,
            'animation': animation_name
        }
        self.last_mapping_message = None
        self.pending_confirmation = None

        print(f"\n=== MAPPING MODE ===")
        print(f"Playlist: {playlist_name}")
        if animation_name:
            print(f"Animation: {animation_name}")
        print("Press a button on your Launchpad to map this playlist.")
        print("System reserved buttons (top row and right column) are not allowed.")
        print("================================")
        return True

    def start_user_action_mapping(self, profile, action):
        """Start mapping mode to assign a user action to a pad.

        Args:
            profile: 'user1' or 'user2'
            action: Action dict (type, label, and type-specific fields)

        Returns:
            bool: True if mapping mode started successfully
        """
        if self.mapping_mode:
            return False
        if profile not in ('user1', 'user2'):
            return False
        if not isinstance(action, dict) or not action.get('type'):
            return False
        if not self.user_action_manager:
            return False

        self.mapping_mode = True
        self.mapping_kind = profile
        self.pending_mapping = {'profile': profile, 'action': action}
        self.last_mapping_message = None
        self.pending_confirmation = None

        label = action.get('label') or action.get('type')
        print(f"\n=== USER ACTION MAPPING ({profile}) ===")
        print(f"Action: {label} [{action.get('type')}]")
        print("Press a grid button on your Launchpad to map this action.")
        print("================================")
        return True

    def cancel_mapping_mode(self):
        """Cancel mapping mode."""
        if self.mapping_mode:
            self.mapping_mode = False
            self.mapping_kind = None
            self.pending_mapping = None
            self.pending_confirmation = None
            self.last_mapping_message = {'type': 'warning', 'message': 'Mapping mode cancelled.'}
            print("Mapping mode cancelled.")
            return True
        return False

    def get_mapping_status(self):
        """Get current mapping mode status.

        Returns:
            dict: Mapping status information
        """
        status = {
            'active': self.mapping_mode,
            'kind': self.mapping_kind,
            'pending': self.pending_mapping,
            'last_message': self.last_mapping_message,
            'pending_confirmation': self.pending_confirmation
        }
        # Clear message after reading (one-time notification)
        if self.last_mapping_message:
            self.last_mapping_message = None
        return status

    def get_user_action_status(self):
        """Status for user-action mapping + last executor message."""
        status = self.get_mapping_status()
        if self.action_executor:
            exec_msg = self.action_executor.pop_last_message()
            if exec_msg:
                status['last_action_message'] = exec_msg
        return status

    def _handle_mapping_mode_button(self, x, y):
        """Handle button press during mapping mode.

        Args:
            x: X coordinate of pressed button
            y: Y coordinate of pressed button
        """
        if not self.pending_mapping:
            self.mapping_mode = False
            self.mapping_kind = None
            return

        # Check if button is system reserved
        if self.is_system_reserved(x, y):
            message = f"⚠️ Button ({x},{y}) is system reserved and cannot be mapped! Please press a different button."
            print(f"⚠️  Button ({x},{y}) is system reserved and cannot be mapped!")
            print("Please press a different button.")
            self.last_mapping_message = {'type': 'error', 'message': message}
            return

        if self.mapping_kind in ('user1', 'user2'):
            self._handle_user_action_mapping_button(x, y)
            return

        # Playlist mapping
        existing_mapping = self.playlist_manager.get_mapping(x, y)
        if existing_mapping:
            playlist_name = self.pending_mapping['playlist']
            animation_name = self.pending_mapping.get('animation')

            self.pending_confirmation = {
                'x': x,
                'y': y,
                'playlist': playlist_name,
                'animation': animation_name,
                'existing': existing_mapping
            }

            existing_info = f"Playlist: {existing_mapping['name']}"
            if existing_mapping.get('animation'):
                existing_info += f", Animation: {existing_mapping['animation']}"

            message = f"⚠️ Button ({x},{y}) is already mapped to {existing_info}. Waiting for confirmation..."
            print(f"⚠️  Button ({x},{y}) is already mapped to:")
            print(f"   Playlist: {existing_mapping['name']}")
            if existing_mapping.get('animation'):
                print(f"   Animation: {existing_mapping['animation']}")
            print("Waiting for confirmation from web interface...")
            self.last_mapping_message = {'type': 'warning', 'message': message}
            return

        self._save_mapping(x, y)

    def _handle_user_action_mapping_button(self, x, y):
        """Handle pad press while capturing a user action mapping."""
        profile = self.mapping_kind
        action = self.pending_mapping.get('action')
        existing = self.user_action_manager.get(profile, x, y) if self.user_action_manager else None

        if existing:
            self.pending_confirmation = {
                'x': x,
                'y': y,
                'profile': profile,
                'action': action,
                'existing': existing,
            }
            label = existing.get('label') or existing.get('type')
            message = (
                f"⚠️ Button ({x},{y}) already has action '{label}'. Waiting for confirmation..."
            )
            print(message)
            self.last_mapping_message = {'type': 'warning', 'message': message}
            return

        self._save_user_action_mapping(x, y)

    def _save_user_action_mapping(self, x, y):
        """Persist a user action mapping at coordinates."""
        if self.pending_confirmation and self.pending_confirmation.get('profile'):
            profile = self.pending_confirmation['profile']
            action = self.pending_confirmation['action']
            x = self.pending_confirmation['x']
            y = self.pending_confirmation['y']
            self.pending_confirmation = None
        elif self.pending_mapping and self.mapping_kind in ('user1', 'user2'):
            profile = self.mapping_kind
            action = self.pending_mapping['action']
        else:
            return

        self.user_action_manager.set(profile, x, y, action)
        self.user_action_manager.save()

        label = action.get('label') or action.get('type')
        success_msg = f"✅ User action saved! [{profile}] ({x},{y}) → {label} ({action.get('type')})"
        print(f"\n{success_msg}")
        self.last_mapping_message = {'type': 'success', 'message': success_msg}

        self.mapping_mode = False
        self.mapping_kind = None
        self.pending_mapping = None

    def _save_mapping(self, x, y):
        """Save playlist mapping for coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if self.pending_confirmation and 'playlist' in self.pending_confirmation:
            playlist_name = self.pending_confirmation['playlist']
            animation_name = self.pending_confirmation.get('animation')
            x = self.pending_confirmation['x']
            y = self.pending_confirmation['y']
            self.pending_confirmation = None
        elif self.pending_mapping and self.mapping_kind == 'playlist':
            playlist_name = self.pending_mapping['playlist']
            animation_name = self.pending_mapping.get('animation')
        else:
            return

        self.playlist_manager.set_mapping(x, y, playlist_name, animation_name)
        self.playlist_manager.save_mappings()

        success_msg = f"✅ Mapping saved! Button ({x},{y}) → Playlist: {playlist_name}"
        if animation_name:
            success_msg += f", Animation: {animation_name}"

        print(f"\n✅ Mapping saved!")
        print(f"   Button ({x},{y}) → Playlist: {playlist_name}")
        if animation_name:
            print(f"   Animation: {animation_name}")

        self.last_mapping_message = {'type': 'success', 'message': success_msg}

        self.mapping_mode = False
        self.mapping_kind = None
        self.pending_mapping = None

    def confirm_overwrite(self):
        """Confirm overwrite of existing mapping.

        Returns:
            bool: True if confirmation was processed, False if no pending confirmation
        """
        if not self.pending_confirmation:
            return False

        x = self.pending_confirmation['x']
        y = self.pending_confirmation['y']
        if self.pending_confirmation.get('profile'):
            self._save_user_action_mapping(x, y)
        else:
            self._save_mapping(x, y)
        return True

    def cancel_overwrite(self):
        """Cancel overwrite of existing mapping.

        Returns:
            bool: True if cancellation was processed, False if no pending confirmation
        """
        if not self.pending_confirmation:
            return False

        self.pending_confirmation = None
        self.mapping_mode = False
        self.mapping_kind = None
        self.pending_mapping = None
        self.last_mapping_message = {'type': 'warning', 'message': 'Mapping cancelled. No changes made.'}
        print("Mapping cancelled by user.")
        return True
