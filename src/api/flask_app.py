"""Flask web API for Launchpad MK2 control."""

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from .. import __version__
from ..animations import ANIMATIONS
from ..services.playlist_manager import (
    show_playlist_animation_preview,
    generate_playlist_mappings,
    randomize_animations,
)
from ..services.spotify_manager import (
    get_active_or_default_device,
    format_track_info,
    get_oauth_redirect_uri,
    annotate_devices_with_local,
    read_default_device_id,
    fetch_and_save_playlists,
    are_spotify_credentials_configured,
    read_secret_values,
    write_secret_values,
    save_spotify_credentials,
    SECRET_FILE,
)
from ..utils.config_manager import config_manager

_API_DIR = Path(__file__).resolve().parent


def create_app(
    animation_controller=None,
    spotify_manager=None,
    playlist_manager=None,
    audio_analyzer=None,
    midi_handler=None,
    reauth_callback=None,
    user_action_manager=None,
    action_executor=None,
):
    """Create Flask application with API routes.

    Args:
        animation_controller: Animation controller instance
        spotify_manager: Spotify manager instance
        playlist_manager: Playlist manager instance
        audio_analyzer: Audio analyzer instance
        midi_handler: MIDI handler instance
        reauth_callback: Callable that performs Spotify re-authentication
        user_action_manager: User 1/2 action bank manager
        action_executor: Executes shell/URL/app/AppleScript actions

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder=str(_API_DIR / 'templates'),
        static_folder=str(_API_DIR / 'static'),
        static_url_path='/static',
    )

    # Disable HTTP request logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.logger.setLevel(logging.ERROR)

    # Store references for route handlers
    app.animation_controller = animation_controller
    app.spotify_manager = spotify_manager
    app.playlist_manager = playlist_manager
    app.midi_handler = midi_handler
    app.reauth_callback = reauth_callback
    app.user_action_manager = user_action_manager
    app.action_executor = action_executor

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
        if app.spotify_manager and app.spotify_manager.needs_reauth:
            return jsonify({
                'error': 'Spotify authentication required',
                'needs_reauth': True
            }), 401
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                devices = app.spotify_manager.spotify.devices()
                return jsonify(annotate_devices_with_local(devices))
            except Exception as e:
                if app.spotify_manager.handle_api_error(e):
                    return jsonify({
                        'error': str(e),
                        'needs_reauth': True
                    }), 401
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Spotify not initialized', 'needs_reauth': True}), 500

    @app.route('/callback')
    def spotify_oauth_callback():
        """Spotify redirects here after the user approves (or denies) access."""
        error = request.args.get('error')
        code = request.args.get('code')
        state = request.args.get('state')
        redirect_uri = get_oauth_redirect_uri()

        if not app.spotify_manager:
            return render_template(
                'auth_callback.html',
                success=False,
                message='Spotify manager is not available.',
                redirect_uri=redirect_uri,
            ), 500

        if error:
            app.spotify_manager.complete_oauth(error=error, state=state)
            return render_template(
                'auth_callback.html',
                success=False,
                message=f'Spotify returned an error: {error}',
                redirect_uri=redirect_uri,
            )

        success = app.spotify_manager.complete_oauth(code=code, state=state)
        return render_template(
            'auth_callback.html',
            success=success,
            message=None if success else (
                getattr(app.spotify_manager, '_oauth_error', None)
                or 'Could not complete Spotify login.'
            ),
            redirect_uri=redirect_uri,
        )

    @app.route('/auth/reauth', methods=['POST'])
    def reauth_spotify():
        """Clear cached tokens and open Spotify OAuth again."""
        if not app.reauth_callback:
            return jsonify({'error': 'Re-authentication not available'}), 500
        if not are_spotify_credentials_configured():
            return jsonify({
                'status': 'error',
                'error': 'Spotify Client ID and Secret are not configured',
                'message': (
                    'Add your Spotify API credentials in Settings → Spotify API Credentials, '
                    f'or edit {SECRET_FILE}.'
                ),
                'needs_reauth': True,
                'credentials_configured': False,
                'setup_required': True,
                'redirect_uri': get_oauth_redirect_uri(),
            }), 400
        try:
            success = app.reauth_callback()
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Spotify re-authenticated successfully'
                })
            return jsonify({
                'status': 'error',
                'message': (
                    'Re-authentication failed or timed out. '
                    f'Finish login in the browser (callback: {get_oauth_redirect_uri()}).'
                ),
                'needs_reauth': True,
                'redirect_uri': get_oauth_redirect_uri(),
            }), 500
        except Exception as e:
            return jsonify({'error': str(e), 'needs_reauth': True}), 500

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
            return jsonify({'default_device_id': read_default_device_id()})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/spotify-credentials', methods=['GET'])
    def get_spotify_credentials():
        """Return whether Spotify API credentials are configured (never returns the secret)."""
        secrets = read_secret_values()
        client_id = (secrets.get('client_id') or '').strip()
        configured = are_spotify_credentials_configured()
        masked_id = ''
        if client_id:
            if len(client_id) <= 8:
                masked_id = client_id[:2] + '…'
            else:
                masked_id = client_id[:4] + '…' + client_id[-4:]
        return jsonify({
            'configured': configured,
            'client_id_masked': masked_id,
            'secret_path': SECRET_FILE,
            'redirect_uri': get_oauth_redirect_uri(),
            'setup_required': not configured,
        })

    @app.route('/api/spotify-credentials', methods=['POST'])
    def set_spotify_credentials():
        """Save Spotify Client ID / Secret to config/.secret."""
        data = request.get_json(silent=True) or {}
        client_id = (data.get('client_id') or '').strip()
        client_secret = (data.get('client_secret') or '').strip()
        if not client_id or not client_secret:
            return jsonify({
                'error': 'Both client_id and client_secret are required',
            }), 400
        try:
            save_spotify_credentials(client_id, client_secret)
            return jsonify({
                'success': True,
                'configured': True,
                'message': (
                    'Credentials saved. Click Re-auth Spotify to sign in. '
                    f'Redirect URI must be {get_oauth_redirect_uri()} in the Spotify Dashboard.'
                ),
                'redirect_uri': get_oauth_redirect_uri(),
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/default-device', methods=['POST'])
    def set_default_device():
        """Set default device ID in .secret file."""
        data = request.get_json()
        device_id = data.get('device_id', '')

        try:
            write_secret_values({'default_device_id': device_id or ''})

            auto_launch_disabled = False
            # Auto-launch Spotify is only valid when default device is this Mac
            if config_manager.is_auto_launch_spotify_enabled():
                still_local = False
                if device_id and app.spotify_manager and app.spotify_manager.spotify:
                    try:
                        payload = annotate_devices_with_local(
                            app.spotify_manager.spotify.devices()
                        )
                        for device in payload.get('devices') or []:
                            if device.get('id') == device_id and device.get('is_local'):
                                still_local = True
                                break
                    except Exception:
                        still_local = False
                if not still_local:
                    config_manager.set_auto_launch_spotify(False)
                    auto_launch_disabled = True

            message = (
                f'Default device set to {device_id}' if device_id else 'Default device cleared'
            )
            if auto_launch_disabled:
                message += ' — Auto-launch Spotify turned off (default device is not this Mac)'

            return jsonify({
                'success': True,
                'message': message,
                'auto_launch_spotify': config_manager.is_auto_launch_spotify_enabled(),
                'auto_launch_disabled': auto_launch_disabled,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def _default_device_is_local_now():
        """Check whether saved default device is currently visible and local."""
        default_id = read_default_device_id()
        if not default_id or not app.spotify_manager or not app.spotify_manager.spotify:
            return False
        try:
            payload = annotate_devices_with_local(app.spotify_manager.spotify.devices())
            for device in payload.get('devices') or []:
                if device.get('id') == default_id:
                    return bool(device.get('is_local'))
        except Exception:
            return False
        return False

    @app.route('/api/app-settings', methods=['GET'])
    def get_app_settings():
        """Application settings for the Settings panel."""
        default_id = read_default_device_id()
        default_is_local = _default_device_is_local_now()
        return jsonify({
            'auto_launch_spotify': config_manager.is_auto_launch_spotify_enabled(),
            'can_enable_auto_launch': bool(default_id) and default_is_local,
            'default_device_id': default_id,
            'default_device_is_local': default_is_local,
        })

    @app.route('/api/app-settings', methods=['POST'])
    def set_app_settings():
        """Update application settings (e.g. auto-launch Spotify)."""
        data = request.get_json() or {}

        if 'auto_launch_spotify' in data:
            enabled = bool(data.get('auto_launch_spotify'))
            if enabled:
                if not read_default_device_id():
                    return jsonify({
                        'error': 'Set a default device first',
                        'auto_launch_spotify': False,
                        'can_enable_auto_launch': False,
                    }), 400
                if not _default_device_is_local_now():
                    return jsonify({
                        'error': (
                            'Auto-launch Spotify can only be enabled when the '
                            'default device is this Mac (Computer device matching this machine).'
                        ),
                        'auto_launch_spotify': config_manager.is_auto_launch_spotify_enabled(),
                        'can_enable_auto_launch': False,
                    }), 400
            config_manager.set_auto_launch_spotify(enabled)

        default_id = read_default_device_id()
        default_is_local = _default_device_is_local_now()
        return jsonify({
            'success': True,
            'auto_launch_spotify': config_manager.is_auto_launch_spotify_enabled(),
            'can_enable_auto_launch': bool(default_id) and default_is_local,
            'default_device_id': default_id,
            'default_device_is_local': default_is_local,
        })

    @app.route('/')
    def index():
        """Render the main web interface."""
        return render_template('index.html', app_version=__version__)

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
        credentials_ok = are_spotify_credentials_configured()
        status = {
            'spotify_connected': False,
            'needs_reauth': False,
            'credentials_configured': credentials_ok,
            'setup_required': not credentials_ok,
            'secret_path': SECRET_FILE,
            'redirect_uri': get_oauth_redirect_uri(),
            'current_track': None,
            'is_playing': False,
            'current_animation': None,
            'launchpad_connected': False,
            'launchpad_port': None,
        }

        # Animation + Launchpad MIDI status (cached; health monitor probes periodically)
        if app.animation_controller:
            status['current_animation'] = app.animation_controller.current_animation
            launchpad = getattr(app.animation_controller, 'launchpad', None)
            if launchpad:
                status['launchpad_connected'] = bool(launchpad.is_connected())
                status['launchpad_port'] = launchpad.port_name if status['launchpad_connected'] else None

        # Spotify status
        if not credentials_ok:
            status['needs_reauth'] = True
            return jsonify(status)

        if app.spotify_manager and app.spotify_manager.needs_reauth:
            status['needs_reauth'] = True
            return jsonify(status)

        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                current = app.spotify_manager.get_current_playback()
                status['spotify_connected'] = True

                if current and current.get('item'):
                    track = current['item']
                    artists = ", ".join([artist['name'] for artist in track['artists']])
                    status['current_track'] = {
                        'name': track['name'],
                        'artists': artists,
                        'duration_ms': track['duration_ms']
                    }
                    status['is_playing'] = current['is_playing']

            except Exception as e:
                if app.spotify_manager.handle_api_error(e):
                    status['needs_reauth'] = True
                else:
                    print(f"Error getting Spotify status: {e}")

        return jsonify(status)

    def _spotify_playback_error(exc):
        if app.spotify_manager and app.spotify_manager.handle_api_error(exc):
            return jsonify({
                'error': str(exc),
                'needs_reauth': True
            }), 401
        return jsonify({'error': str(exc)}), 500

    @app.route('/play', methods=['POST'])
    def play():
        """Start Spotify playback."""
        if app.spotify_manager and app.spotify_manager.needs_reauth:
            return jsonify({'error': 'Spotify authentication required', 'needs_reauth': True}), 401
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(
                    app.spotify_manager.spotify, app.spotify_manager
                )
                if device_id:
                    app.spotify_manager.spotify.start_playback(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    err = {'error': 'No active device found'}
                    if app.spotify_manager.needs_reauth:
                        err['needs_reauth'] = True
                        return jsonify(err), 401
                    return jsonify(err), 400
            except Exception as e:
                return _spotify_playback_error(e)
        return jsonify({'error': 'Spotify not initialized', 'needs_reauth': True}), 500

    @app.route('/pause', methods=['POST'])
    def pause():
        """Pause Spotify playback."""
        if app.spotify_manager and app.spotify_manager.needs_reauth:
            return jsonify({'error': 'Spotify authentication required', 'needs_reauth': True}), 401
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(
                    app.spotify_manager.spotify, app.spotify_manager
                )
                if device_id:
                    app.spotify_manager.spotify.pause_playback(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    err = {'error': 'No active device found'}
                    if app.spotify_manager.needs_reauth:
                        err['needs_reauth'] = True
                        return jsonify(err), 401
                    return jsonify(err), 400
            except Exception as e:
                return _spotify_playback_error(e)
        return jsonify({'error': 'Spotify not initialized', 'needs_reauth': True}), 500

    @app.route('/next', methods=['POST'])
    def next_track():
        """Skip to next track."""
        if app.spotify_manager and app.spotify_manager.needs_reauth:
            return jsonify({'error': 'Spotify authentication required', 'needs_reauth': True}), 401
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(
                    app.spotify_manager.spotify, app.spotify_manager
                )
                if device_id:
                    app.spotify_manager.spotify.next_track(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    err = {'error': 'No active device found'}
                    if app.spotify_manager.needs_reauth:
                        err['needs_reauth'] = True
                        return jsonify(err), 401
                    return jsonify(err), 400
            except Exception as e:
                return _spotify_playback_error(e)
        return jsonify({'error': 'Spotify not initialized', 'needs_reauth': True}), 500

    @app.route('/previous', methods=['POST'])
    def previous_track():
        """Skip to previous track."""
        if app.spotify_manager and app.spotify_manager.needs_reauth:
            return jsonify({'error': 'Spotify authentication required', 'needs_reauth': True}), 401
        if app.spotify_manager and app.spotify_manager.spotify:
            try:
                device_id = get_active_or_default_device(
                    app.spotify_manager.spotify, app.spotify_manager
                )
                if device_id:
                    app.spotify_manager.spotify.previous_track(device_id=device_id)
                    return jsonify({'status': 'success'})
                else:
                    err = {'error': 'No active device found'}
                    if app.spotify_manager.needs_reauth:
                        err['needs_reauth'] = True
                        return jsonify(err), 401
                    return jsonify(err), 400
            except Exception as e:
                return _spotify_playback_error(e)
        return jsonify({'error': 'Spotify not initialized', 'needs_reauth': True}), 500

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

    @app.route('/api/playlists/fetch', methods=['POST'])
    def fetch_playlists():
        """Fetch playlists from Spotify and save to .playlists (CLI: p)."""
        if not app.spotify_manager or not app.spotify_manager.ensure_ready():
            return jsonify({
                'error': 'Spotify authentication required',
                'needs_reauth': bool(app.spotify_manager and app.spotify_manager.needs_reauth),
            }), 401

        try:
            playlists = fetch_and_save_playlists(app.spotify_manager.spotify)
            if playlists is None:
                return jsonify({'error': 'Failed to fetch playlists from Spotify'}), 500
            count = len(playlists)
            return jsonify({
                'success': True,
                'message': f'Fetched and saved {count} playlists to .playlists',
                'count': count,
            })
        except Exception as e:
            if app.spotify_manager.handle_api_error(e):
                return jsonify({'error': str(e), 'needs_reauth': True}), 401
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/generate', methods=['POST'])
    def generate_mappings():
        """Auto-generate playlist↔pad mappings (CLI: g)."""
        if not app.spotify_manager or not app.spotify_manager.ensure_ready():
            return jsonify({
                'error': 'Spotify authentication required',
                'needs_reauth': bool(app.spotify_manager and app.spotify_manager.needs_reauth),
            }), 401
        if not app.playlist_manager:
            return jsonify({'error': 'Playlist manager not available'}), 503

        data = request.get_json(silent=True) or {}
        filter_type = (data.get('filter') or 'newest').lower()
        if filter_type not in ('newest', 'popular', 'all'):
            return jsonify({'error': 'filter must be newest, popular, or all'}), 400

        mode = (data.get('mode') or 'fill').lower()
        if mode not in ('fill', 'replace'):
            return jsonify({'error': 'mode must be fill or replace'}), 400
        replace_all = mode == 'replace'

        try:
            before = len(app.playlist_manager.mappings)
            generate_playlist_mappings(
                app.spotify_manager.spotify,
                ANIMATIONS,
                filter_type,
                replace_all=replace_all,
            )
            app.playlist_manager.load_mappings()
            after = len(app.playlist_manager.mappings)
            if replace_all:
                message = (
                    f'Replaced all mappings ({filter_type}). '
                    f'{before} → {after} pads mapped.'
                )
            else:
                message = (
                    f'Filled empty pads ({filter_type}). '
                    f'Total pads mapped: {after} (+{after - before}).'
                )
            return jsonify({
                'success': True,
                'filter': filter_type,
                'mode': mode,
                'replace_all': replace_all,
                'mappings_before': before,
                'mappings_after': after,
                'message': message,
            })
        except Exception as e:
            if app.spotify_manager.handle_api_error(e):
                return jsonify({'error': str(e), 'needs_reauth': True}), 401
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapping/randomize-animations', methods=['POST'])
    def randomize_mapping_animations():
        """Randomize animation for every mapped playlist (CLI: r)."""
        if not app.playlist_manager:
            return jsonify({'error': 'Playlist manager not available'}), 503

        try:
            randomize_animations(ANIMATIONS)
            app.playlist_manager.load_mappings()
            return jsonify({
                'success': True,
                'count': len(app.playlist_manager.mappings),
                'message': f'Randomized animations for {len(app.playlist_manager.mappings)} mappings',
            })
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

    @app.route('/api/mapping/clear-all', methods=['POST'])
    def clear_all_mappings():
        """Clear every playlist mapping."""
        if not app.playlist_manager:
            return jsonify({'error': 'Playlist manager not available'}), 503

        try:
            cleared = len(app.playlist_manager.mappings)
            app.playlist_manager.mappings.clear()
            app.playlist_manager.save_mappings()
            return jsonify({
                'success': True,
                'cleared': cleared,
                'message': f'Cleared {cleared} mapping(s)',
            })
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

    def _normalize_user_action(data):
        """Validate and normalize a user action payload from the web UI."""
        if not data:
            return None, 'Action payload is required'

        action_type = data.get('type')
        allowed = ('shell', 'open_url', 'http_request', 'app_toggle', 'applescript')
        if action_type not in allowed:
            return None, f'Invalid action type. Allowed: {", ".join(allowed)}'

        action = {
            'label': (data.get('label') or '').strip() or action_type,
            'type': action_type,
        }

        if action_type == 'shell':
            command = (data.get('command') or '').strip()
            if not command:
                return None, 'command is required for shell actions'
            action['command'] = command

        elif action_type == 'open_url':
            url = (data.get('url') or '').strip()
            if not url:
                return None, 'url is required for open_url actions'
            action['url'] = url

        elif action_type == 'http_request':
            url = (data.get('url') or '').strip()
            if not url:
                return None, 'url is required for http_request actions'
            method = (data.get('method') or 'GET').upper()
            headers = data.get('headers') or {}
            if isinstance(headers, str):
                headers = headers.strip()
                if headers:
                    import json as _json
                    try:
                        headers = _json.loads(headers)
                    except Exception:
                        return None, 'headers must be a JSON object'
                else:
                    headers = {}
            if not isinstance(headers, dict):
                return None, 'headers must be an object'
            action['url'] = url
            action['method'] = method
            action['headers'] = headers
            action['body'] = data.get('body') if data.get('body') is not None else ''

        elif action_type == 'app_toggle':
            app_name = (data.get('app_name') or '').strip()
            if not app_name:
                return None, 'app_name is required for app_toggle actions'
            action['app_name'] = app_name
            action['force_kill'] = bool(data.get('force_kill'))

        elif action_type == 'applescript':
            script = (data.get('script') or '').strip()
            if not script:
                return None, 'script is required for applescript actions'
            action['script'] = script

        return action, None

    @app.route('/api/user-actions', methods=['GET'])
    def get_user_actions():
        """List User 1 / User 2 action banks."""
        if not app.user_action_manager:
            return jsonify({'error': 'User action manager not available'}), 503
        profile = request.args.get('profile')
        if profile:
            if profile not in ('user1', 'user2'):
                return jsonify({'error': 'profile must be user1 or user2'}), 400
            return jsonify({'profile': profile, 'actions': app.user_action_manager.list_profile(profile)})
        return jsonify(app.user_action_manager.list_all())

    @app.route('/api/user-actions/running-apps', methods=['GET'])
    def get_running_apps():
        """List currently running macOS apps for app_toggle picker."""
        from ..services.action_executor import ActionExecutor

        include_background = request.args.get('background', '').lower() in ('1', 'true', 'yes')
        try:
            executor = app.action_executor or ActionExecutor()
            apps = executor.list_running_apps(include_background=include_background)
            return jsonify({
                'apps': apps,
                'count': len(apps),
                'include_background': include_background,
            })
        except Exception as e:
            return jsonify({'error': str(e), 'apps': []}), 500

    @app.route('/api/user-actions/start', methods=['POST'])
    def start_user_action_mapping():
        """Start pad capture for a user action."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503

        data = request.get_json() or {}
        profile = data.get('profile')
        if profile not in ('user1', 'user2'):
            return jsonify({'error': 'profile must be user1 or user2'}), 400

        action, err = _normalize_user_action(data.get('action') or data)
        if err:
            return jsonify({'error': err}), 400

        try:
            success = app.midi_handler.start_user_action_mapping(profile, action)
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Press a Launchpad button to map this action to {profile}.'
                })
            return jsonify({'error': 'Mapping mode already active or user actions unavailable'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user-actions/cancel', methods=['POST'])
    def cancel_user_action_mapping():
        """Cancel user-action mapping mode."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503
        try:
            success = app.midi_handler.cancel_mapping_mode()
            return jsonify({
                'success': success,
                'message': 'Mapping mode cancelled' if success else 'Mapping mode not active'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user-actions/status', methods=['GET'])
    def get_user_action_status():
        """Mapping status + last executed action message."""
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503
        try:
            return jsonify(app.midi_handler.get_user_action_status())
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user-actions/confirm-overwrite', methods=['POST'])
    def confirm_user_action_overwrite():
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503
        try:
            success = app.midi_handler.confirm_overwrite()
            if success:
                return jsonify({'success': True, 'message': 'User action overwritten successfully'})
            return jsonify({'error': 'No pending confirmation'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user-actions/cancel-overwrite', methods=['POST'])
    def cancel_user_action_overwrite():
        if not app.midi_handler:
            return jsonify({'error': 'MIDI handler not available'}), 503
        try:
            success = app.midi_handler.cancel_overwrite()
            if success:
                return jsonify({'success': True, 'message': 'Mapping cancelled'})
            return jsonify({'error': 'No pending confirmation'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user-actions/delete', methods=['POST'])
    def delete_user_action():
        if not app.user_action_manager:
            return jsonify({'error': 'User action manager not available'}), 503

        data = request.get_json() or {}
        profile = data.get('profile')
        x = data.get('x')
        y = data.get('y')
        if profile not in ('user1', 'user2'):
            return jsonify({'error': 'profile must be user1 or user2'}), 400
        if x is None or y is None:
            return jsonify({'error': 'Coordinates (x, y) are required'}), 400

        try:
            if app.user_action_manager.delete(profile, int(x), int(y)):
                app.user_action_manager.save()
                return jsonify({
                    'success': True,
                    'message': f'Action at ({x},{y}) deleted from {profile}'
                })
            return jsonify({'error': 'No action found at this coordinate'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user-actions/update', methods=['POST'])
    def update_user_action():
        """Update an existing pad action without re-mapping."""
        if not app.user_action_manager:
            return jsonify({'error': 'User action manager not available'}), 503

        data = request.get_json() or {}
        profile = data.get('profile')
        x = data.get('x')
        y = data.get('y')
        if profile not in ('user1', 'user2'):
            return jsonify({'error': 'profile must be user1 or user2'}), 400
        if x is None or y is None:
            return jsonify({'error': 'Coordinates (x, y) are required'}), 400

        existing = app.user_action_manager.get(profile, int(x), int(y))
        if not existing:
            return jsonify({'error': 'No action found at this coordinate'}), 404

        action, err = _normalize_user_action(data.get('action') or data)
        if err:
            return jsonify({'error': err}), 400

        try:
            app.user_action_manager.set(profile, int(x), int(y), action)
            app.user_action_manager.save()
            return jsonify({
                'success': True,
                'message': f'Action at ({x},{y}) updated for {profile}'
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
