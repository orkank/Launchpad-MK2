"""Spotify integration and management."""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time


class SpotifyManager:
    """Manages Spotify client and related operations."""

    def __init__(self):
        self.spotify = None

    def initialize(self):
        """Initialize Spotify client with required scopes."""
        return initialize_spotify()

    def get_devices(self):
        """Get available Spotify devices."""
        if not self.spotify:
            return None
        try:
            return self.spotify.devices()
        except Exception as e:
            print(f"Error getting devices: {e}")
            return None

    def get_current_playback(self):
        """Get current playback information."""
        if not self.spotify:
            return None
        try:
            return self.spotify.current_playback()
        except Exception as e:
            print(f"Error getting playback: {e}")
            return None


def initialize_spotify():
    """Initialize Spotify client with required scopes.

    Returns:
        spotipy.Spotify: Initialized Spotify client or None on failure
    """
    try:
        scope = [
          'user-read-playback-state',
          'user-modify-playback-state',
          'user-read-currently-playing',
          'playlist-read-private',
          'playlist-read-collaborative',
          'app-remote-control',
          'streaming',
          'user-read-playback-position',
          'user-read-recently-played'
        ]

        with open('config/.secret', 'r') as f:
            secrets = dict(line.strip().split('=') for line in f if '=' in line)
            client_id = secrets.get('client_id')
            client_secret = secrets.get('client_secret')

        if not client_id or not client_secret:
            print("Missing Spotify credentials in .secret file")
            return None

        spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri='http://localhost:8888/callback',
            scope=' '.join(scope),
            open_browser=True
        ))
        return spotify

    except Exception as e:
        print(f"Error initializing Spotify: {str(e)}")
        return None


def show_spotify_devices(spotify):
    """Display available Spotify devices and allow selection.

    Args:
        spotify: Spotify client instance
    """
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


def get_current_audio_features(spotify):
    """Get audio features for currently playing track.

    Args:
        spotify: Spotify client instance

    Returns:
        dict: Audio features or None
    """
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


def format_track_info(track, progress_ms=None):
    """Format track information with time.

    Args:
        track: Spotify track object
        progress_ms: Current progress in milliseconds

    Returns:
        str: Formatted track information
    """
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


def get_active_or_default_device(spotify):
    """Get active device, default device, or first available device.

    Args:
        spotify: Spotify client instance

    Returns:
        str: Device ID or None
    """
    try:
        # Get available devices
        devices = spotify.devices()

        if not devices or 'devices' not in devices or not devices['devices']:
            print("No Spotify devices found")
            return None

        # First try to find an active device
        device_id = None
        for device in devices['devices']:
            if device['is_active']:
                device_id = device['id']
                print(f"Using active device: {device['name']}")
                break

        # If no active device, try to use default from .secret
        if not device_id:
            try:
                with open('config/.secret', 'r') as f:
                    secrets = dict(line.strip().split('=') for line in f if '=' in line)
                    default_device_id = secrets.get('default_device_id')
                    if default_device_id:
                        print(f"Using default device from .secret")
                        spotify.start_playback(device_id=default_device_id)
                        time.sleep(1)  # Wait for device activation
                        device_id = default_device_id
            except Exception as e:
                print(f"Could not use default device: {e}")

        # If still no device, use the first available one
        if not device_id and devices['devices']:
            first_device = devices['devices'][0]
            device_id = first_device['id']
            print(f"No active or default device found. Using first available device: {first_device['name']}")
            spotify.start_playback(device_id=device_id)
            time.sleep(2)  # Wait for device activation

        return device_id

    except Exception as e:
        print(f"Error getting device: {e}")
        return None


def fetch_and_save_playlists(spotify):
    """Fetch user playlists from Spotify and save to file.

    Args:
        spotify: Spotify client instance

    Returns:
        list: List of playlists or None on failure
    """
    if spotify is None:
        print("Spotify not initialized")
        return

    try:
        playlists = []
        results = spotify.current_user_playlists(limit=50)

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
