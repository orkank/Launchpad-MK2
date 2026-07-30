"""Launchpad MK2 hardware interface."""

import gc
import sys
import time

import rtmidi

# Pads that keep a fixed color; animations / clear / fill cannot override them
# unless set_color(..., force=True) is used (e.g. auth lockout).
_locked_pads = {}  # {(x, y): (r, g, b)}

LAUNCHPAD_PORT_HINTS = ('launchpad', 'focusrite', 'novation')


class LaunchpadManager:
    """Manages Launchpad MK2 hardware communication."""

    def __init__(self):
        self.midi_out = None
        self.midi_in = None
        self.port_name = None
        self._last_connected = None  # None unknown, True/False after checks

    def initialize(self):
        """Try to open Launchpad MIDI ports.

        Missing hardware is non-fatal — the app can start without a pad and
        MidiHealthMonitor will reconnect when the device appears.
        """
        self.midi_out, self.midi_in, self.port_name = initialize_launchpad(fatal=False)
        if self.midi_out:
            self._enter_programmer_mode()
            self._last_connected = True
            return True
        self._last_connected = False
        print(
            "Launchpad not found at startup — continuing without MIDI. "
            "Connect the device and it will be picked up automatically."
        )
        return False

    def _enter_programmer_mode(self):
        if not self.midi_out:
            return
        try:
            self.midi_out.send_message([240, 0, 32, 41, 2, 24, 14, 1, 247])
        except Exception:
            pass

    def close(self):
        """Close MIDI connections."""
        unlock_all_pads()
        self._close_ports_quietly()
        self.port_name = None
        self._last_connected = False

    def _close_ports_quietly(self):
        if self.midi_out:
            try:
                if self.midi_out.is_port_open():
                    try:
                        clear_all(self.midi_out, force=True)
                    except Exception:
                        pass
            except Exception:
                pass
            _discard_midi_client(self.midi_out)
            self.midi_out = None
        if self.midi_in:
            _discard_midi_client(self.midi_in)
            self.midi_in = None

    def is_connected(self):
        """Return cached connection flag (updated by check_connection)."""
        if self._last_connected is None:
            return bool(self.midi_out and self.midi_in)
        return bool(self._last_connected)

    def check_connection(self):
        """Probe whether the Launchpad MIDI ports are still reachable.

        Avoids sending the programmer-mode SysEx (that resets the LED
        buffer and makes mode locks look like they were overridden).

        Returns:
            bool: True if connected and responsive
        """
        if not self.midi_out or not self.midi_in:
            self._last_connected = False
            return False

        try:
            if hasattr(self.midi_out, 'is_port_open') and not self.midi_out.is_port_open():
                self._last_connected = False
                return False
            if hasattr(self.midi_in, 'is_port_open') and not self.midi_in.is_port_open():
                self._last_connected = False
                return False

            ports = list(self.midi_out.get_ports() or [])
            if self.port_name and self.port_name not in ports:
                self._last_connected = False
                return False
            if not any(_looks_like_launchpad(p) for p in ports):
                self._last_connected = False
                return False

            # Gentle write probe: re-assert a locked pad, or a no-op black on (8,8)
            # — never send layout/programmer SysEx here (it clears the pad).
            if _locked_pads:
                (lx, ly), (lr, lg, lb) = next(iter(_locked_pads.items()))
                set_color(self.midi_out, lx, ly, lr, lg, lb, force=True)
            else:
                set_color(self.midi_out, 8, 8, 0, 0, 0, force=True)
            self._last_connected = True
            return True
        except Exception:
            self._last_connected = False
            return False

    def try_reconnect(self, verbose=False):
        """Attempt to reopen Launchpad ports if disconnected.

        Always destroys previous MIDI clients first so CoreMIDI can see
        hot-plugged devices (port lists are tied to the client lifetime).

        Returns:
            bool: True if connected after the attempt
        """
        if self.midi_out and self.midi_in and self.check_connection():
            return True

        # Drop stale clients so the next MidiOut()/MidiIn() sees current ports
        self._close_ports_quietly()
        gc.collect()

        # Give CoreMIDI a moment after USB plug events
        time.sleep(0.4)

        midi_out, midi_in, port_name = open_launchpad_ports(verbose=verbose)
        if not midi_out or not midi_in:
            self._last_connected = False
            return False

        self.midi_out = midi_out
        self.midi_in = midi_in
        self.port_name = port_name
        self._enter_programmer_mode()
        self._last_connected = True
        return True

    def get_status(self):
        """Status dict for API / dashboard."""
        # Prefer cached flag — avoid probing from HTTP threads
        connected = self.is_connected()
        return {
            'connected': connected,
            'port_name': self.port_name if connected else None,
        }


def _looks_like_launchpad(port_name):
    port_lower = (port_name or '').lower()
    return any(hint in port_lower for hint in LAUNCHPAD_PORT_HINTS)


def _port_priority(port_name):
    """Lower score = better match (prefer real Launchpad over Focusrite, etc.)."""
    name = (port_name or '').lower()
    if 'launchpad' in name:
        return 0
    if 'novation' in name:
        return 1
    if 'focusrite' in name:
        return 2
    return 99


def _find_matching_in_port(out_name, in_ports):
    """Find an input port index that pairs with the given output port name."""
    if not in_ports:
        return None

    # 1) Exact name match (classic Launchpad MK2)
    for j, in_name in enumerate(in_ports):
        if in_name == out_name:
            return j

    out_l = out_name.lower()
    # 2) Case-insensitive equality
    for j, in_name in enumerate(in_ports):
        if in_name.lower() == out_l:
            return j

    # 3) Both look like Launchpad / Novation — pick best related input
    candidates = [
        (j, in_name) for j, in_name in enumerate(in_ports)
        if _looks_like_launchpad(in_name)
    ]
    if not candidates:
        return None

    # Prefer input that shares a significant token with the output name
    out_tokens = {t for t in out_l.replace('_', ' ').split() if len(t) > 2}
    best = None
    best_score = -1
    for j, in_name in candidates:
        in_l = in_name.lower()
        score = len(out_tokens.intersection(in_l.replace('_', ' ').split()))
        if 'launchpad' in in_l:
            score += 5
        if score > best_score:
            best_score = score
            best = j

    # If only one Launchpad-like input exists, use it
    if best is None and len(candidates) == 1:
        return candidates[0][0]
    if best is not None and (best_score > 0 or len(candidates) == 1):
        return best
    if len(candidates) == 1:
        return candidates[0][0]
    return best


def _new_midi_clients():
    """Create MidiOut/MidiIn, preferring CoreMIDI on macOS."""
    try:
        if rtmidi.API_MACOSX_CORE in (rtmidi.get_compiled_api() or []):
            return (
                rtmidi.MidiOut(rtmidi.API_MACOSX_CORE),
                rtmidi.MidiIn(rtmidi.API_MACOSX_CORE),
            )
    except Exception:
        pass
    return rtmidi.MidiOut(), rtmidi.MidiIn()


def _discard_midi_client(client):
    """Close and destroy an rtmidi client (required for CoreMIDI hotplug).

    python-rtmidi keeps the underlying C++ client until the Python object is
    truly deallocated; without delete()/gc.collect(), get_ports() can stay
    empty forever after the first failed scan.
    """
    if client is None:
        return
    try:
        if hasattr(client, 'is_port_open') and client.is_port_open():
            client.close_port()
    except Exception:
        pass
    try:
        if hasattr(client, 'delete'):
            client.delete()
    except Exception:
        pass
    try:
        del client
    except Exception:
        pass


def open_launchpad_ports(verbose=True):
    """Find and open Launchpad MIDI in/out ports.

    Creates a fresh CoreMIDI client each call (required to see hot-plugged
    devices). Failed attempts always destroy the clients so we do not leak
    MIDIClient handles — leaking those eventually blocks further opens.

    Returns:
        tuple: (midi_out, midi_in, port_name) or (None, None, None)
    """
    midi_out = None
    midi_in = None
    try:
        # Ensure previous CoreMIDI clients are gone before creating new ones
        gc.collect()
        midi_out, midi_in = _new_midi_clients()
        out_ports = list(midi_out.get_ports() or [])
        in_ports = list(midi_in.get_ports() or [])

        # Hot-plug settle: empty list right after USB attach is common
        if not out_ports:
            _discard_midi_client(midi_in)
            _discard_midi_client(midi_out)
            midi_out = None
            midi_in = None
            gc.collect()
            time.sleep(0.6)
            midi_out, midi_in = _new_midi_clients()
            out_ports = list(midi_out.get_ports() or [])
            in_ports = list(midi_in.get_ports() or [])

        if verbose:
            print("Available MIDI ports:")
            print("  OUT:")
            for i, port in enumerate(out_ports):
                print(f"    [{i}] {port}")
            print("  IN:")
            for i, port in enumerate(in_ports):
                print(f"    [{i}] {port}")

        if not out_ports:
            if verbose:
                print("No MIDI output ports found!")
            _discard_midi_client(midi_in)
            _discard_midi_client(midi_out)
            return None, None, None

        candidates = [
            (i, port) for i, port in enumerate(out_ports)
            if _looks_like_launchpad(port)
        ]
        candidates.sort(key=lambda item: (_port_priority(item[1]), item[0]))

        if not candidates:
            if verbose:
                print("No Launchpad-like ports in MIDI list")
            _discard_midi_client(midi_in)
            _discard_midi_client(midi_out)
            return None, None, None

        for i, port in candidates:
            if verbose:
                print(f"Trying Launchpad output [{i}]: {port}")
            in_index = _find_matching_in_port(port, in_ports)
            if in_index is None:
                if verbose:
                    print(f"  No matching MIDI input for '{port}'")
                continue
            try:
                # Fresh clients per successful attempt path — reopen cleanly
                if midi_out.is_port_open():
                    midi_out.close_port()
                if midi_in.is_port_open():
                    midi_in.close_port()

                midi_out.open_port(i)
                midi_in.open_port(in_index)
                if verbose:
                    print(
                        f"Successfully connected OUT[{i}]='{port}' "
                        f"IN[{in_index}]='{in_ports[in_index]}'"
                    )
                return midi_out, midi_in, port
            except (rtmidi.SystemError, rtmidi.InvalidPortError, OSError) as e:
                if verbose:
                    print(f"  Failed to open ports: {e}")
                try:
                    if midi_out.is_port_open():
                        midi_out.close_port()
                except Exception:
                    pass
                try:
                    if midi_in.is_port_open():
                        midi_in.close_port()
                except Exception:
                    pass
                continue

        if verbose:
            print("No Launchpad MIDI in/out pair could be opened")
        _discard_midi_client(midi_in)
        _discard_midi_client(midi_out)
        return None, None, None

    except Exception as e:
        print(f"Error opening MIDI: {e}")
        _discard_midi_client(midi_in)
        _discard_midi_client(midi_out)
        return None, None, None


def initialize_launchpad(fatal=True):
    """Initialize Launchpad MK2 MIDI connection.

    Args:
        fatal: If True, exit the process when no device is found (startup)

    Returns:
        tuple: (midi_out, midi_in, port_name)
    """
    midi_out, midi_in, port_name = open_launchpad_ports(verbose=True)
    if midi_out and midi_in:
        return midi_out, midi_in, port_name

    if fatal:
        print("\nTroubleshooting steps:")
        print("1. Open 'Audio MIDI Setup' application")
        print("2. Go to Window > Show MIDI Studio")
        print("3. Check if Launchpad MK2 is visible and enabled")
        print("4. Try unplugging and replugging the Launchpad")
        print("\nPlease ensure:")
        print("1. Launchpad is properly connected via USB")
        print("2. Device is configured in Audio MIDI Setup")
        print("3. You have necessary permissions")
        sys.exit(1)

    return None, None, None


def lock_pad(midi_out, x, y, r, g, b):
    """Lock a pad to a fixed color that animations cannot override.

    Args:
        midi_out: MIDI output device (optional; applies color immediately if given)
        x: X coordinate (0-8)
        y: Y coordinate (0-8)
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)
    """
    _locked_pads[(x, y)] = (r, g, b)
    if midi_out:
        set_color(midi_out, x, y, r, g, b, force=True)


def unlock_pad(midi_out, x, y, clear=True):
    """Unlock a pad so animations can control it again.

    Args:
        midi_out: MIDI output device (optional)
        x: X coordinate (0-8)
        y: Y coordinate (0-8)
        clear: If True and midi_out is set, turn the pad off after unlock
    """
    _locked_pads.pop((x, y), None)
    if clear and midi_out:
        set_color(midi_out, x, y, 0, 0, 0, force=True)


def unlock_all_pads():
    """Remove all pad color locks."""
    _locked_pads.clear()


def reassert_locked_pads(midi_out):
    """Force-write every locked pad color (call after bulk LED updates)."""
    if not midi_out or not _locked_pads:
        return
    for (x, y), (r, g, b) in list(_locked_pads.items()):
        set_color(midi_out, x, y, r, g, b, force=True)


def set_color(midi_out, x, y, r, g, b, force=False):
    """Set color of a specific LED on the Launchpad.

    Args:
        midi_out: MIDI output device
        x: X coordinate (0-8)
        y: Y coordinate (0-8)
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)
        force: If True, ignore pad locks (used for auth lockout / unlock clear)
    """
    if not midi_out:
        return

    # Locked pads always keep their color unless force=True (auth / unlock)
    if not force and (x, y) in _locked_pads:
        r, g, b = _locked_pads[(x, y)]

    r = min(63, int(r * 63 / 255))
    g = min(63, int(g * 63 / 255))
    b = min(63, int(b * 63 / 255))

    if x == 8 and y == 8:
        note = 99
    elif y == 8:
        note = 104 + x
    elif x == 8:
        note = 19 + (y * 10)
    else:
        note = 11 + x + (y * 10)

    sysex_msg = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x18, 0x0B, note, r, g, b, 0xF7]
    try:
        midi_out.send_message(sysex_msg)
    except Exception:
        # Device may have been unplugged mid-frame
        pass


def clear_all(midi_out, force=False):
    """Clear all LEDs on the Launchpad.

    Args:
        midi_out: MIDI output device
        force: If True, also clear locked pads
    """
    fill_all(midi_out, 0, 0, 0, force=force)


def fill_all(midi_out, r, g, b, force=False):
    """Set every Launchpad LED to the same color.

    Args:
        midi_out: MIDI output device
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)
        force: If True, ignore pad locks
    """
    if not midi_out:
        return
    for y in range(9):
        for x in range(9):
            set_color(midi_out, x, y, r, g, b, force=force)
    if not force:
        reassert_locked_pads(midi_out)
