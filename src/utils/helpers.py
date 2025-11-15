"""Helper utility functions."""


def print_available_animations(animations_dict):
    """Print available animations in a formatted list.

    Args:
        animations_dict: Dictionary of available animations
    """
    print("\nAvailable animations:")
    print("-------------------------")
    for i, anim in enumerate(animations_dict.keys(), 1):
        print(f"{i}. {anim}")
    print("-------------------------")


def print_available_playlists():
    """Print available playlists from the playlists file."""
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
