"""Animation controller for managing LED animations."""

import threading
import time
from ..animations import ANIMATIONS
from ..hardware.launchpad import LaunchpadManager


class AnimationController:
    """Controls and manages LED animations."""

    # Mode pad LEDs — locked colors animations cannot override
    SESSION_PAD = (4, 8)
    USER1_PAD = (5, 8)
    USER2_PAD = (6, 8)
    MODE_LEDS = {
        'session': (SESSION_PAD, (0, 220, 255)),   # cyan
        'user1': (USER1_PAD, (0, 255, 80)),        # green
        'user2': (USER2_PAD, (255, 40, 180)),      # magenta
    }
    VALID_MODES = frozenset(MODE_LEDS.keys())

    def __init__(self, audio_analyzer=None, spotify_manager=None):
        self.launchpad = LaunchpadManager()
        self.current_animation = None
        self.last_animation = None
        self.should_run = True
        self.animation_thread = None
        # Mutual-exclusive pad modes: None | 'session' | 'user1' | 'user2'
        self.active_mode = None
        self.audio_analyzer = audio_analyzer
        self.spotify_manager = spotify_manager
        # When True, pad stays solid red (Spotify auth required)
        self.auth_lockout = False

    @property
    def animation_select_mode(self):
        """True when Session (animation select) mode is active."""
        return self.active_mode == 'session'

    def initialize(self):
        """Initialize the animation controller.

        Returns True even if the Launchpad is missing so the rest of the app
        (web API, Spotify, CLI) can still start.
        """
        self.launchpad.initialize()

        # Start animation worker thread
        self.animation_thread = threading.Thread(target=self._animation_worker, daemon=True)
        self.animation_thread.start()
        return True

    def set_auth_lockout(self, enabled):
        """Solid-red pad when Spotify auth is required.

        Args:
            enabled: True to force all LEDs red and pause animations
        """
        from ..hardware.launchpad import fill_all, clear_all

        was_enabled = self.auth_lockout
        self.auth_lockout = bool(enabled)

        if enabled:
            self.current_animation = None
            if self.launchpad.midi_out:
                fill_all(self.launchpad.midi_out, 255, 0, 0, force=True)
        elif was_enabled and self.launchpad.midi_out:
            clear_all(self.launchpad.midi_out)
            # Re-assert mode indicator if a pad mode is still on
            self._apply_mode_leds()

    def set_animation(self, animation_name):
        """Set the current animation.

        Args:
            animation_name: Name of the animation to start

        Returns:
            bool: True if animation was set successfully
        """
        if self.auth_lockout:
            print("Spotify auth required — animations locked. Type 'auth' to reconnect.")
            return False

        if animation_name in ANIMATIONS:
            # Clear screen when switching animations
            if self.current_animation != animation_name and self.launchpad.midi_out:
                from ..hardware.launchpad import clear_all
                clear_all(self.launchpad.midi_out)
            
            self.last_animation = self.current_animation = animation_name
            return True
        return False

    def stop_animation(self):
        """Stop the current animation."""
        if self.auth_lockout:
            return

        # Clear screen when stopping
        if self.launchpad.midi_out:
            from ..hardware.launchpad import clear_all
            clear_all(self.launchpad.midi_out)
        
        self.current_animation = None
        self.last_animation = None

    def get_available_animations(self):
        """Get list of available animations.

        Returns:
            list: List of animation names
        """
        return list(ANIMATIONS.keys())

    def _clear_all_mode_leds(self):
        """Unlock all mode indicator pads."""
        from ..hardware.launchpad import unlock_pad

        midi_out = self.launchpad.midi_out
        for pad, _color in self.MODE_LEDS.values():
            unlock_pad(midi_out, pad[0], pad[1], clear=True)

    def _apply_mode_leds(self):
        """Lock the active mode pad LED; unlock the others."""
        from ..hardware.launchpad import lock_pad, unlock_pad

        midi_out = self.launchpad.midi_out
        for mode, (pad, color) in self.MODE_LEDS.items():
            x, y = pad
            if mode == self.active_mode:
                lock_pad(midi_out, x, y, *color)
            else:
                unlock_pad(midi_out, x, y, clear=True)

    def set_active_mode(self, mode):
        """Set pad mode explicitly (None to clear).

        Args:
            mode: None | 'session' | 'user1' | 'user2'

        Returns:
            str|None: The resulting active_mode
        """
        if mode is not None and mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {mode}")
        self.active_mode = mode
        self._apply_mode_leds()
        return self.active_mode

    def toggle_mode(self, mode):
        """Toggle a pad mode. Activating one clears any other.

        Args:
            mode: 'session' | 'user1' | 'user2'

        Returns:
            bool: True if the mode is now active
        """
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {mode}")

        if self.active_mode == mode:
            self.set_active_mode(None)
            return False

        self.set_active_mode(mode)
        return True

    def toggle_animation_select_mode(self):
        """Toggle Session / animation selection mode."""
        return self.toggle_mode('session')

    def toggle_user_mode(self, profile):
        """Toggle User 1 / User 2 action mode.

        Args:
            profile: 'user1' or 'user2'

        Returns:
            bool: True if that user mode is now active
        """
        if profile not in ('user1', 'user2'):
            raise ValueError(f"Invalid user profile: {profile}")
        return self.toggle_mode(profile)

    def select_animation_by_position(self, x, y):
        """Select animation by grid position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            str: Selected animation name or None
        """
        if 0 <= x < 8 and 0 <= y <= 7:
            # Calculate animation index
            index = (7 - y) * 8 + x
            anim_list = sorted(list(ANIMATIONS.keys()))

            if index < len(anim_list):
                selected_animation = anim_list[index]
                self.set_animation(selected_animation)
                return selected_animation
        return None

    def _animation_worker(self):
        """Worker thread for running animations."""
        last_animation = None
        try:
            while self.should_run:
                if self.auth_lockout:
                    # Keep the pad red even if button effects flash briefly
                    if self.launchpad.midi_out:
                        from ..hardware.launchpad import fill_all
                        fill_all(self.launchpad.midi_out, 255, 0, 0, force=True)
                    last_animation = None
                    time.sleep(0.5)
                    continue

                if self.current_animation in ANIMATIONS:
                    # Clear screen when animation changes
                    if last_animation != self.current_animation and self.launchpad.midi_out:
                        from ..hardware.launchpad import clear_all
                        clear_all(self.launchpad.midi_out)
                        last_animation = self.current_animation
                    
                    # Create wrapper functions for animation parameters
                    should_run_func = lambda: self.should_run
                    current_animation_func = lambda: self.current_animation

                    # Check if animation supports audio features
                    animation_func = ANIMATIONS[self.current_animation]

                    # Try to call with audio analyzer if supported and enabled
                    try:
                        if (self.current_animation.startswith(('spotify_', 'adaptive_', 'energy_', 'tempo_', 'auto_')) and
                            self.audio_analyzer and self.audio_analyzer.is_enabled()):
                            animation_func(
                                self.launchpad.midi_out,
                                should_run_func,
                                current_animation_func,
                                audio_analyzer=self.audio_analyzer,
                                spotify_manager=self.spotify_manager
                            )
                        else:
                            animation_func(
                                self.launchpad.midi_out,
                                should_run_func,
                                current_animation_func
                            )
                    except TypeError:
                        # Fallback to standard call if audio parameters not supported
                        animation_func(
                            self.launchpad.midi_out,
                            should_run_func,
                            current_animation_func
                        )
                else:
                    # Animation stopped or None - clear screen and wait
                    if last_animation is not None and self.launchpad.midi_out:
                        from ..hardware.launchpad import clear_all
                        clear_all(self.launchpad.midi_out)
                        last_animation = None
                time.sleep(0.1)
        finally:
            if self.launchpad.midi_out:
                from ..hardware.launchpad import clear_all
                clear_all(self.launchpad.midi_out)

    def shutdown(self):
        """Shutdown the animation controller."""
        self.should_run = False
        if self.animation_thread:
            self.animation_thread.join(timeout=1)
        self.launchpad.close()
