"""Animation controller for managing LED animations."""

import threading
import time
from ..animations import ANIMATIONS
from ..hardware.launchpad import LaunchpadManager


class AnimationController:
    """Controls and manages LED animations."""

    def __init__(self, audio_analyzer=None, spotify_manager=None):
        self.launchpad = LaunchpadManager()
        self.current_animation = None
        self.last_animation = None
        self.should_run = True
        self.animation_thread = None
        self.animation_select_mode = False
        self.audio_analyzer = audio_analyzer
        self.spotify_manager = spotify_manager

    def initialize(self):
        """Initialize the animation controller."""
        if not self.launchpad.initialize():
            return False

        # Start animation worker thread
        self.animation_thread = threading.Thread(target=self._animation_worker, daemon=True)
        self.animation_thread.start()
        return True

    def set_animation(self, animation_name):
        """Set the current animation.

        Args:
            animation_name: Name of the animation to start

        Returns:
            bool: True if animation was set successfully
        """
        if animation_name in ANIMATIONS:
            self.last_animation = self.current_animation = animation_name
            return True
        return False

    def stop_animation(self):
        """Stop the current animation."""
        self.current_animation = None

    def get_available_animations(self):
        """Get list of available animations.

        Returns:
            list: List of animation names
        """
        return list(ANIMATIONS.keys())

    def toggle_animation_select_mode(self):
        """Toggle animation selection mode."""
        self.animation_select_mode = not self.animation_select_mode
        return self.animation_select_mode

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
        try:
            while self.should_run:
                if self.current_animation in ANIMATIONS:
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
                    if self.launchpad.midi_out:
                        from ..hardware.launchpad import clear_all
                        clear_all(self.launchpad.midi_out)
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
