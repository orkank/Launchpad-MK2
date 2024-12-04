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
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import requests
from homebridge import HomebridgeServer
import argparse

app = Flask(__name__)

# Global variables for control
current_animation = None
animation_thread = None
command_queue = Queue()
should_run = True
spotify = None
last_animation = None

def load_playlist_mappings():
    try:
        with open('playlists.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convert string coordinates back to tuples
            mappings = {}
            for coord, info in data['mappings'].items():
                x, y = map(int, coord.split(','))
                mappings[(x, y)] = {
                    'name': info['name'],
                    'animation': info.get('animation')  # Use get() to make animation optional
                }
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
    """Initialize Spotify client with required scopes"""
    try:
        global spotify
        scope = [
            'user-read-playback-state',
            'user-modify-playback-state',
            'user-read-currently-playing',
            'playlist-read-private',
            'playlist-read-collaborative',
            'app-remote-control',
            'streaming',
            'user-read-playback-position',  # Add this scope
            'user-read-recently-played'      # Add this scope
        ]

        with open('.secret', 'r') as f:
            secrets = dict(line.strip().split('=') for line in f if '=' in line)
            client_id = secrets.get('client_id')
            client_secret = secrets.get('client_secret')

        if not client_id or not client_secret:
            print("Missing Spotify credentials in .secret file")
            return False

        spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri='http://localhost:8888/callback',
            scope=' '.join(scope),
            open_browser=True
        ))
        return True

    except Exception as e:
        print(f"Error initializing Spotify: {str(e)}")
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

def check_playlist_file_changed():
    """Check if playlist file has been modified"""
    global playlist_mappings, last_playlist_modified
    try:
        current_mtime = os.path.getmtime('.playlists')
        if not hasattr(check_playlist_file_changed, 'last_mtime'):
            check_playlist_file_changed.last_mtime = current_mtime
        elif current_mtime > check_playlist_file_changed.last_mtime:
            print("\nPlaylist file changed, reloading mappings...")
            playlist_mappings = load_playlist_mappings()
            check_playlist_file_changed.last_mtime = current_mtime
            print("Playlist mappings updated!")
    except Exception as e:
        pass

def format_track_info(track, progress_ms=None):
    """Format track information with time"""
    if not track:
        return "No track playing"

    artists = ", ".join([artist['name'] for artist in track['artists']])
    name = track['name']

    # Format duration
    duration_ms = track['duration_ms']
    duration_min = int(duration_ms / 60000)
    duration_sec = int((duration_ms % 60000) / 1000)

    # Format progress if provided
    if progress_ms is not None:
        progress_min = int(progress_ms / 60000)
        progress_sec = int((progress_ms % 60000) / 1000)
        time_info = f"[{progress_min}:{progress_sec:02d}/{duration_min}:{duration_sec:02d}]"
    else:
        time_info = f"[{duration_min}:{duration_sec:02d}]"

    return f"{artists} - {name} {time_info}"

def get_active_or_default_device():
    """Get active device or set default from .secret"""
    try:
        # Get available devices
        devices = spotify.devices()

        # Find an active device
        device_id = None
        for device in devices['devices']:
            if device['is_active']:
                device_id = device['id']
                break

        # If no active device, use default from .secret
        if not device_id:
            try:
                with open('.secret', 'r') as f:
                    secrets = dict(line.strip().split('=') for line in f if '=' in line)
                    default_device_id = secrets.get('default_device_id')
                    if default_device_id:
                        print(f"No active device found, using default device")
                        spotify.start_playback(device_id=default_device_id)
                        time.sleep(1)  # Wait for device activation
                        device_id = default_device_id
                    else:
                        print("No default device configured in .secret file")
                        return None
            except Exception as e:
                print(f"Error reading default device from .secret: {e}")
                return None

        return device_id
    except Exception as e:
        print(f"Error getting device: {e}")
        return None

def on_midi_message(message, time_stamp):
    """Callback function for MIDI messages"""
    # Track button states
    if not hasattr(on_midi_message, 'button_states'):
        on_midi_message.button_states = {}

    status_byte, note, velocity = message[0]

    # Check for playlist file changes
    check_playlist_file_changed()

    if note >= 104:  # Top row
        x = note - 104
        y = 8
    elif note % 10 == 9:  # Right column
        x = 8
        y = (note - 19) // 10
    else:  # Main grid
        x = (note - 11) % 10
        y = (note - 11) // 10

    button_id = f"{x},{y}"

    # Handle button press and release
    if velocity > 0:  # Button press
        # Skip if button is already pressed
        if button_id in on_midi_message.button_states and on_midi_message.button_states[button_id]:
            return

        # Mark button as pressed
        on_midi_message.button_states[button_id] = True

        print(f"Button pressed - x: {x}, y: {y}, velocity: {velocity}")
        create_explosion_effect(midi_out, x, y)

        # Control buttons (top row)
        if y == 8:
            if x == 0:  # Volume Up
                try:
                    device_id = get_active_or_default_device()
                    if device_id:
                        current = spotify.current_playback()
                        if current and current['device']:
                            volume = min(100, current['device']['volume_percent'] + 10)
                            spotify.volume(volume, device_id=device_id)
                            print(f"Volume up: {volume}%")
                except Exception as e:
                    print(f"Error adjusting volume: {e}")

            elif x == 1:  # Volume Down
                try:
                    device_id = get_active_or_default_device()
                    if device_id:
                        current = spotify.current_playback()
                        if current and current['device']:
                            volume = max(0, current['device']['volume_percent'] - 10)
                            spotify.volume(volume, device_id=device_id)
                            print(f"Volume down: {volume}%")
                except Exception as e:
                    print(f"Error adjusting volume: {e}")

            elif x == 2:  # Previous Track
                try:
                    device_id = get_active_or_default_device()
                    if device_id:
                        spotify.previous_track(device_id=device_id)
                        time.sleep(0.1)
                        current = spotify.current_playback()
                        if current and current['item']:
                            print(f"Previous track: {format_track_info(current['item'], current['progress_ms'])}")
                except Exception as e:
                    print(f"Error: {e}")

            elif x == 3:  # Next Track
                try:
                    device_id = get_active_or_default_device()
                    if device_id:
                        spotify.next_track(device_id=device_id)
                        time.sleep(0.1)
                        current = spotify.current_playback()
                        if current and current['item']:
                            print(f"Next track: {format_track_info(current['item'], current['progress_ms'])}")
                except Exception as e:
                    print(f"Error: {e}")

        else:  # Regular playlist buttons
            play_playlist_for_button(x, y)

    else:  # Button release (velocity = 0)
        # Mark button as released
        on_midi_message.button_states[button_id] = False

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
    """Handle playlist button press"""
    if spotify is None:
        print("Spotify not initialized")
        return

    if (x, y) in playlist_mappings:
        mapping = playlist_mappings[(x, y)]
        playlist_name = mapping['name']

        try:
            # Get available devices
            devices = spotify.devices()

            # Find an active device
            device_id = None
            for device in devices['devices']:
                if device['is_active']:
                    device_id = device['id']
                    break

            # If no active device, use default from .secret
            if not device_id:
                try:
                    with open('.secret', 'r') as f:
                        secrets = dict(line.strip().split('=') for line in f if '=' in line)
                        default_device_id = secrets.get('default_device_id')
                        if default_device_id:
                            print(f"No active device found, using default device")
                            device_id = default_device_id
                        else:
                            print("No default device configured in .secret file")
                            return
                except Exception as e:
                    print(f"Error reading default device from .secret: {e}")
                    return

            # Handle animation if specified
            if 'animation' in mapping and mapping['animation']:
                global current_animation
                if mapping['animation'] in animations:
                    current_animation = mapping['animation']
                    print(f"Changed animation to: {mapping['animation']}")

            # Play the playlist with device_id
            playlist_id = get_playlist_id_by_name(playlist_name)
            if playlist_id:
                spotify.start_playback(
                    device_id=device_id,
                    context_uri=f'spotify:playlist:{playlist_id}'
                )
                # Wait briefly for playback to start
                time.sleep(0.1)
                current = spotify.current_playback()
                if current and current['item']:
                    print(f"Playing: {format_track_info(current['item'], current['progress_ms'])}")
                print(f"Playing playlist: {playlist_name}")
            else:
                print(f"Playlist not found: {playlist_name}")

        except Exception as e:
            print(f"Error playing playlist: {str(e)}")
            if "No active device found" in str(e):
                print("Tip: Make sure Spotify is open on your device")

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

def create_explosion_effect(midi_out, center_x, center_y, color=(255, 255, 255), duration=0.1, max_radius=3):
    """Creates a temporary explosion effect around a pressed key"""
    original_animation = current_animation
    start_time = time.time()

    while time.time() - start_time < duration:
        progress = (time.time() - start_time) / duration
        current_radius = progress * max_radius

        # Store current grid state if there's an animation
        if original_animation:
            # Let the current animation update one frame
            time.sleep(0.01)

        # Draw the explosion effect
        for y in range(max(0, int(center_y - max_radius)), min(9, int(center_y + max_radius + 1))):
            for x in range(max(0, int(center_x - max_radius)), min(9, int(center_x + max_radius + 1))):
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx*dx + dy*dy)

                if distance <= current_radius:
                    # Calculate intensity based on distance and time
                    intensity = (1.0 - distance/max_radius) * (1.0 - progress)
                    r = int(color[0] * intensity)
                    g = int(color[1] * intensity)
                    b = int(color[2] * intensity)

                    set_color(midi_out, x, y, r, g, b)

        time.sleep(0.01)

def temperature_map(midi_out):
    """
    TEMPORARILY DISABLED
    Temperature visualization animation
    Needs further development/testing
    """
    return

    """Display temperature using colors (requires OpenWeatherMap API)"""
    # You'll need to add these to your .secret file
    try:
        with open('.secret', 'r') as f:
            secrets = dict(line.strip().split('=') for line in f if '=' in line)
            API_KEY = secrets.get('weather_api_key')
            CITY_ID = secrets.get('city_id', '2643743')  # Default: London
    except:
        print("Weather API key not found in .secret file")
        return

    while should_run and current_animation == 'temperature':
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?id={CITY_ID}&appid={API_KEY}&units=metric"
            response = requests.get(url)
            data = response.json()
            temp = data['main']['temp']

            # Map temperature to color (blue=-10°C, green=10°C, red=30°C)
            normalized_temp = (temp + 10) / 40  # -10 to 30 range
            if normalized_temp < 0.5:  # Cold
                r, g, b = 0, int(255 * normalized_temp * 2), 255
            else:  # Warm
                r, g, b = 255, int(255 * (1 - (normalized_temp - 0.5) * 2)), 0

            # Display temperature
            for y in range(9):
                for x in range(9):
                    set_color(midi_out, x, y, r, g, b)

            # Show temperature value in corner
            temp_int = int(temp)
            if temp_int < 0:
                set_color(midi_out, 0, 0, 0, 0, 255)  # Blue for negative
            set_color(midi_out, 1, 0, r, g, b)  # Temperature color

        except Exception as e:
            print(f"Weather error: {e}")

        time.sleep(300)  # Update every 5 minutes

def electronic_animation(midi_out):
    """Fast, geometric patterns for electronic music"""
    center_x, center_y = 4, 4  # Center of grid

    while should_run and current_animation == 'electronic':
        # Create expanding squares with rotation
        for size in range(5):
            if current_animation != 'electronic':
                break
            clear_all(midi_out)

            # Draw expanding square with rotation
            angle = time.time() * 2  # Rotation angle
            for i in range(size + 1):
                for offset in range(8):
                    # Calculate rotated corner positions
                    x = center_x + i * math.cos(angle + offset * math.pi/4)
                    y = center_y + i * math.sin(angle + offset * math.pi/4)

                    # Convert to grid coordinates
                    grid_x = int(round(x))
                    grid_y = int(round(y))

                    if 0 <= grid_x < 9 and 0 <= grid_y < 9:
                        # Create color cycling effect
                        hue = (time.time() / 2 + i / 5) % 1.0
                        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
                        set_color(midi_out, grid_x, grid_y, r, g, b)

            time.sleep(0.1)

def classical_animation(midi_out):
    """Smooth, flowing waves for classical music"""
    while should_run and current_animation == 'classical':
        phase = time.time() * 2
        for y in range(9):
            for x in range(9):
                # Create gentle sine wave pattern
                wave = math.sin(phase + (x + y) / 4.0) * 0.5 + 0.5
                r = int(wave * 100)  # Soft red
                g = int(wave * 150)  # Medium green
                b = int(wave * 255)  # Strong blue
                set_color(midi_out, x, y, r, g, b)
        time.sleep(0.05)

def rock_animation(midi_out):
    """Aggressive, flashing patterns for rock music"""
    patterns = [
        # Diagonal strikes
        [(x, x) for x in range(9)] + [(x, 8-x) for x in range(9)],
        # X pattern
        [(0,0), (1,1), (2,2), (3,3), (4,4), (5,5), (6,6), (7,7), (8,8),
         (0,8), (1,7), (2,6), (3,5), (4,4), (5,3), (6,2), (7,1), (8,0)],
        # Border flash
        [(x, 0) for x in range(9)] + [(x, 8) for x in range(9)] +
        [(0, y) for y in range(1, 8)] + [(8, y) for y in range(1, 8)],
        # Random explosion pattern
        [(random.randint(0, 8), random.randint(0, 8)) for _ in range(20)]
    ]

    while should_run and current_animation == 'rock':
        for pattern in patterns:
            if current_animation != 'rock':
                break

            # Flash pattern in red/orange
            for intensity in [255, 100, 255, 50]:  # More varied intensity
                clear_all(midi_out)
                for x, y in pattern:
                    # Add some random variation to make it more dynamic
                    r = min(255, intensity + random.randint(-20, 20))
                    g = min(255, intensity//3 + random.randint(-10, 10))
                    b = min(255, intensity//6 + random.randint(-5, 5))
                    set_color(midi_out, x, y, r, g, b)
                time.sleep(0.05)

            # Add random sparks
            for _ in range(3):
                x, y = random.randint(0, 8), random.randint(0, 8)
                set_color(midi_out, x, y, 255, 200, 0)  # Bright flash
                time.sleep(0.02)

            time.sleep(0.1)

def jazz_animation(midi_out):
    """Complex, evolving patterns for jazz music"""
    points = [(random.randint(0, 8), random.randint(0, 8)) for _ in range(5)]
    colors = [(random.randint(100, 255), random.randint(50, 150), random.randint(0, 100))
              for _ in range(5)]

    while should_run and current_animation == 'jazz':
        clear_all(midi_out)

        # Smooth movement of light points
        for i in range(len(points)):
            x, y = points[i]
            r, g, b = colors[i]

            # Draw smooth gradient around each point
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < 9 and 0 <= new_y < 9:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance < 2:
                            intensity = (2 - distance) / 2
                            set_color(midi_out, new_x, new_y,
                                    int(r * intensity),
                                    int(g * intensity),
                                    int(b * intensity))

            # Slowly move points
            points[i] = ((x + random.uniform(-0.2, 0.2)) % 9,
                        (y + random.uniform(-0.2, 0.2)) % 9)

        time.sleep(0.05)

def ambient_animation(midi_out):
    """Slow, peaceful patterns for ambient music"""
    while should_run and current_animation == 'ambient':
        phase = time.time() * 0.5
        for y in range(9):
            for x in range(9):
                # Create very slow moving color pattern
                hue = (math.sin(phase + x/5.0) * math.cos(phase + y/5.0) + 1) / 2
                r, g, b = [int(c * 100) for c in colorsys.hsv_to_rgb(hue, 0.5, 0.8)]
                set_color(midi_out, x, y, r, g, b)
        time.sleep(0.1)

def get_current_audio_features():
    """Get audio features for currently playing track"""
    try:
        current = spotify.current_playback()
        if current and current['item']:
            track_id = current['item']['id']
            features = spotify.audio_features([track_id])[0]
            return features
        return None
    except Exception as e:
        print(f"Error getting audio features: {e}")
        return None

def equalizer_animation(midi_out):
    """Equalizer visualization based on Spotify audio features"""
    last_track_id = None

    while should_run and current_animation == 'equalizer':
        try:
            current = spotify.current_playback()
            if not current or not current['is_playing']:
                # Show idle animation when not playing
                clear_all(midi_out)
                for x in range(9):
                    height = int(2 + math.sin(time.time() * 2 + x/2) * 2)
                    for y in range(height):
                        set_color(midi_out, x, y, 0, 255, 100)
                time.sleep(0.1)
                continue

            track_id = current['item']['id']

            # Print track info when track changes
            if track_id != last_track_id:
                print(f"Now playing: {format_track_info(current['item'], current['progress_ms'])}")
                last_track_id = track_id

                # Get new features when track changes
                features = get_current_audio_features()
                if not features:
                    continue

                # Extract relevant features
                energy = features['energy']
                danceability = features['danceability']
                valence = features['valence']
                tempo = features['tempo']

                # Clear grid
                clear_all(midi_out)

                # Create visualization based on features
                # Energy (columns 0-2)
                height = int(energy * 8)
                for x in range(3):
                    for y in range(height):
                        set_color(midi_out, x, y, 255, 0, 0)  # Red for energy

                # Danceability (columns 3-5)
                height = int(danceability * 8)
                for x in range(3, 6):
                    for y in range(height):
                        set_color(midi_out, x, y, 0, 255, 0)  # Green for danceability

                # Valence (columns 6-8)
                height = int(valence * 8)
                for x in range(6, 9):
                    for y in range(height):
                        set_color(midi_out, x, y, 0, 0, 255)  # Blue for valence

                # Add some animation based on tempo
                pulse_time = time.time() * (tempo / 60)  # Pulses per second
                pulse = (math.sin(pulse_time) + 1) / 2  # 0 to 1

                # Add pulsing overlay
                for x in range(9):
                    for y in range(8):
                        if midi_out:  # If LED is already lit
                            r, g, b = 255, 255, 255
                            intensity = pulse * 0.3  # 30% max intensity
                            set_color(midi_out, x, y,
                                    int(r * intensity),
                                    int(g * intensity),
                                    int(b * intensity))

            time.sleep(0.05)  # Adjust for smoothness

        except Exception as e:
            print(f"Equalizer error: {e}")
            time.sleep(1)

def get_playlist_animation(playlist_id):
    """Get animation for playlist if configured"""
    try:
        playlist = spotify.playlist(playlist_id)
        playlist_name = playlist['name']

        # Check if this playlist exists in our mappings
        for coord, mapping in playlist_mappings.items():
            if mapping['name'] == playlist_name and 'animation' in mapping:
                return mapping['animation']
    except Exception as e:
        print(f"Error getting playlist animation: {e}")
    return None

def spotify_status_monitor():
    """Monitor Spotify status changes"""
    global should_run, last_animation
    last_track_id = None
    last_is_playing = None
    last_playlist_id = None

    while should_run:
        global current_animation

        try:
            current = spotify.current_playback()

            if current:
                # Track change detection
                track_id = current['item']['id'] if current['item'] else None
                if track_id != last_track_id:
                    last_track_id = track_id
                    if current['item']:
                        print(f"Now playing: {format_track_info(current['item'], current['progress_ms'])}")

                # Play/Pause state change
                is_playing = current['is_playing']
                if is_playing != last_is_playing:
                    last_is_playing = is_playing
                    print(f"Playback {'resumed' if is_playing else 'paused'}")
                if not is_playing:
                    current_animation = None
                else:
                    current_animation = last_animation


                # Playlist change detection
                context = current.get('context')
                if context and context['type'] == 'playlist':
                    playlist_id = context['uri'].split(':')[-1]
                    if playlist_id != last_playlist_id:
                        last_playlist_id = playlist_id
                        # Get playlist name
                        try:
                            playlist = spotify.playlist(playlist_id)
                            print(f"Current playlist: {playlist['name']}")

                            # Handle animation if specified
                            playlist_animation = get_playlist_animation(playlist_id)
                            if playlist_animation:
                                if playlist_animation in animations:
                                    last_animation = current_animation = playlist_animation
                                    print(f"Changed animation to: {playlist_animation}")
                        except:
                            pass

            time.sleep(1)  # Poll every second

        except Exception as e:
            print(f"Status monitor error: {e}")
            time.sleep(5)  # Wait longer on error

animations = {
    'rainbow': rainbow_wave,
    'matrix': matrix_rain,
    'pulse': pulse_rings,
    'sparkle': random_sparkle,
    'wipe': color_wipe,
    'snake': snake,
    'fireworks': fireworks,
    'rain': rain,
    'wave': wave_collision,
    'equalizer': equalizer_animation,
    # 'temperature': temperature_map,

    # Genre-based animations
    'electronic': electronic_animation,
    'classical': classical_animation,
    'rock': rock_animation,
    'jazz': jazz_animation,
    'ambient': ambient_animation,
}

def animation_worker():
    midi_out, midi_in = initialize_launchpad()
    global current_animation, should_run, last_animation

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
        last_animation = current_animation = name
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
                '/animation/<name>': 'Start an animation (available: rainbow, matrix, pulse, sparkle, wipe, snake, fireworks, rain, wave, temperature, electronic, classical, rock, jazz, ambient)',
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

def setup_playlist_watcher():
    try:
        event_handler = PlaylistFileHandler()
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=False)
        observer.daemon = True  # Make sure the observer thread is daemonic
        observer.start()
        return observer
    except Exception as e:
        print(f"Warning: Could not setup playlist watcher: {e}")
        return None

if __name__ == '__main__':
    try:
        # Initialize Spotify
        if not initialize_spotify():
            print("Failed to initialize Spotify. Continuing without Spotify support.")

        # Load initial playlist mappings
        playlist_mappings = load_playlist_mappings()

        # Initialize MIDI before starting watchers
        midi_out, midi_in = initialize_launchpad()

        # Start playlist file watcher in try-except block
        try:
            playlist_observer = setup_playlist_watcher()
        except Exception as e:
            print(f"Warning: Playlist watcher not started: {e}")
            playlist_observer = None

        # Start animation thread
        animation_thread = threading.Thread(target=animation_worker, daemon=True)
        animation_thread.start()

        # Start status monitor thread
        status_thread = threading.Thread(target=spotify_status_monitor, daemon=True)
        status_thread.start()
        print("Spotify status monitor started")


        parser = argparse.ArgumentParser(description='Launchpad MK2 Spotify Controller')
        parser.add_argument('--homebridge', action='store_true', help='Start Homebridge server')
        args = parser.parse_args()

        # Start Homebridge server
        if args.homebridge:
            homebridge = HomebridgeServer(spotify, animations)
            homebridge.start()
            print("Homebridge server started on port 3000")

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
                            last_animation = current_animation = anim_list[anim_num]
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
        if 'playlist_observer' in locals() and playlist_observer:
            playlist_observer.stop()
            playlist_observer.join()