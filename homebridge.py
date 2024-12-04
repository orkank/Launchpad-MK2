from flask import Flask, jsonify, request
import threading
import logging

class HomebridgeServer:
    def __init__(self, spotify_client, animations_dict):
        self.app = Flask(__name__)
        self.spotify = spotify_client
        self.animations = animations_dict

        # Global state for HomeKit
        self.state = {
            'power': False,
            'volume': 50,
            'playing': False,
            'current_animation': None
        }

        # Register routes
        self.register_routes()

    def register_routes(self):
        # Status endpoint
        @self.app.route('/status', methods=['GET'])
        def get_status():
            try:
                current = self.spotify.current_playback()
                if current:
                    self.state['power'] = True
                    self.state['playing'] = current['is_playing']
                    self.state['volume'] = current['device']['volume_percent']
                return jsonify(self.state)
            except:
                return jsonify(self.state)

        # Power control
        @self.app.route('/power', methods=['GET', 'PUT'])
        def power():
            if request.method == 'PUT':
                try:
                    state = request.json.get('state')
                    if state:  # Turn on
                        self.spotify.transfer_playback(device_id=self.default_device_id, force_play=False)
                    else:  # Turn off
                        self.spotify.pause_playback()
                    self.state['power'] = state
                    return jsonify({'success': True})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            return jsonify({'state': self.state['power']})

        # Playback control
        @self.app.route('/play', methods=['GET', 'PUT'])
        def play():
            if request.method == 'PUT':
                try:
                    state = request.json.get('state')
                    if state:
                        self.spotify.start_playback()
                    else:
                        self.spotify.pause_playback()
                    self.state['playing'] = state
                    return jsonify({'success': True})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            return jsonify({'state': self.state['playing']})

        # Volume control
        @self.app.route('/volume', methods=['GET', 'PUT'])
        def volume():
            if request.method == 'PUT':
                try:
                    level = request.json.get('level')
                    self.spotify.volume(level)
                    self.state['volume'] = level
                    return jsonify({'success': True})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            return jsonify({'level': self.state['volume']})

        # Animation control
        @self.app.route('/animation', methods=['GET', 'PUT'])
        def animation():
            if request.method == 'PUT':
                try:
                    animation_name = request.json.get('name')
                    if animation_name in self.animations:
                        self.state['current_animation'] = animation_name
                        return jsonify({'success': True, 'animation': animation_name})
                    else:
                        return jsonify({'error': 'Animation not found'}), 404
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            return jsonify({'animation': self.state['current_animation']})

        # List animations
        @self.app.route('/animations', methods=['GET'])
        def list_animations():
            return jsonify({
                'animations': list(self.animations.keys()),
                'current': self.state['current_animation']
            })

    def start(self, host='0.0.0.0', port=3000):
        """Start the Homebridge server"""
        threading.Thread(target=self._run_server,
                       args=(host, port),
                       daemon=True).start()
        logging.info(f"Homebridge server started on {host}:{port}")

    def _run_server(self, host, port):
        self.app.run(host=host, port=port)