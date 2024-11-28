# Launchpad MK2 Spotify Controller

Control your Spotify playback using a Novation Launchpad MK2. Features include playlist control, device selection, and LED animations.

## Getting Started

### Prerequisites

1. Python 3.6 or higher
2. Novation Launchpad MK2 (tested on MK2+)
3. Spotify Premium account
4. Spotify Developer account

### Installation

1. Install required Python packages:

```bash
pip install rtmidi flask spotipy
```

### Configuration

1. Configure your playlist mappings in the script:

To map playlists to buttons, edit the `playlist_mappings` dictionary in the script:

```python
playlist_mappings = {
# Format: (x, y): 'playlist_name'
(0, 7): 'dream catcher',
(0, 0): 'Trip',
# Add more mappings as needed
}
```

## Launchpad Key Mapping

### Grid Layout
The Launchpad MK2 has a 9x9 grid of buttons (including the top row and right column). The coordinates are mapped as follows:

```
   0   1   2   3   4   5   6   7   8  (x)
0  □   □   □   □   □   □   □   □   ▷
1  □   □   □   □   □   □   □   □   ▷
2  □   □   □   □   □   □   □   □   ▷
3  □   □   □   □   □   □   □   □   ▷
4  □   □   □   □   □   □   □   □   ▷
5  □   □   □   □   □   □   □   □   ▷
6  □   □   □   □   □   □   □   □   ▷
7  □   □   □   □   □   □   □   □   ▷
8  ▽   ▽   ▽   ▽   ▽   ▽   ▽   ▽   ⬚
(y)
```
- Main grid: (0,0) to (7,7)
- Top row: (0,8) to (7,8)
- Right column: (8,0) to (8,7)
- Top-right corner: (8,8)

## Running the Script

1. Connect your Launchpad MK2 to your computer
2. Open Spotify on your computer
3. Run the script:

```bash
python mk2.py
```

4. On first run:
   - The script will open your browser for Spotify authentication
   - Log in to your Spotify account
   - Grant the requested permissions
   - Copy the URL from the browser and paste it into the script (it will be in the form of http://localhost:5125/callback?code=...)
   - Callback URI doesnt matter, just use http://localhost:5125/callback.

## Commands

## Commands

| Command | Description |
|---------|-------------|
| `s` | Show and select available Spotify devices |
| `p` | Fetch and save your Spotify playlists to `.playlists` file |
| `l` | List all available playlists |
| `a` | List and start animations |
| `x` | Stop current animation |
| `q` | Quit the application |

### Available Animations
- `rainbow` - Rainbow wave pattern
- `matrix` - Matrix-style falling characters
- `pulse` - Pulsing rings of light
- `sparkle` - Random twinkling lights
- `wipe` - Color wipe transitions
- `snake` - Moving snake pattern
- `fireworks` - Exploding firework effects
- `rain` - Falling rain effect
- `wave` - Colliding wave patterns

You can start animations either through:
1. Command line: Use 'a' to list and select animations
2. Web interface: Visit `http://localhost:5125/animation/<name>`
3. Stop any running animation with the 'x' command
## Web Interface

The script runs a web server on port 5125 with the following endpoints:

- `/animation/<name>` - Start an animation
- `/stop` - Stop current animation
- `/list` - List available animations

Available animations:
- rainbow
- matrix
- pulse
- sparkle
- wipe
- snake
- fireworks
- rain
- wave

## Launchpad Layout

- Top-right button (8,8): Show Spotify devices
- Other buttons: Play mapped playlists (according to playlist_mappings)

## Troubleshooting

1. If you get "No MIDI ports found":
   - Open 'Audio MIDI Setup' application
   - Go to Window > Show MIDI Studio
   - Check if Launchpad MK2 is visible and enabled
   - Try unplugging and replugging the Launchpad

2. If you get Spotify authentication errors:
   - Delete the `.cache` file
   - Run the script again
   - Go through the authentication process

3. If playlists don't play:
   - Make sure Spotify is open and active
   - Verify the device selection using the 's' command
   - Check playlist names match exactly using the 'l' command

## Files

- `mk2.py` - Main script
- `.playlists` - Cached playlist information
- `.cache` - Spotify authentication cache

## Notes

- Requires Spotify Premium for playback control
- Playlist names are case-insensitive but must otherwise match exactly
- The script must be run from a terminal that can handle input commands