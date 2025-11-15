"""Spotify audio analysis for dynamic animation control."""

import time
import threading
from typing import Dict, Optional, Tuple


class AudioAnalyzer:
    """Analyzes Spotify audio features for dynamic animation control."""

    def __init__(self, spotify_manager, enabled=True):
        self.spotify_manager = spotify_manager
        self.current_features = None
        self.current_analysis = None
        self.last_track_id = None
        self.analysis_thread = None
        self.should_run = True
        self.enabled = enabled
        self._paused = False

    def start_analysis(self):
        """Start continuous audio analysis."""
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()

    def stop_analysis(self):
        """Stop audio analysis."""
        self.should_run = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=1)

    def _analysis_loop(self):
        """Continuous analysis loop."""
        while self.should_run:
            try:
                if self.enabled and not self._paused:
                    self._update_analysis()
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Audio analysis error: {e}")
                time.sleep(5)

    def _update_analysis(self):
        """Update audio features and analysis for current track."""
        if not self.spotify_manager or not self.spotify_manager.spotify:
            return

        try:
            current = self.spotify_manager.spotify.current_playback()
            if not current or not current['item']:
                return

            track_id = current['item']['id']

            # Only fetch new data if track changed
            if track_id != self.last_track_id:
                self.last_track_id = track_id

                # Get audio features
                features = self.spotify_manager.spotify.audio_features([track_id])[0]
                if features:
                    self.current_features = features

                # Get audio analysis (detailed)
                try:
                    analysis = self.spotify_manager.spotify.audio_analysis(track_id)
                    self.current_analysis = analysis
                except Exception as e:
                    print(f"Could not get audio analysis: {e}")

        except Exception as e:
            print(f"Error updating audio analysis: {e}")

    def get_current_features(self) -> Optional[Dict]:
        """Get current track's audio features."""
        return self.current_features

    def get_current_analysis(self) -> Optional[Dict]:
        """Get current track's detailed audio analysis."""
        return self.current_analysis

    def get_energy_level(self) -> float:
        """Get energy level (0.0-1.0)."""
        if not self.current_features:
            return 0.5
        return self.current_features.get('energy', 0.5)

    def get_tempo(self) -> float:
        """Get tempo in BPM."""
        if not self.current_features:
            return 120.0
        return self.current_features.get('tempo', 120.0)

    def get_danceability(self) -> float:
        """Get danceability (0.0-1.0)."""
        if not self.current_features:
            return 0.5
        return self.current_features.get('danceability', 0.5)

    def get_valence(self) -> float:
        """Get valence/mood (0.0-1.0)."""
        if not self.current_features:
            return 0.5
        return self.current_features.get('valence', 0.5)

    def get_loudness(self) -> float:
        """Get loudness in dB (typically -60 to 0)."""
        if not self.current_features:
            return -30.0
        return self.current_features.get('loudness', -30.0)

    def get_acousticness(self) -> float:
        """Get acousticness (0.0-1.0)."""
        if not self.current_features:
            return 0.5
        return self.current_features.get('acousticness', 0.5)

    def get_instrumentalness(self) -> float:
        """Get instrumentalness (0.0-1.0)."""
        if not self.current_features:
            return 0.5
        return self.current_features.get('instrumentalness', 0.5)

    def suggest_animation(self) -> str:
        """Suggest animation based on audio features."""
        if not self.current_features:
            return 'rainbow'

        energy = self.get_energy_level()
        tempo = self.get_tempo()
        danceability = self.get_danceability()
        valence = self.get_valence()
        acousticness = self.get_acousticness()
        instrumentalness = self.get_instrumentalness()

        # High energy, fast tempo
        if energy > 0.8 and tempo > 140:
            if danceability > 0.7:
                return 'party'
            else:
                return 'rock'

        # Electronic characteristics
        if acousticness < 0.3 and instrumentalness > 0.5:
            return 'electronic'

        # Calm, acoustic
        if energy < 0.4 and acousticness > 0.6:
            if valence < 0.4:
                return 'meditation'
            else:
                return 'ambient'

        # Chill, lo-fi vibes
        if energy < 0.6 and valence > 0.3 and valence < 0.7:
            return 'lofi'

        # Classical characteristics
        if acousticness > 0.7 and energy < 0.5:
            return 'classical'

        # Jazz characteristics
        if acousticness > 0.4 and instrumentalness > 0.3 and energy > 0.3 and energy < 0.7:
            return 'jazz'

        # Synthwave vibes
        if tempo > 100 and tempo < 140 and energy > 0.5 and acousticness < 0.4:
            return 'synthwave'

        # Default based on energy
        if energy > 0.7:
            return 'fireworks'
        elif energy > 0.4:
            return 'pulse'
        else:
            return 'ambient'

    def get_animation_parameters(self) -> Dict:
        """Get animation parameters based on audio features."""
        if not self.current_features:
            return {
                'speed': 1.0,
                'intensity': 0.5,
                'color_shift': 0.0,
                'pulse_rate': 1.0
            }

        energy = self.get_energy_level()
        tempo = self.get_tempo()
        valence = self.get_valence()
        danceability = self.get_danceability()

        # Calculate animation parameters
        speed = max(0.3, min(3.0, (tempo / 120.0) * energy))
        intensity = energy
        color_shift = valence  # Happy songs = warmer colors
        pulse_rate = max(0.5, min(2.0, tempo / 120.0))

        return {
            'speed': speed,
            'intensity': intensity,
            'color_shift': color_shift,
            'pulse_rate': pulse_rate,
            'danceability': danceability
        }

    def get_current_segments(self, progress_ms: int) -> Tuple[Optional[Dict], list]:
        """Get current and upcoming audio segments."""
        if not self.current_analysis or not progress_ms:
            return None, []

        progress_sec = progress_ms / 1000.0
        segments = self.current_analysis.get('segments', [])

        current_segment = None
        upcoming_segments = []

        for i, segment in enumerate(segments):
            start = segment['start']
            duration = segment['duration']
            end = start + duration

            if start <= progress_sec <= end:
                current_segment = segment
                # Get next few segments for prediction
                upcoming_segments = segments[i+1:i+4]
                break

        return current_segment, upcoming_segments

    def get_spectrum_data(self, progress_ms: int) -> Optional[Dict]:
        """Get spectrum data for current position."""
        current_segment, upcoming = self.get_current_segments(progress_ms)

        if not current_segment:
            return None

        # Extract useful data for visualization
        return {
            'loudness_max': current_segment.get('loudness_max', -30),
            'loudness_start': current_segment.get('loudness_start', -30),
            'pitches': current_segment.get('pitches', [0] * 12),  # 12-tone chroma
            'timbre': current_segment.get('timbre', [0] * 12),    # Spectral characteristics
            'confidence': current_segment.get('confidence', 0.5)
        }


    def enable(self):
        """Enable audio analysis."""
        self.enabled = True
        print("🎵 Spotify audio features enabled")

    def disable(self):
        """Disable audio analysis."""
        self.enabled = False
        print("🔇 Spotify audio features disabled")

    def pause(self):
        """Temporarily pause audio analysis."""
        self._paused = True
        print("⏸️ Audio analysis paused")

    def resume(self):
        """Resume audio analysis."""
        self._paused = False
        print("▶️ Audio analysis resumed")

    def is_enabled(self) -> bool:
        """Check if audio analysis is enabled."""
        return self.enabled and not self._paused

    def get_status(self) -> str:
        """Get current status of audio analyzer."""
        if not self.enabled:
            return "disabled"
        elif self._paused:
            return "paused"
        elif self.current_features is None:
            return "waiting"
        else:
            return "active"


def create_audio_analyzer(spotify_manager, enabled=True):
    """Factory function to create audio analyzer."""
    analyzer = AudioAnalyzer(spotify_manager, enabled=enabled)
    if enabled:
        analyzer.start_analysis()
    return analyzer
