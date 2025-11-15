"""Audio input interface for microphone-based animations."""

import pyaudio


def initialize_audio():
    """Initialize audio input for microphone-based visualizations.

    Returns:
        tuple: (pyaudio_instance, stream) or (None, None) on failure
    """
    try:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=2048
        )
        return p, stream
    except Exception as e:
        print(f"Error initializing audio: {e}")
        return None, None
