"""Launchpad MIDI health checks — must run MIDI open/scan on the main thread.

On macOS, CoreMIDI clients created from a background thread often see an empty
port list even when the USB device is present. All rtmidi open/enumerate work
is done via MidiHealthMonitor.pump() on the main thread.
"""

import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align


def print_midi_disconnect_warning(port_name=None, detail=None):
    """Print a high-visibility Launchpad disconnect warning."""
    console = Console(stderr=False)
    body = Text()
    body.append("LAUNCHPAD MIDI DISCONNECTED\n\n", style="bold white on red")
    body.append("The Launchpad MIDI device is no longer reachable.\n", style="bold red")
    if port_name:
        body.append("Last port: ", style="white")
        body.append(f"{port_name}\n", style="bold yellow")
    if detail:
        body.append(f"\n{detail}\n", style="dim")
    body.append("\nCheck USB connection and Audio MIDI Setup.\n", style="white")
    body.append("Retrying on the main thread…", style="dim")

    console.print()
    console.print(
        Panel(
            Align.center(body),
            title="[bold white on red] MIDI [/]",
            border_style="bold red",
            padding=(1, 2),
        )
    )
    console.print()


def print_midi_reconnected(port_name=None):
    """Print recovery message when Launchpad comes back."""
    console = Console(stderr=False)
    detail = f" ({port_name})" if port_name else ""
    console.print(
        Panel(
            Align.center(
                Text(f"Launchpad MIDI reconnected{detail}", style="bold green")
            ),
            title="[bold white on green] MIDI [/]",
            border_style="bold green",
            padding=(0, 2),
        )
    )


class MidiHealthMonitor:
    """Main-thread MIDI health checker (call pump() regularly)."""

    def __init__(self, animation_controller, midi_handler=None, interval=3.0):
        self.animation_controller = animation_controller
        self.midi_handler = midi_handler
        self.interval = max(2.0, float(interval))
        self._was_disconnected = False
        self._last_port_name = None
        self._fail_streak = 0
        self._last_pump = 0.0
        self._started = False

    def start(self):
        """Mark monitor active; work happens in pump() on the main thread."""
        self._started = True
        launchpad = self._launchpad()
        if launchpad and not launchpad.is_connected():
            self._was_disconnected = True
        self._last_pump = 0.0  # force an immediate check on first pump()

    def stop(self):
        """Stop accepting pump work."""
        self._started = False

    def _launchpad(self):
        if not self.animation_controller:
            return None
        return getattr(self.animation_controller, 'launchpad', None)

    def _reattach_midi_callback(self):
        """Re-bind MIDI input callback after a successful reconnect."""
        launchpad = self._launchpad()
        if not launchpad or not launchpad.midi_in or not self.midi_handler:
            return
        try:
            launchpad.midi_in.cancel_callback()
        except Exception:
            pass
        try:
            launchpad.midi_in.set_callback(self.midi_handler.on_midi_message)
            print("MIDI input callback re-attached after reconnect")
        except Exception as e:
            print(f"Failed to re-attach MIDI callback: {e}")

        # Restore Session / User mode indicator locks on the fresh connection
        try:
            if self.animation_controller and hasattr(self.animation_controller, '_apply_mode_leds'):
                self.animation_controller._apply_mode_leds()
        except Exception as e:
            print(f"Failed to restore mode LED locks: {e}")

    def pump(self, force=False):
        """Run one health check / reconnect attempt on the current (main) thread.

        Args:
            force: Ignore the interval throttle
        """
        if not self._started:
            return

        now = time.monotonic()
        if not force and (now - self._last_pump) < self.interval:
            return
        self._last_pump = now

        launchpad = self._launchpad()
        if not launchpad:
            return

        try:
            has_handles = bool(launchpad.midi_out and launchpad.midi_in)
            connected = has_handles and launchpad.check_connection()

            if connected:
                if self._was_disconnected:
                    print_midi_reconnected(launchpad.port_name)
                    self._reattach_midi_callback()
                self._was_disconnected = False
                self._fail_streak = 0
                if launchpad.port_name:
                    self._last_port_name = launchpad.port_name
                return

            if launchpad.port_name:
                self._last_port_name = launchpad.port_name

            self._fail_streak += 1
            verbose = self._fail_streak <= 3 or self._fail_streak % 5 == 0
            if verbose:
                print(f"MIDI reconnect attempt #{self._fail_streak} (main thread)…")

            reconnected = launchpad.try_reconnect(verbose=verbose)
            if reconnected:
                self._reattach_midi_callback()
                print_midi_reconnected(launchpad.port_name)
                self._was_disconnected = False
                self._fail_streak = 0
                return

            self._was_disconnected = True
            if self._fail_streak == 1 or self._fail_streak % 5 == 0:
                print_midi_disconnect_warning(
                    self._last_port_name,
                    detail=f"Reconnect attempts: {self._fail_streak}",
                )
        except Exception as e:
            print(f"MIDI health check error: {e}")
            self._was_disconnected = True
