"""Loud, repeating Spotify auth-required alerts (console + Launchpad)."""

import threading
import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from ..services.spotify_manager import get_oauth_redirect_uri


def print_auth_warning():
    """Print a high-visibility Spotify auth warning to the terminal."""
    console = Console(stderr=False)
    body = Text()
    body.append("SPOTIFY AUTH REQUIRED\n\n", style="bold white on red")
    body.append("Token missing or revoked — Launchpad Spotify control is locked.\n", style="bold red")
    body.append("Type ", style="white")
    body.append("auth", style="bold yellow")
    body.append(" here, or click ", style="white")
    body.append("Re-auth", style="bold yellow")
    body.append(" at ", style="white")
    body.append("http://localhost:5125", style="bold cyan")
    body.append("\n\nSpotify Dashboard Redirect URI (unchanged for all users):\n", style="white")
    body.append(get_oauth_redirect_uri(), style="bold bright_white")

    console.print()
    console.print(
        Panel(
            Align.center(body),
            title="[bold white on red] AUTH [/]",
            border_style="bold red",
            padding=(1, 2),
        )
    )
    console.print()


class AuthAlertService:
    """Repeats console warnings and keeps Launchpad red while auth is broken."""

    def __init__(self, spotify_manager, animation_controller, interval=5.0):
        self.spotify_manager = spotify_manager
        self.animation_controller = animation_controller
        self.interval = interval
        self.should_run = False
        self._thread = None
        self._was_alerting = False

    def start(self):
        """Start the background alert loop."""
        if self._thread and self._thread.is_alive():
            return
        self.should_run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background alert loop and clear lockout LEDs if active."""
        self.should_run = False
        if self._thread:
            try:
                self._thread.join(timeout=0.5)
            except Exception:
                pass
            self._thread = None
        if self._was_alerting and self.animation_controller:
            try:
                self.animation_controller.set_auth_lockout(False)
            except Exception:
                pass
            self._was_alerting = False

    def _needs_alert(self):
        sm = self.spotify_manager
        if not sm:
            return False
        return bool(sm.needs_reauth)

    def _loop(self):
        # Let startup / Flask banners finish printing first
        time.sleep(1.0)

        while self.should_run:
            if self._needs_alert():
                if self.animation_controller:
                    self.animation_controller.set_auth_lockout(True)
                print_auth_warning()
                self._was_alerting = True
            else:
                if self._was_alerting and self.animation_controller:
                    self.animation_controller.set_auth_lockout(False)
                    self._was_alerting = False
            time.sleep(self.interval)
