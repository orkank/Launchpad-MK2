"""Main application entry point for Launchpad MK2 Spotify Controller."""

import argparse
import select
import sys
import threading
import time

from .core.animation_controller import AnimationController
from .core.midi_handler import MidiHandler
from .core.status_monitor import StatusMonitor
from .services.spotify_manager import (
    SpotifyManager,
    initialize_spotify,
    show_spotify_devices,
    fetch_and_save_playlists,
    set_oauth_redirect_uri,
    configure_spotipy_logging,
)
from .services.playlist_manager import (
    PlaylistManager,
    generate_playlist_mappings,
    randomize_animations
)
from .services.user_action_manager import UserActionManager
from .services.action_executor import ActionExecutor
from .services.audio_analyzer import create_audio_analyzer
from .utils.config_manager import config_manager
from .animations import ANIMATIONS
from .api.flask_app import create_app
from .utils.helpers import print_available_animations, print_available_playlists
from .utils.help_system import show_help, show_quick_status
from .utils.auth_alert import AuthAlertService, print_auth_warning
from .utils.midi_health import MidiHealthMonitor


class LaunchpadController:
    """Main application controller."""

    def __init__(self):
        self.spotify_manager = SpotifyManager()
        self.playlist_manager = PlaylistManager()
        self.user_action_manager = UserActionManager()
        self.action_executor = ActionExecutor()
        self.audio_analyzer = None
        self.animation_controller = None
        self.midi_handler = None
        self.status_monitor = None
        self.flask_app = None
        self.flask_thread = None
        self.auth_alert = None
        self.midi_health = None

    def initialize(self):
        """Initialize all components."""
        print("Initializing Launchpad MK2 Controller...")

        # Initialize Spotify (initialize_spotify already validates the session)
        spotify_client = initialize_spotify()
        if spotify_client:
            self.spotify_manager.spotify = spotify_client
            self.spotify_manager.needs_reauth = False
            print("Spotify initialized successfully")

            # Initialize audio analyzer for Spotify-powered features
            audio_enabled = (config_manager.is_audio_features_enabled() and
                           config_manager.should_auto_start_analysis())
            self.audio_analyzer = create_audio_analyzer(self.spotify_manager, enabled=audio_enabled)

            if audio_enabled:
                print("🎵 Audio analyzer initialized and enabled")
            else:
                print("🎵 Audio analyzer initialized but disabled")
                print("   Use 'af enable' to enable Spotify audio features")
        else:
            # Keep early logs quiet — AuthAlertService prints a loud banner
            # at the end of startup and every 5s until the user runs 'auth'.
            self.spotify_manager.needs_reauth = True
            self.audio_analyzer = create_audio_analyzer(self.spotify_manager, enabled=False)

        # Load playlist mappings
        self.playlist_manager.load_mappings()
        print(f"Loaded {len(self.playlist_manager.mappings)} playlist mappings")

        self.user_action_manager.load()
        user_count = sum(len(b) for b in self.user_action_manager.banks.values())
        print(f"Loaded {user_count} user action mappings")

        # Initialize animation controller with audio analyzer
        self.animation_controller = AnimationController(
            audio_analyzer=self.audio_analyzer,
            spotify_manager=self.spotify_manager
        )
        self.animation_controller.initialize()
        if self.animation_controller.launchpad.is_connected():
            print("Animation controller initialized (Launchpad connected)")
        else:
            print("Animation controller initialized (Launchpad offline — waiting for MIDI)")

        # Set up MIDI handler
        self.midi_handler = MidiHandler(
            self.animation_controller,
            self.spotify_manager,
            self.playlist_manager,
            user_action_manager=self.user_action_manager,
            action_executor=self.action_executor,
        )

        # Set MIDI callback when ports are available (health monitor re-attaches later)
        if self.animation_controller.launchpad.midi_in:
            self.animation_controller.launchpad.midi_in.set_callback(
                self.midi_handler.on_midi_message
            )
            print("MIDI handler initialized")
        else:
            print("MIDI handler ready (callback will attach when Launchpad connects)")

        # Start status monitor only when auth is healthy
        if self.spotify_manager.spotify and not self.spotify_manager.needs_reauth:
            self._start_status_monitor()

        return True

    def _start_status_monitor(self):
        """Start (or restart) the Spotify status monitor."""
        if self.status_monitor:
            self.status_monitor.stop()
        self.status_monitor = StatusMonitor(
            self.spotify_manager,
            self.animation_controller,
            self.playlist_manager
        )
        self.status_monitor.start()
        print("Spotify status monitor started")

    def reauthenticate_spotify(self):
        """Clear tokens, open Spotify OAuth, and restart dependent services.

        Returns:
            bool: True if re-authentication succeeded
        """
        if self.status_monitor:
            self.status_monitor.stop()
            self.status_monitor = None

        if self.audio_analyzer:
            self.audio_analyzer.pause()

        if self.animation_controller:
            # Keep pad red until login completes; alert loop will manage it
            self.animation_controller.set_auth_lockout(True)

        success = self.spotify_manager.reauthenticate()

        if success:
            if self.animation_controller:
                self.animation_controller.set_auth_lockout(False)
            self._start_status_monitor()
            # Keep audio features off unless explicitly enabled (Spotify 403 for most apps)
            if self.audio_analyzer:
                self.audio_analyzer.pause()
                if (config_manager.is_audio_features_enabled() and
                        config_manager.should_auto_start_analysis()):
                    self.audio_analyzer.enable()
                    if (not self.audio_analyzer.analysis_thread or
                            not self.audio_analyzer.analysis_thread.is_alive()):
                        self.audio_analyzer.start_analysis()
                    self.audio_analyzer.resume()
            print("Spotify services restarted.")
        else:
            self.spotify_manager.needs_reauth = True
            if self.animation_controller:
                self.animation_controller.set_auth_lockout(True)
            print("Spotify still unavailable. Try 'auth' again when ready.")

        return success

    def start_api(self, host='0.0.0.0', port=5125):
        """Start the Flask API server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.flask_app = create_app(
            self.animation_controller,
            self.spotify_manager,
            self.playlist_manager,
            self.audio_analyzer,
            self.midi_handler,
            reauth_callback=self.reauthenticate_spotify,
            user_action_manager=self.user_action_manager,
            action_executor=self.action_executor,
        )
        self.flask_thread = threading.Thread(
            target=lambda: self.flask_app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            ),
            daemon=True
        )
        self.flask_thread.start()
        print(f"Flask API started on http://{host}:{port}")

    def _read_cli_line(self, timeout=3.0):
        """Read a CLI line with timeout so MIDI health can pump on the main thread.

        Returns:
            str|None: Command line without trailing newline, or None on timeout
        """
        if not sys.stdin or not sys.stdin.isatty():
            # Non-interactive (launchd / pipe): still pump MIDI, then block briefly
            if self.midi_health:
                self.midi_health.pump()
            time.sleep(timeout)
            return None

        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        line = sys.stdin.readline()
        if line == '':
            raise EOFError
        return line.lower().strip()

    def run_interactive(self):
        """Run the interactive command line interface."""
        # Show initial status
        show_quick_status(self.playlist_manager, self.animation_controller, self.spotify_manager)

        # Auth banner last so it isn't buried under startup / Flask logs
        if self.spotify_manager.needs_reauth:
            print_auth_warning()

        while True:
            try:
                # CoreMIDI hotplug only works reliably when open/scan runs here
                if self.midi_health:
                    self.midi_health.pump()

                cmd = self._read_cli_line(timeout=3.0)
                if cmd is None:
                    continue

                if cmd == 'h':
                    show_help()

                elif cmd == 'v':
                    self.playlist_manager.show_preview('table')

                elif cmd in ('auth', 'reauth'):
                    self.reauthenticate_spotify()

                elif cmd == 's':
                    if self.spotify_manager.ensure_ready():
                        show_spotify_devices(self.spotify_manager.spotify)
                    # ensure_ready already prints recovery hint

                elif cmd == 'p':
                    if self.spotify_manager.ensure_ready():
                        fetch_and_save_playlists(self.spotify_manager.spotify)

                elif cmd == 'l':
                    print_available_playlists()

                elif cmd == 'a':
                    print_available_animations(ANIMATIONS)
                    try:
                        choice = input("\nSelect animation number (or press Enter to cancel): ").strip()
                        if choice:
                            anim_num = int(choice) - 1
                            anim_list = list(ANIMATIONS.keys())
                            if 0 <= anim_num < len(anim_list):
                                animation_name = anim_list[anim_num]
                                if self.animation_controller.set_animation(animation_name):
                                    print(f"Started animation: {animation_name}")
                                else:
                                    print("Failed to start animation")
                            else:
                                print("Invalid animation number!")
                    except ValueError:
                        print("Invalid input! Please enter a number.")

                elif cmd == 'x':
                    self.animation_controller.stop_animation()
                    print("Animation stopped")

                elif cmd == 'g':
                    if self.spotify_manager.ensure_ready():
                        print("\nSelect filter type:")
                        print("1. Newest playlists")
                        print("2. Most popular playlists")
                        print("3. All playlists")
                        try:
                            choice = input("\nEnter choice (1-3): ").strip()
                            filter_type = {
                                '1': 'newest',
                                '2': 'popular',
                                '3': 'all'
                            }.get(choice, 'newest')
                            generate_playlist_mappings(
                                self.spotify_manager.spotify,
                                ANIMATIONS,
                                filter_type
                            )
                            # Reload mappings after generation
                            self.playlist_manager.load_mappings()
                        except ValueError:
                            print("Invalid input! Using 'newest' filter.")
                            generate_playlist_mappings(
                                self.spotify_manager.spotify,
                                ANIMATIONS,
                                'newest'
                            )
                            self.playlist_manager.load_mappings()

                elif cmd == 'r':
                    print("\nRandomizing animations for all playlists...")
                    randomize_animations(ANIMATIONS)
                    # Reload mappings after randomization
                    self.playlist_manager.load_mappings()

                elif cmd == 'af':
                    self._handle_audio_features_command()

                elif cmd == 'q':
                    break

                else:
                    print("Unknown command. Type 'h' for help.")

            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _handle_audio_features_command(self):
        """Handle audio features sub-commands."""
        if not self.audio_analyzer:
            print("🚫 Audio features not available (Spotify not initialized)")
            return

        print("\n🎵 Audio Features Control")
        print("=" * 40)
        print("1. Enable audio features")
        print("2. Disable audio features")
        print("3. Pause analysis")
        print("4. Resume analysis")
        print("5. Show status")
        print("6. Show configuration")
        print("7. Toggle auto-start")
        print("8. Set update interval")
        print("9. Reset to defaults")
        print("0. Back to main menu")

        try:
            choice = input("\nSelect option (0-9): ").strip()

            if choice == '1':
                self.audio_analyzer.enable()
                if not self.audio_analyzer.analysis_thread or not self.audio_analyzer.analysis_thread.is_alive():
                    self.audio_analyzer.start_analysis()
                config_manager.set_audio_features_enabled(True)

            elif choice == '2':
                self.audio_analyzer.disable()
                config_manager.set_audio_features_enabled(False)

            elif choice == '3':
                self.audio_analyzer.pause()

            elif choice == '4':
                self.audio_analyzer.resume()

            elif choice == '5':
                self._show_audio_features_status()

            elif choice == '6':
                print(config_manager.get_config_summary())

            elif choice == '7':
                current = config_manager.should_auto_start_analysis()
                config_manager.audio_features_config["auto_start"] = not current
                config_manager.save_audio_features_config()
                status = "enabled" if not current else "disabled"
                print(f"🔄 Auto-start {status}")

            elif choice == '8':
                current = config_manager.get_update_interval()
                print(f"Current update interval: {current}s")
                try:
                    new_interval = float(input("Enter new interval (0.5-10.0 seconds): "))
                    config_manager.set_update_interval(new_interval)
                except ValueError:
                    print("Invalid input! Please enter a number.")

            elif choice == '9':
                confirm = input("Reset all audio features settings to defaults? (y/N): ").lower()
                if confirm == 'y':
                    config_manager.reset_to_defaults()

            elif choice == '0':
                return

            else:
                print("Invalid choice!")

        except Exception as e:
            print(f"Error: {e}")

    def _show_audio_features_status(self):
        """Show detailed audio features status."""
        if not self.audio_analyzer:
            print("🚫 Audio analyzer not available")
            return

        print("\n🎵 Audio Features Status")
        print("=" * 40)
        print(f"Status: {self.audio_analyzer.get_status()}")
        print(f"Enabled: {self.audio_analyzer.enabled}")
        print(f"Paused: {self.audio_analyzer._paused}")
        print(f"Thread alive: {self.audio_analyzer.analysis_thread.is_alive() if self.audio_analyzer.analysis_thread else False}")

        if self.audio_analyzer.current_features:
            features = self.audio_analyzer.current_features
            print(f"\n📊 Current Track Features:")
            print(f"  Energy: {features.get('energy', 0):.2f}")
            print(f"  Tempo: {features.get('tempo', 0):.1f} BPM")
            print(f"  Danceability: {features.get('danceability', 0):.2f}")
            print(f"  Valence: {features.get('valence', 0):.2f}")
            print(f"  Loudness: {features.get('loudness', 0):.1f} dB")

            # Show suggested animation
            suggested = self.audio_analyzer.suggest_animation()
            print(f"  Suggested animation: {suggested}")
        else:
            print("\n📊 No current track data")

    def shutdown(self):
        """Shutdown all components."""
        print("Shutting down...")

        if self.midi_health:
            self.midi_health.stop()

        if self.auth_alert:
            self.auth_alert.stop()

        if self.status_monitor:
            self.status_monitor.stop()

        if self.audio_analyzer:
            self.audio_analyzer.stop_analysis()

        if self.animation_controller:
            self.animation_controller.shutdown()

        print("Shutdown complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Launchpad MK2 Spotify Controller')
    parser.add_argument('--homebridge', action='store_true', help='Start Homebridge server')
    parser.add_argument('--api-host', default='0.0.0.0', help='API host (default: 0.0.0.0)')
    parser.add_argument('--api-port', type=int, default=5125, help='API port (default: 5125)')
    args = parser.parse_args()

    configure_spotipy_logging()

    # Spotify requires 127.0.0.1 (not localhost). Flask serves /callback with
    # our welcome page — register this exact URI in the Developer Dashboard.
    set_oauth_redirect_uri(f'http://127.0.0.1:{args.api_port}/callback')

    controller = LaunchpadController()

    try:
        if not controller.initialize():
            print("Failed to initialize controller")
            return 1

        # Start API server (also hosts Spotify OAuth /callback)
        controller.start_api(args.api_host, args.api_port)

        # Repeat auth warnings + keep Launchpad red while token is invalid
        controller.auth_alert = AuthAlertService(
            controller.spotify_manager,
            controller.animation_controller,
            interval=5.0,
        )
        controller.auth_alert.start()

        # MIDI health: pump() runs on the main CLI loop (CoreMIDI + hotplug)
        controller.midi_health = MidiHealthMonitor(
            controller.animation_controller,
            midi_handler=controller.midi_handler,
            interval=3.0,
        )
        controller.midi_health.start()

        # TODO: Implement Homebridge server if requested
        if args.homebridge:
            print("Homebridge support not yet implemented in refactored version")

        # Run interactive CLI
        controller.run_interactive()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    finally:
        controller.shutdown()

    return 0


if __name__ == '__main__':
    exit(main())
