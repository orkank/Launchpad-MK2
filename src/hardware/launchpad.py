"""Launchpad MK2 hardware interface."""

import rtmidi
import sys


class LaunchpadManager:
    """Manages Launchpad MK2 hardware communication."""

    def __init__(self):
        self.midi_out = None
        self.midi_in = None

    def initialize(self):
        """Initialize MIDI connection to Launchpad."""
        self.midi_out, self.midi_in = initialize_launchpad()
        if self.midi_out:
            # Initialize MIDI device with programmer mode
            self.midi_out.send_message([240, 0, 32, 41, 2, 24, 14, 1, 247])
        return self.midi_out is not None

    def close(self):
        """Close MIDI connections."""
        if self.midi_out:
            clear_all(self.midi_out)
            self.midi_out.close_port()
        if self.midi_in:
            self.midi_in.close_port()


def initialize_launchpad():
    """Initialize Launchpad MK2 MIDI connection.

    Returns:
        tuple: (midi_out, midi_in) objects or (None, None) on failure
    """
    try:
        midi_out = rtmidi.MidiOut()
        midi_in = rtmidi.MidiIn()
        out_ports = midi_out.get_ports()
        in_ports = midi_in.get_ports()

        print("Available MIDI ports:")
        if not out_ports:
            print("No MIDI ports found!")
            print("\nTroubleshooting steps:")
            print("1. Open 'Audio MIDI Setup' application")
            print("2. Go to Window > Show MIDI Studio")
            print("3. Check if Launchpad MK2 is visible and enabled")
            print("4. Try unplugging and replugging the Launchpad")
            sys.exit(1)

        for i, port in enumerate(out_ports):
            port_lower = port.lower()
            if any(name in port_lower for name in ['launchpad', 'focusrite', 'novation']):
                print(f"Found potential Launchpad output at port {i}: {port}")
                try:
                    midi_out.open_port(i)
                    for j, in_port in enumerate(in_ports):
                        if port == in_port:
                            midi_in.open_port(j)
                            print("Successfully connected to input and output ports!")
                            return midi_out, midi_in
                except rtmidi.SystemError as e:
                    print(f"Failed to open port {i}: {e}")
                    continue

        print("\nNo Launchpad found in available ports!")
        print("If your Launchpad is connected, please check Audio MIDI Setup")
        sys.exit(1)

    except Exception as e:
        print(f"Error initializing MIDI: {str(e)}")
        print("\nPlease ensure:")
        print("1. Launchpad is properly connected via USB")
        print("2. Device is configured in Audio MIDI Setup")
        print("3. You have necessary permissions")
        sys.exit(1)


def set_color(midi_out, x, y, r, g, b):
    """Set color of a specific LED on the Launchpad.

    Args:
        midi_out: MIDI output device
        x: X coordinate (0-8)
        y: Y coordinate (0-8)
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)
    """
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
    midi_out.send_message(sysex_msg)


def clear_all(midi_out):
    """Clear all LEDs on the Launchpad.

    Args:
        midi_out: MIDI output device
    """
    for y in range(9):
        for x in range(9):
            set_color(midi_out, x, y, 0, 0, 0)
