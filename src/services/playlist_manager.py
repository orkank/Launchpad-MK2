"""Playlist mapping and management."""

import json
import os
import random
import threading
import sys
import time
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.text import Text


def load_playlist_mappings():
    """Load playlist mappings from configuration file.

    Returns:
        dict: Playlist mappings dictionary
    """
    try:
        with open('config/playlists.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convert string coordinates back to tuples
            mappings = {}
            for coord, info in data['mappings'].items():
                x, y = map(int, coord.split(','))
                mappings[(x, y)] = {
                    'name': info['name'],
                    'animation': info.get('animation')
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


def show_loading_message():
    """Show an animated loading message in a separate thread."""
    loading_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    while show_loading_message.is_loading:
        sys.stdout.write(f'\rGenerating playlist mappings... {loading_chars[i]} ')
        sys.stdout.flush()
        time.sleep(0.1)
        i = (i + 1) % len(loading_chars)
    sys.stdout.write('\r' + ' ' * 50 + '\r')  # Clear the loading message
    sys.stdout.flush()


def generate_playlist_mappings(spotify, animations_dict, filter_type='newest'):
    """Generate playlist mappings automatically from Spotify.

    Args:
        spotify: Spotify client instance
        animations_dict: Dictionary of available animations
        filter_type: 'newest', 'popular', or 'all'
    """
    if spotify is None:
        print("Spotify not initialized")
        return

    # Start loading animation
    show_loading_message.is_loading = True
    loading_thread = threading.Thread(target=show_loading_message)
    loading_thread.daemon = True
    loading_thread.start()

    try:
        # Load existing mappings
        existing_mappings = {}
        if os.path.exists('config/playlists.json'):
            with open('config/playlists.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_mappings = data.get('mappings', {})

        print("\nLoading existing mappings...")

        # Get all used coordinates
        used_coords = set()
        for coord_str in existing_mappings:
            x, y = map(int, coord_str.split(','))
            used_coords.add((x, y))

        # Get available coordinates (excluding top row which is for controls)
        available_coords = []
        for y in range(8):  # 0-7 (excluding top row)
            for x in range(8):  # 0-7 (excluding rightmost column)
                if (x, y) not in used_coords:
                    available_coords.append((x, y))

        if not available_coords:
            # Stop loading animation
            show_loading_message.is_loading = False
            loading_thread.join()
            print("No available coordinates for new mappings!")
            return

        # Get list of animations for random selection (excluding equalizer_microphone)
        available_animations = [anim for anim in animations_dict.keys()
                              if anim != 'equalizer_microphone']

        # Get user's playlists
        playlists = []
        results = spotify.current_user_playlists(limit=50)

        while results:
            for item in results['items']:
                # Skip playlists that are already mapped
                playlist_name = item['name'].encode('utf-8').decode('utf-8')
                if not any(mapping['name'] == playlist_name for mapping in existing_mappings.values()):
                    playlist_info = {
                        'name': playlist_name,
                        'id': item['id'],
                        'tracks': item['tracks']['total'],
                        'owner': item['owner']['id'],
                        'added_at': datetime.now(timezone.utc).isoformat(),
                    }

                    # Get additional details for filtering
                    if filter_type == 'popular':
                        try:
                            playlist_details = spotify.playlist(item['id'])
                            playlist_info['followers'] = playlist_details['followers']['total']
                        except:
                            playlist_info['followers'] = 0

                    playlists.append(playlist_info)

            if results['next']:
                results = spotify.next(results)
            else:
                break

        # Sort playlists based on filter type
        if filter_type == 'newest':
            playlists.sort(key=lambda x: x['added_at'], reverse=True)
        elif filter_type == 'popular':
            playlists.sort(key=lambda x: x.get('followers', 0), reverse=True)

        # Map new playlists to available coordinates
        new_mappings = {}
        for playlist in playlists:
            if not available_coords:
                break

            coord = available_coords.pop(0)
            coord_str = f"{coord[0]},{coord[1]}"
            new_mappings[coord_str] = {
                'name': playlist['name'],
                'animation': random.choice(available_animations)
            }

        # Merge with existing mappings
        merged_mappings = {**existing_mappings, **new_mappings}

        # Save updated mappings with proper UTF-8 encoding
        print("\nSaving new mappings...")
        with open('config/playlists.json', 'w', encoding='utf-8') as f:
            json.dump({'mappings': merged_mappings}, f, indent=2, ensure_ascii=False)

        # Stop loading animation
        show_loading_message.is_loading = False
        loading_thread.join()

        print(f"\nAdded {len(new_mappings)} new playlist mappings:")
        for coord, mapping in new_mappings.items():
            print(f"Coordinate {coord}: {mapping['name']} (Animation: {mapping['animation']})")

    except Exception as e:
        # Stop loading animation on error
        show_loading_message.is_loading = False
        loading_thread.join()
        print(f"\nError generating playlist mappings: {e}")


def randomize_animations(animations_dict):
    """Randomly assign animations to all playlists in playlists.json.

    Args:
        animations_dict: Dictionary of available animations
    """
    try:
        # Load existing mappings
        with open('config/playlists.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            mappings = data.get('mappings', {})

        if not mappings:
            print("No playlist mappings found!")
            return

        # Get list of available animations (excluding equalizer_microphone)
        available_animations = [anim for anim in animations_dict.keys()
                              if anim != 'equalizer_microphone']

        # Count of changes made
        changes = 0

        # Assign random animations
        for coord, mapping in mappings.items():
            old_animation = mapping.get('animation')
            new_animation = random.choice(available_animations)

            # Update animation
            mapping['animation'] = new_animation

            if old_animation != new_animation:
                changes += 1
                print(f"Changed {mapping['name']}: {old_animation or 'None'} → {new_animation}")

        # Save updated mappings
        with open('config/playlists.json', 'w', encoding='utf-8') as f:
            json.dump({'mappings': mappings}, f, indent=2, ensure_ascii=False)

        print(f"\nUpdated {changes} animations in playlist mappings!")

    except Exception as e:
        print(f"Error randomizing animations: {e}")


def get_playlist_id_by_name(playlist_name):
    """Get playlist ID by name from the playlists file.

    Args:
        playlist_name: Name of the playlist

    Returns:
        str: Playlist ID or None if not found
    """
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


def show_playlist_animation_preview(mappings=None, format_type='table'):
    """Show playlist-animation mappings in a formatted table or JSON.

    Args:
        mappings: Dictionary of playlist mappings (loads from file if None)
        format_type: 'table' for Rich table display, 'json' for JSON format

    Returns:
        dict: Mappings in JSON format if format_type is 'json'
    """
    if mappings is None:
        mappings = load_playlist_mappings()

    if not mappings:
        if format_type == 'table':
            console = Console()
            console.print("📭 [yellow]No playlist mappings found![/yellow]")
            console.print("💡 [dim]Use 'g' command to generate mappings or manually edit config/playlists.json[/dim]")
        return {}

    if format_type == 'json':
        # Convert tuple keys to strings for JSON serialization
        json_mappings = {}
        for (x, y), mapping in mappings.items():
            json_mappings[f"{x},{y}"] = {
                'coordinates': [x, y],
                'playlist': mapping['name'],
                'animation': mapping.get('animation', 'None')
            }
        return json_mappings

    # Rich table display
    console = Console()
    table = Table(title="🎵 Playlist ↔ Animation Mappings", show_header=True, header_style="bold magenta")

    table.add_column("📍 Position", style="cyan", width=12)
    table.add_column("🎵 Playlist", style="green", width=40, no_wrap=False)
    table.add_column("✨ Animation", style="yellow", width=20)
    table.add_column("🎯 Status", style="blue", width=12)

    # Sort by coordinates for consistent display
    sorted_mappings = sorted(mappings.items(), key=lambda x: (x[0][1], x[0][0]))

    for (x, y), mapping in sorted_mappings:
        # Truncate long playlist names
        playlist_name = mapping['name']
        if len(playlist_name) > 38:
            playlist_name = playlist_name[:35] + "..."

        animation = mapping.get('animation', 'None')

        # Status indicator
        if animation and animation != 'None':
            status = "✅ Mapped"
            status_style = "green"
        else:
            status = "⚠️ No Anim"
            status_style = "yellow"

        table.add_row(
            f"({x},{y})",
            Text(playlist_name, overflow="ellipsis"),
            animation or "None",
            Text(status, style=status_style)
        )

    console.print(table)
    console.print(f"\n📊 [bold]Total: {len(mappings)} playlists mapped[/bold]")

    # Show grid utilization
    total_slots = 64  # 8x8 grid
    utilization = (len(mappings) / total_slots) * 100
    console.print(f"🎯 [bold]Grid utilization: {utilization:.1f}% ({len(mappings)}/{total_slots} slots)[/bold]")

    return mappings


class PlaylistManager:
    """Manages playlist mappings and operations."""

    def __init__(self, spotify_client=None):
        self.spotify = spotify_client
        self.mappings = {}
        self.load_mappings()

    def load_mappings(self):
        """Load playlist mappings from file."""
        self.mappings = load_playlist_mappings()

    def save_mappings(self):
        """Save current mappings to file."""
        # Convert tuple keys back to string format for JSON
        string_mappings = {}
        for (x, y), mapping in self.mappings.items():
            string_mappings[f"{x},{y}"] = mapping

        with open('config/playlists.json', 'w', encoding='utf-8') as f:
            json.dump({'mappings': string_mappings}, f, indent=2, ensure_ascii=False)

    def get_mapping(self, x, y):
        """Get mapping for specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            dict: Mapping info or None
        """
        return self.mappings.get((x, y))

    def set_mapping(self, x, y, name, animation=None):
        """Set mapping for specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            name: Playlist name
            animation: Animation name (optional)
        """
        self.mappings[(x, y)] = {
            'name': name,
            'animation': animation
        }

    def show_preview(self, format_type='table'):
        """Show playlist-animation preview.

        Args:
            format_type: 'table' for Rich table display, 'json' for JSON format

        Returns:
            dict: Mappings in JSON format if format_type is 'json'
        """
        return show_playlist_animation_preview(self.mappings, format_type)
