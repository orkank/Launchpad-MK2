"""Flask web API for Launchpad MK2 control."""

import logging
from flask import Flask, jsonify, render_template, request
from ..services.playlist_manager import show_playlist_animation_preview
from ..services.spotify_manager import get_active_or_default_device, format_track_info


def create_app(animation_controller=None, spotify_manager=None, playlist_manager=None, audio_analyzer=None, midi_handler=None):
    """Create Flask application with API routes.

    Args:
        animation_controller: Animation controller instance
        spotify_manager: Spotify manager instance
        playlist_manager: Playlist manager instance
        audio_analyzer: Audio analyzer instance
        midi_handler: MIDI handler instance

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
    app.midi_handler = midi_handler

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

    @app.route('/api/default-device', methods=['GET'])
    def get_default_device():
        """Get default device ID from .secret file."""
        try:
            with open('config/.secret', 'r') as f:
                secrets = dict(line.strip().split('=', 1) for line in f if '=' in line)
                default_device_id = secrets.get('default_device_id', '')
                return jsonify({'default_device_id': default_device_id})
        except FileNotFoundError:
            return jsonify({'default_device_id': ''})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/default-device', methods=['POST'])
    def set_default_device():
        """Set default device ID in .secret file."""
        data = request.get_json()
        device_id = data.get('device_id', '')

        try:
            # Read existing secrets
            secrets = {}
            try:
                with open('config/.secret', 'r') as f:
                    secrets = dict(line.strip().split('=', 1) for line in f if '=' in line)
            except FileNotFoundError:
                pass

            # Update default_device_id
            secrets['default_device_id'] = device_id

            # Write back to file
            with open('config/.secret', 'w') as f:
                for key, value in secrets.items():
                    f.write(f"{key}={value}\n")

            return jsonify({
                'success': True,
                'message': f'Default device set to {device_id}' if device_id else 'Default device cleared'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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

    # Playlist Mapping Endpoints
    @app.route('/api/playlists', methods=['GET'])
    def get_playlists():
        """Get list of user's Spotify playlists."""
        if not app.spotify_manager or not app.spotify_manager.spotify:
            return jsonify({'error': 'Spotify not initialized'}), 500

        try:
            playlists = []
            results = app.spotify_manager.spotify.current_user_playlists(limit=50)

            while results:
                for item in results['items']:
                    playlists.append({
                        'name': item['name'],
                        'id': item['id'],
                        'tracks': item['tracks']['total']
                    })

                if results['next']:
                    results = app.spotify_manager.spotify.next(results)
                else:
                    break

            return jsonify({'playlists': playlists})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/start', methods=['POST'])
    def start_mapping():
        """Start mapping mode for a playlist."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503

        data = request.get_json()
        playlist_name = data.get('playlist')
        animation_name = data.get('animation')  # Optional

        if not playlist_name:
            return jsonify({'error': 'Playlist name is required'}), 400

        try:
            success = app.midi_handler.start_mapping_mode(playlist_name, animation_name)
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Mapping mode started. Press a button on your Launchpad.'
                })
            else:
                return jsonify({'error': 'Mapping mode already active'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/cancel', methods=['POST'])
    def cancel_mapping():
        """Cancel mapping mode."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503

        try:
            success = app.midi_handler.cancel_mapping_mode()
            if success:
                return jsonify({'success': True, 'message': 'Mapping mode cancelled'})
            else:
                return jsonify({'success': False, 'message': 'Mapping mode not active'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/status', methods=['GET'])
    def get_mapping_status():
        """Get current mapping mode status."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503

        try:
            status = app.midi_handler.get_mapping_status()
            return jsonify(status)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/confirm-overwrite', methods=['POST'])
    def confirm_overwrite():
        """Confirm overwrite of existing mapping."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503

        try:
            success = app.midi_handler.confirm_overwrite()
            if success:
                return jsonify({'success': True, 'message': 'Mapping overwritten successfully'})
            else:
                return jsonify({'error': 'No pending confirmation'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/cancel-overwrite', methods=['POST'])
    def cancel_overwrite():
        """Cancel overwrite of existing mapping."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503

        try:
            success = app.midi_handler.cancel_overwrite()
            if success:
                return jsonify({'success': True, 'message': 'Mapping cancelled'})
            else:
                return jsonify({'error': 'No pending confirmation'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/delete', methods=['POST'])
    def delete_mapping():
        """Delete a playlist mapping."""
        if not app.playlist_manager:
            return jsonify({'error': 'Playlist manager not available'}), 503

        data = request.get_json()
        x = data.get('x')
        y = data.get('y')

        if x is None or y is None:
            return jsonify({'error': 'Coordinates (x, y) are required'}), 400

        try:
            # Check if mapping exists
            mapping = app.playlist_manager.get_mapping(x, y)
            if not mapping:
                return jsonify({'error': 'No mapping found at this coordinate'}), 404

            # Delete mapping
            if (x, y) in app.playlist_manager.mappings:
                del app.playlist_manager.mappings[(x, y)]
                app.playlist_manager.save_mappings()
                return jsonify({
                    'success': True,
                    'message': f'Mapping at ({x},{y}) deleted'
                })
            else:
                return jsonify({'error': 'Mapping not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/update-animation', methods=['POST'])
    def update_mapping_animation():
        """Update animation for a playlist mapping."""
        if not app.playlist_manager:
            return jsonify({'error': 'Playlist manager not available'}), 503

        data = request.get_json()
        x = data.get('x')
        y = data.get('y')
        animation = data.get('animation')  # Can be None or empty string

        if x is None or y is None:
            return jsonify({'error': 'Coordinates (x, y) are required'}), 400

        try:
            # Check if mapping exists
            mapping = app.playlist_manager.get_mapping(x, y)
            if not mapping:
                return jsonify({'error': 'No mapping found at this coordinate'}), 404

            # Update animation (empty string becomes None)
            animation_name = animation if animation else None
            app.playlist_manager.set_mapping(x, y, mapping['name'], animation_name)
            app.playlist_manager.save_mappings()

            return jsonify({
                'success': True,
                'message': f'Animation updated for mapping at ({x},{y})'
            })
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
