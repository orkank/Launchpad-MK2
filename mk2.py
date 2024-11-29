import rtmidi
import time
import colorsys
import sys
import random
import math
import threading
from flask import Flask, jsonify
from queue import Queue
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json

app = Flask(__name__)

# Global variables for control
current_animation = None
animation_thread = None
command_queue = Queue()
should_run = True
spotify = None

def load_playlist_mappings():
    try:
        with open('playlists.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convert string coordinates back to tuples
            mappings = {}
            for coord, info in data['mappings'].items():
                x, y = map(int, coord.split(','))
                mappings[(x, y)] = info['name']
            return mappings
    except FileNotFoundError:
        print("Warning: playlists.json not found, using empty mapping")
        return {}
    except json.JSONDecodeError:
        print("Error: Invalid JSON in playlists.json")
        return {}
    except Exception as e:
        print(f"Error loading playlist mappings: {str(e)}")
        return {}

# Load mappings when script starts
playlist_mappings = load_playlist_mappings()

def initialize_launchpad():
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
                            midi_in.set_callback(on_midi_message)
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
    for y in range(9):
        for x in range(9):
            set_color(midi_out, x, y, 0, 0, 0)

def rainbow_wave(midi_out):
    while should_run and current_animation == 'rainbow':
        for offset in range(0, 100, 2):
            if current_animation != 'rainbow':
                break
            for y in range(9):
                for x in range(9):
                    center_x, center_y = 3.5, 3.5
                    distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                    hue = (offset + distance * 10) % 100 / 100.0
                    r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
                    set_color(midi_out, x, y, r, g, b)
            time.sleep(0.05)

def matrix_rain(midi_out):
    drops = []
    grid_width = 9  # Match grid size
    grid_height = 9

    while should_run and current_animation == 'matrix':
        # Create new drops
        if random.random() < 0.3:
            drops.append({
                'x': random.randint(0, grid_width - 1),
                'y': grid_height - 1,
                'speed': random.uniform(0.2, 0.5)
            })

        # Clear grid
        clear_all(midi_out)

        # Update and draw drops
        new_drops = []
        for drop in drops:
            drop['y'] -= drop['speed']
            if drop['y'] > 0:
                x = int(drop['x'])
                y = int(drop['y'])
                if 0 <= x < grid_width and 0 <= y < grid_height:
                    intensity = min(255, int((1.0 - (drop['y'] / grid_height)) * 255))
                    set_color(midi_out, x, y, 0, intensity, 0)
                    new_drops.append(drop)

        drops = new_drops
        time.sleep(0.05)

def pulse_rings(midi_out):
    center_x = 4  # Center X coordinate (same as rainbow)
    center_y = 4  # Center Y coordinate (same as rainbow)
    max_radius = 8  # Maximum radius to cover the grid
    phase = 0

    while should_run and current_animation == 'pulse':
        # Clear grid
        clear_all(midi_out)

        # Calculate pulse intensity (0 to 1)
        pulse = (math.sin(phase / 10) + 1) / 2

        # Draw concentric rings
        for y in range(9):
            for x in range(9):
                # Calculate distance from center
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx*dx + dy*dy)

                # Calculate color intensity based on distance and pulse
                intensity = 1.0 - (distance / max_radius)
                if intensity < 0:
                    intensity = 0

                # Modulate intensity with pulse
                intensity *= pulse

                # Set color (using similar color scheme to rainbow)
                r = int(255 * intensity)
                g = int(100 * intensity)
                b = int(200 * intensity)

                set_color(midi_out, x, y, r, g, b)

        phase += 1
        time.sleep(0.05)

def random_sparkle(midi_out):
    grid_width = 9  # Match grid size
    grid_height = 9
    sparkles = []

    while should_run and current_animation == 'sparkle':
        # Add new sparkles
        if random.random() < 0.2:
            sparkles.append({
                'x': random.randint(0, grid_width - 1),
                'y': random.randint(0, grid_height - 1),
                'life': 1.0,
                'color': (
                    random.randint(100, 255),
                    random.randint(100, 255),
                    random.randint(100, 255)
                )
            })

        # Clear grid
        clear_all(midi_out)

        # Update and draw sparkles
        new_sparkles = []
        for sparkle in sparkles:
            if sparkle['life'] > 0:
                x = sparkle['x']
                y = sparkle['y']
                intensity = sparkle['life']
                r = int(sparkle['color'][0] * intensity)
                g = int(sparkle['color'][1] * intensity)
                b = int(sparkle['color'][2] * intensity)
                set_color(midi_out, x, y, r, g, b)

                sparkle['life'] -= 0.05
                if sparkle['life'] > 0:
                    new_sparkles.append(sparkle)

        sparkles = new_sparkles
        time.sleep(0.05)

def initialize_spotify():
    global spotify
    try:
        # Read credentials from .secret file
        credentials = {}
        try:
            with open('.secret', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        credentials[key] = value
        except FileNotFoundError:
            print("Error: .secret file not found!")
            print("Please create a .secret file with your Spotify credentials:")
            print("client_id=YOUR_CLIENT_ID")
            print("client_secret=YOUR_CLIENT_SECRET")
            return False

        if 'client_id' not in credentials or 'client_secret' not in credentials:
            print("Error: Missing credentials in .secret file!")
            print("File should contain client_id and client_secret")
            return False

        auth_manager = SpotifyOAuth(
            client_id=credentials['client_id'],
            client_secret=credentials['client_secret'],
            redirect_uri='http://localhost:8888/callback',
            scope='user-modify-playback-state user-read-playback-state playlist-read-private',
            open_browser=False
        )

        # Check if there's a cached token and it's still valid
        token_info = auth_manager.cache_handler.get_cached_token()
        if not token_info or not auth_manager.validate_token(token_info):
            # Get the authorization URL
            auth_url = auth_manager.get_authorize_url()
            print(f"\nPlease go to this URL and authorize the app:\n{auth_url}\n")

            # Get the response URL from user
            response = input("Enter the full redirect URL: ").strip()

            # Extract code from response
            code = auth_manager.parse_response_code(response)

            # Get and cache the token
            token_info = auth_manager.get_cached_token()
            if not token_info:
                token_info = auth_manager.get_access_token(code, as_dict=True)
                auth_manager.cache_handler.save_token_to_cache(token_info)

        spotify = spotipy.Spotify(auth_manager=auth_manager)

        # Test the connection
        spotify.current_user()  # This will raise an exception if authentication failed
        print("Successfully connected to Spotify!")
        return True

    except Exception as e:
        print(f"Error initializing Spotify: {str(e)}")
        if "invalid_grant" in str(e):
            print("\nTip: The authorization code can only be used once.")
            print("Try deleting the .cache file and running the script again.")
        return False

def show_spotify_devices():
    if spotify is None:
        print("\nSpotify not initialized")
        return

    try:
        devices = spotify.devices()
        print("\nAvailable Spotify Devices:")
        print("-------------------------")
        for i, device in enumerate(devices['devices']):
            status = "ACTIVE" if device['is_active'] else "inactive"
            volume = device.get('volume_percent', 'N/A')
            print(f"{i+1}. {device['name']} ({device['type']}) - {status}")
            print(f"   ID: {device['id']}")
            print(f"   Volume: {volume}%")
            print("-------------------------")

        # Ask user to select a device
        try:
            choice = input("\nSelect device number (or press Enter to cancel): ").strip()
            if choice:
                device_num = int(choice) - 1
                if 0 <= device_num < len(devices['devices']):
                    device = devices['devices'][device_num]
                    spotify.transfer_playback(device_id=device['id'])
                    print(f"\nPlayback transferred to: {device['name']}")
                else:
                    print("Invalid device number!")
        except ValueError:
            print("Invalid input! Please enter a number.")

    except Exception as e:
        print(f"Error getting devices: {str(e)}")

def on_midi_message(message, time_stamp):
    status_byte, note, velocity = message[0]

    if note >= 104:  # Top row
        x = note - 104
        y = 8
    elif note % 10 == 9:  # Right column
        x = 8
        y = (note - 19) // 10
    else:  # Main grid
        x = (note - 11) % 10
        y = (note - 11) // 10

    print(f"Button pressed - x: {x}, y: {y}, velocity: {velocity}")

    if velocity > 0:  # Button press (not release)
        if x == 8 and y == 8:  # Top-right button ('S' button)
            show_spotify_devices()
        else:
            play_playlist_for_button(x, y)

def get_playlist_id_by_name(playlist_name):
    try:
        with open('.playlists', 'r', encoding='utf-8') as f:
            current_name = None
            current_id = None
            for line in f:
                if line.startswith('-------------------------'):
                    continue
                elif '. ' in line and ' tracks)' in line:
                    current_name = line.split('. ', 1)[1].rsplit(' (', 1)[0]
                    if current_name.lower() == playlist_name.lower():
                        # Next line will be the ID
                        current_id = next(f).strip()
                        return current_id
    except FileNotFoundError:
        print("Playlist file not found. Please run 'p' command first to fetch playlists.")
    except Exception as e:
        print(f"Error reading playlist file: {str(e)}")
    return None

def play_playlist_for_button(x, y):
    if spotify is None:
        print("Spotify not initialized")
        return

    if (x, y) in playlist_mappings:
        try:
            # Get available devices
            devices = spotify.devices()

            # Find an active device or the first available device
            device_id = None
            for device in devices['devices']:
                if device['is_active']:
                    device_id = device['id']
                    break
                elif device['type'] == 'Computer':  # Fallback to first computer device
                    device_id = device['id']

            if not device_id:
                print("No Spotify devices found. Please open Spotify app first!")
                return

            # Get playlist ID from name
            playlist_name = playlist_mappings[(x, y)]
            playlist_id = get_playlist_id_by_name(playlist_name)

            if not playlist_id:
                print(f"Could not find playlist: {playlist_name}")
                return

            # Start playback on the selected device
            spotify.start_playback(
                device_id=device_id,
                context_uri=f'spotify:playlist:{playlist_id}'
            )
            print(f"Playing playlist '{playlist_name}' for button ({x}, {y})")

        except Exception as e:
            print(f"Error playing playlist: {str(e)}")
            if "No active device found" in str(e):
                print("\nTip: Make sure Spotify is open and playing/paused")

def fetch_and_save_playlists():
    if spotify is None:
        print("Spotify not initialized")
        return

    try:
        playlists = []
        results = spotify.current_user_playlists(limit=50)  # Get 50 playlists at a time

        if results is None:
            print("Error: No results returned from Spotify API")
            return None

        total_playlists = results['total']
        print(f"Found {total_playlists} playlists")
        print("Fetching playlist details...")

        while True:
            try:
                for item in results['items']:
                    try:
                        playlist_info = {
                            'name': item['name'],
                            'id': item['id'],
                            'tracks': item['tracks']['total']
                        }
                        playlists.append(playlist_info)
                        print(f"Retrieved: {playlist_info['name']}")
                    except Exception as e:
                        print(f"Error processing playlist: {str(e)}")
                        continue

                if not results['next']:
                    break

                results = spotify.next(results)
                if results is None:
                    print("Warning: Could not fetch next page of playlists")
                    break

            except Exception as e:
                print(f"Error in playlist fetch loop: {str(e)}")
                break

        if playlists:
            print(f"\nWriting {len(playlists)} playlists to file...")
            with open('.playlists', 'w', encoding='utf-8') as f:
                for i, playlist in enumerate(playlists, 1):
                    f.write(f"{i}. {playlist['name']} ({playlist['tracks']} tracks)\n")
                    f.write(f"{playlist['id']}\n")
                    f.write("-------------------------\n")

            print("Successfully saved playlists to .playlists file!")
            return playlists
        else:
            print("No playlists were retrieved successfully")
            return None

    except Exception as e:
        print(f"Error fetching playlists: {str(e)}")
        print("\nTrying to debug Spotify connection...")
        try:
            user = spotify.current_user()
            print(f"Connected as user: {user['display_name']}")
            print(f"User ID: {user['id']}")

            # Test specific playlist access
            try:
                first_playlist = spotify.current_user_playlists(limit=1)
                if first_playlist and first_playlist['items']:
                    print(f"Successfully accessed first playlist: {first_playlist['items'][0]['name']}")
            except Exception as e2:
                print(f"Error accessing first playlist: {str(e2)}")

        except Exception as e2:
            print(f"Error getting user info: {str(e2)}")
            print("Try re-authenticating by deleting the .cache file")
        return None

def color_wipe(midi_out):
    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
    ]

    while should_run and current_animation == 'wipe':
        for color in colors:
            if current_animation != 'wipe':
                break
            for y in range(9):
                for x in range(9):
                    set_color(midi_out, x, y, *color)
                    time.sleep(0.02)
        time.sleep(0.5)

def snake(midi_out):
    snake_body = [(0, 0)]
    direction = (1, 0)  # Start moving right

    while should_run and current_animation == 'snake':
        # Clear the grid
        clear_all(midi_out)

        # Draw snake
        for i, (x, y) in enumerate(snake_body):
            brightness = 255 - (i * 20)  # Fade tail
            if brightness < 0:
                brightness = 0
            set_color(midi_out, x, y, 0, brightness, 0)

        # Move snake head
        head_x, head_y = snake_body[0]
        new_x = (head_x + direction[0]) % 9
        new_y = (head_y + direction[1]) % 9

        # Add new head
        snake_body.insert(0, (new_x, new_y))
        if len(snake_body) > 10:  # Limit snake length
            snake_body.pop()

        # Change direction randomly
        if random.random() < 0.1:  # 10% chance to change direction
            direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])

        time.sleep(0.1)

def fireworks(midi_out):
    while should_run and current_animation == 'fireworks':
        # Launch firework
        center_x = random.randint(2, 6)
        center_y = random.randint(2, 6)
        color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )

        # Explosion animation
        for radius in range(5):
            if current_animation != 'fireworks':
                break
            clear_all(midi_out)

            # Draw explosion
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    x = center_x + dx
                    y = center_y + dy
                    if 0 <= x < 9 and 0 <= y < 9:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if abs(distance - radius) < 1:
                            brightness = 1.0 - (distance / 5)
                            if brightness < 0:
                                brightness = 0
                            r = int(color[0] * brightness)
                            g = int(color[1] * brightness)
                            b = int(color[2] * brightness)
                            set_color(midi_out, x, y, r, g, b)

            time.sleep(0.1)
        time.sleep(0.2)

def rain(midi_out):
    drops = []
    while should_run and current_animation == 'rain':
        # Create new drops
        if random.random() < 0.3:  # 30% chance to create new drop
            drops.append({
                'x': random.randint(0, 8),
                'y': 8,
                'speed': random.uniform(0.2, 0.5)
            })

        # Clear grid
        clear_all(midi_out)

        # Update and draw drops
        new_drops = []
        for drop in drops:
            drop['y'] -= drop['speed']
            if drop['y'] > 0:
                x = int(drop['x'])
                y = int(drop['y'])
                intensity = min(255, int((1.0 - (drop['y'] / 9)) * 255))
                set_color(midi_out, x, y, 0, 0, intensity)
                new_drops.append(drop)

        drops = new_drops
        time.sleep(0.05)

def wave_collision(midi_out):
    center_x = 4  # Center X coordinate (same as rainbow)
    center_y = 4  # Center Y coordinate (same as rainbow)
    grid_width = 9
    grid_height = 9
    phase = 0

    while should_run and current_animation == 'wave':
        for y in range(grid_height):
            for x in range(grid_width):
                # Calculate distances from center
                dx1 = x - center_x
                dy1 = y - center_y
                dx2 = x - (grid_width - center_x - 1)
                dy2 = y - (grid_height - center_y - 1)

                # Create two waves from opposite corners
                dist1 = math.sqrt(dx1*dx1 + dy1*dy1)
                dist2 = math.sqrt(dx2*dx2 + dy2*dy2)

                wave1 = math.sin(phase/10.0 + dist1/2.0)
                wave2 = math.sin(phase/10.0 + dist2/2.0)

                # Combine waves
                combined = (wave1 + wave2) / 2.0

                # Create color based on interference
                intensity = (combined + 1) / 2.0  # Normalize to 0-1
                r = int(255 * intensity * abs(math.sin(phase/25.0)))
                g = int(255 * intensity * abs(math.sin(phase/20.0)))
                b = int(255 * intensity * abs(math.sin(phase/15.0)))

                set_color(midi_out, x, y, r, g, b)

        phase += 1
        time.sleep(0.05)

animations = {
    'rainbow': rainbow_wave,
    'matrix': matrix_rain,
    'pulse': pulse_rings,
    'sparkle': random_sparkle,
    'wipe': color_wipe,
    'snake': snake,
    'fireworks': fireworks,
    'rain': rain,
    'wave': wave_collision
}

def animation_worker():
    midi_out, midi_in = initialize_launchpad()
    global current_animation, should_run

    # Initialize MIDI device with programmer mode
    midi_out.send_message([240, 0, 32, 41, 2, 24, 14, 1, 247])

    try:
        while should_run:
            if current_animation in animations:
                animations[current_animation](midi_out)
            else:
                clear_all(midi_out)
            time.sleep(0.1)
    finally:
        clear_all(midi_out)
        midi_out.close_port()
        midi_in.close_port()

@app.route('/animation/<name>')
def set_animation(name):
    global current_animation
    if name in animations:
        current_animation = name
        return jsonify({'status': 'success', 'animation': name})
    return jsonify({'status': 'error', 'message': 'Animation not found'}), 404

@app.route('/stop')
def stop_animation():
    global current_animation
    current_animation = None
    return jsonify({'status': 'success', 'message': 'Animation stopped'})

@app.route('/list')
def list_animations():
    return jsonify(list(animations.keys()))

@app.route('/devices')
def list_devices():
    if spotify:
        try:
            devices = spotify.devices()
            return jsonify(devices)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Spotify not initialized'}), 500

@app.route('/device/<device_id>')
def select_device(device_id):
    if spotify:
        try:
            spotify.transfer_playback(device_id)
            return jsonify({'success': True, 'message': f'Playback transferred to device {device_id}'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Spotify not initialized'}), 500

@app.route('/')
def index():
    commands = {
        'animations': {
            'description': 'Control LED animations',
            'endpoints': {
                '/animation/<name>': 'Start an animation (available: rainbow, matrix, pulse, sparkle, wipe, snake, fireworks, rain, wave)',
                '/stop': 'Stop current animation',
                '/list': 'List all available animations'
            }
        },
        'spotify': {
            'description': 'Spotify controls',
            'endpoints': {
                '/devices': 'List available Spotify devices',
                '/device/<id>': 'Select Spotify device by ID'
            }
        }
    }

    # Create HTML response
    html = """
    <html>
    <head>
        <title>Launchpad MK2 Controller</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            h2 { color: #666; margin-top: 20px; }
            .endpoint { margin-left: 20px; margin-bottom: 10px; }
            .description { color: #888; }
            code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>Launchpad MK2 Controller API</h1>
    """

    for category, info in commands.items():
        html += f"<h2>{category.title()}</h2>"
        html += f"<p class='description'>{info['description']}</p>"
        for endpoint, desc in info['endpoints'].items():
            html += f"<div class='endpoint'>"
            html += f"<code>{endpoint}</code>: {desc}"
            html += "</div>"

    html += """
    </body>
    </html>
    """

    return html

def print_available_animations():
    print("\nAvailable animations:")
    print("-------------------------")
    for i, anim in enumerate(animations.keys(), 1):
        print(f"{i}. {anim}")
    print("-------------------------")

def print_available_playlists():
    try:
        with open('.playlists', 'r', encoding='utf-8') as f:
            print("\nAvailable playlists:")
            print("-------------------------")
            for line in f:
                if ' tracks)' in line:  # This is a name line
                    print(line.strip())
            print("-------------------------")
    except FileNotFoundError:
        print("Playlist file not found. Please run 'p' command first to fetch playlists.")
    except Exception as e:
        print(f"Error reading playlist file: {str(e)}")

if __name__ == '__main__':
    try:
        # Initialize Spotify
        if not initialize_spotify():
            print("Failed to initialize Spotify. Continuing without Spotify support.")

        # Start animation thread
        animation_thread = threading.Thread(target=animation_worker, daemon=True)
        animation_thread.start()

        print("\nCommands:")
        print("'s' - Show Spotify devices and select active device")
        print("'p' - Fetch and save playlists")
        print("'l' - List available playlists")
        print("'a' - List and start animations")
        print("'x' - Stop current animation")
        print("'q' - Quit")

        # Start Flask server in a separate thread
        flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5125), daemon=True)
        flask_thread.start()

        # Handle keyboard input
        while True:
            cmd = input().lower().strip()
            if cmd == 's':
                show_spotify_devices()
            elif cmd == 'p':
                fetch_and_save_playlists()
            elif cmd == 'l':
                print_available_playlists()
            elif cmd == 'a':
                print_available_animations()
                try:
                    choice = input("\nSelect animation number (or press Enter to cancel): ").strip()
                    if choice:
                        anim_num = int(choice) - 1
                        anim_list = list(animations.keys())
                        if 0 <= anim_num < len(anim_list):
                            current_animation = anim_list[anim_num]
                            print(f"Started animation: {current_animation}")
                        else:
                            print("Invalid animation number!")
                except ValueError:
                    print("Invalid input! Please enter a number.")
            elif cmd == 'x':
                current_animation = None
                print("Animation stopped")
            elif cmd == 'q':
                break

    finally:
        # Cleanup on exit
        should_run = False
        if animation_thread:
            animation_thread.join(timeout=1)