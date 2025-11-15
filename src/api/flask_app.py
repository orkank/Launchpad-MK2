"""Flask web API for Launchpad MK2 control."""

import logging
from flask import Flask, jsonify, render_template
from ..services.playlist_manager import show_playlist_animation_preview
from ..services.spotify_manager import get_active_or_default_device, format_track_info


def create_app(animation_controller=None, spotify_manager=None, playlist_manager=None, audio_analyzer=None):
    """Create Flask application with API routes.

    Args:
        animation_controller: Animation controller instance
        spotify_manager: Spotify manager instance
        playlist_manager: Playlist manager instance

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__, template_folder='templates')

    # Disable HTTP request logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.logger.setLevel(logging.ERROR)

    # Store references for route handlers
    app.animation_controller = animation_controller
    app.spotify_manager = spotify_manager
    app.playlist_manager = playlist_manager

    @app.route('/animation/<name>')
    def set_animation(name):
        if app.animation_controller and hasattr(app.animation_controller, 'set_animation'):
            result = app.animation_controller.set_animation(name)
            if result:
                return jsonify({'status': 'success', 'animation': name})
        return jsonify({'status': 'error', 'message': 'Animation not found'}), 404

    @app.route('/stop')
    def stop_animation():
        if app.animation_controller and hasattr(app.animation_controller, 'stop_animation'):
            app.animation_controller.stop_animation()
            return jsonify({'status': 'success', 'message': 'Animation stopped'})
        return jsonify({'status': 'error', 'message': 'Controller not available'}), 500

    @app.route('/list')
    def list_animations():
        if app.animation_controller and hasattr(app.animation_controller, 'get_available_animations'):
            animations = app.animation_controller.get_available_animations()
            return jsonify(animations)
        return jsonify([])

    @app.route('/devices')
    def list_devices():
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                devices = app.spotify_manager.spotify.devices()
                return jsonify(devices)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Spotify not initialized'}), 500

    @app.route('/device/<device_id>')
    def select_device(device_id):
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                app.spotify_manager.spotify.transfer_playback(device_id)
                return jsonify({'success': True, 'message': f'Playback transferred to device {device_id}'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Spotify not initialized'}), 500

    @app.route('/')
    def index():
        """Render the main web interface."""
        return render_template('index.html')

    @app.route('/mappings')
    def get_mappings():
        """Get playlist mappings in JSON format."""
        if app.playlist_manager:
            mappings = show_playlist_animation_preview(app.playlist_manager.mappings, 'json')
            return jsonify(mappings)
        return jsonify({})

    @app.route('/status')
    def get_status():
        """Get current system status."""
        status = {
            'spotify_connected': False,
            'current_track': None,
            'is_playing': False,
            'current_animation': None
        }

        # Animation status
        if app.animation_controller:
            status['current_animation'] = app.animation_controller.current_animation

        # Spotify status
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                current = app.spotify_manager.spotify.current_playback()
                status['spotify_connected'] = True

                if current and current['item']:
                    track = current['item']
                    artists = ", ".join([artist['name'] for artist in track['artists']])
                    status['current_track'] = {
                        'name': track['name'],
                        'artists': artists,
                        'duration_ms': track['duration_ms']
                    }
                    status['is_playing'] = current['is_playing']

            except Exception as e:
                print(f"Error getting Spotify status: {e}")

        return jsonify(status)

    @app.route('/play', methods=['POST'])
    def play():
        """Start Spotify playback."""
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(app.spotify_manager.spotify)
                if device_id:
                    app.spotify_manager.spotify.start_playback(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'No active device found'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Spotify not initialized'}), 500

    @app.route('/pause', methods=['POST'])
    def pause():
        """Pause Spotify playback."""
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(app.spotify_manager.spotify)
                if device_id:
                    app.spotify_manager.spotify.pause_playback(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'No active device found'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Spotify not initialized'}), 500

    @app.route('/next', methods=['POST'])
    def next_track():
        """Skip to next track."""
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(app.spotify_manager.spotify)
                if device_id:
                    app.spotify_manager.spotify.next_track(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'No active device found'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Spotify not initialized'}), 500

    @app.route('/previous', methods=['POST'])
    def previous_track():
        """Skip to previous track."""
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(app.spotify_manager.spotify)
                if device_id:
                    app.spotify_manager.spotify.previous_track(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    return jsonify({'error': 'No active device found'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Spotify not initialized'}), 500

    # Audio Features Endpoints
    @app.route('/api/audio_features/status')
    def get_audio_features_status():
        """Get audio features status."""
        if not audio_analyzer:
            return jsonify({'error': 'Audio analyzer not available'}), 503

        status = {
            'enabled': audio_analyzer.enabled,
            'paused': audio_analyzer._paused,
            'status': audio_analyzer.get_status(),
            'thread_alive': audio_analyzer.analysis_thread.is_alive() if audio_analyzer.analysis_thread else False
        }

        # Add current track features if available
        if audio_analyzer.current_features:
            status['current_features'] = audio_analyzer.current_features
            status['suggested_animation'] = audio_analyzer.suggest_animation()

        return jsonify(status)

    @app.route('/api/audio_features/enable', methods=['POST'])
    def enable_audio_features():
        """Enable audio features."""
        if not audio_analyzer:
            return jsonify({'error': 'Audio analyzer not available'}), 503

        try:
            audio_analyzer.enable()
            if not audio_analyzer.analysis_thread or not audio_analyzer.analysis_thread.is_alive():
                audio_analyzer.start_analysis()
            return jsonify({'success': True, 'message': 'Audio features enabled'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/audio_features/disable', methods=['POST'])
    def disable_audio_features():
        """Disable audio features."""
        if not audio_analyzer:
            return jsonify({'error': 'Audio analyzer not available'}), 503

        try:
            audio_analyzer.disable()
            return jsonify({'success': True, 'message': 'Audio features disabled'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/audio_features/pause', methods=['POST'])
    def pause_audio_features():
        """Pause audio features."""
        if not audio_analyzer:
            return jsonify({'error': 'Audio analyzer not available'}), 503

        try:
            audio_analyzer.pause()
            return jsonify({'success': True, 'message': 'Audio analysis paused'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/audio_features/resume', methods=['POST'])
    def resume_audio_features():
        """Resume audio features."""
        if not audio_analyzer:
            return jsonify({'error': 'Audio analyzer not available'}), 503

        try:
            audio_analyzer.resume()
            return jsonify({'success': True, 'message': 'Audio analysis resumed'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app


# Global app instance for backwards compatibility
_app_instance = None

def get_app_instance():
    """Get the global app instance."""
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance
