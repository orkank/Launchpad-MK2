# Launchpad MK2 Spotify Controller

This project was created to repurpose an old Novation Launchpad MK2 as a Spotify controller. The script allows you to control Spotify playback and create LED animations through both direct interaction and HTTP requests, enabling integration with other applications.

![Launchpad MK2 Spotify Controller](https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3oxZHc3eWN4YTJvcDRxN2hveHpvYmo2a24waWg0eXhucWhoNWJ2cSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Zmjxih3FL25oKoTLjC/giphy.gif)

## Disclaimer
- This is a personal project created for my own use with an old Launchpad MK2
- Use this script at your own risk
- No warranty or guarantee is provided
- The code and documentation may have conflicts or inconsistencies
- If you encounter issues, please open a GitHub issue for discussion

### Features
- Spotify playlist control through Launchpad buttons
- LED animations controllable via HTTP requests
- Device selection for Spotify playback
- Customizable playlist mappings

## Table of Contents
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Spotify Developer Setup](#spotify-developer-setup)
- [Configuration](#configuration)
  - [Playlist Configuration](#playlist-configuration)
- [Running the Script](#running-the-script)
- [Commands](#commands)
  - [Available Animations](#available-animations)
- [Web Interface](#web-interface)
- [Launchpad Layout](#launchpad-layout)
  - [Grid Reference](#grid-reference)
  - [Control Buttons](#control-buttons)
- [System Requirements & Compatibility](#system-requirements--compatibility)
  - [Tested Environment](#tested-environment)
  - [Important Notes](#important-notes)
  - [macOS Setup](#macos-setup)
  - [Known Issues](#known-issues)
- [Troubleshooting](#troubleshooting)
- [Files](#files)
- [Notes](#notes)
- [Running as a Service (macOS)](#running-as-a-service-macos)

## Getting Started

### Prerequisites

1. Python 3.6 or higher
2. Novation Launchpad MK2 (tested on MK2+)
3. Spotify Premium account
4. Spotify Developer account

### Installation

1. Install required Python packages:

```bash
pip install rtmidi flask spotipy watchdog
```

## Spotify Developer Setup

1. Create a Spotify Developer Account:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Log in with your Spotify account

2. Create a New Application:
   - Click "Create an App" button
   - Fill in the application details:
     - App name: (e.g., "Launchpad Controller")
     - App description: (e.g., "Launchpad MK2 Spotify Controller")
     - Redirect URI: `http://localhost:8888/callback`
   - Click "Create"

3. Get Your Credentials:
   - Once created, you'll see your app in the dashboard
   - Click on your app to view settings
   - Note down the following:
     - Client ID
     - Client Secret (click "View Client Secret" to reveal)

4. Create `.secret` file:
   - Create a file named `.secret` in the same directory as the script
   - Add your credentials in this format:
```
client_id=YOUR_CLIENT_ID
client_secret=YOUR_CLIENT_SECRET
```
   - Save the file
   - Note: Never share or commit your `.secret` file!

5. Required Spotify Permissions:
   - Your app needs the following scopes:
     - `user-modify-playback-state`
     - `user-read-playback-state`
     - `playlist-read-private`
   - These are automatically requested during authentication

[Source: Spotify Web API Getting Started Guide](https://developer.spotify.com/documentation/web-api/tutorials/getting-started)

## Configuration

### Playlist Configuration

Playlists are configured in `playlists.json`. The format is:

```json
{
    "mappings": {
        "x,y": {
            "name": "exact_playlist_name",
            "description": "Optional description"
        }
    }
}
```

Example configuration:
```json
{
    "mappings": {
        "0,7": {
            "name": "dream catcher",
            "description": "Bottom-left - Chill vibes"
        },
        "0,0": {
            "name": "Trip",
            "description": "Top-left - Travel playlist"
        }
    }
}
```

Coordinate Reference:
- x: 0-8 (left to right)
- y: 0-8 (top to bottom)
- Example: "0,7" is bottom-left corner

To configure:
1. Use 'l' command to list available playlists
2. Copy exact playlist names
3. Edit playlists.json
4. Restart the script to load new mappings

Tips:
- Keep playlist names exactly as they appear in Spotify
- Use descriptions to remember what each button does

## Playlist Configuration

### playlists.json Format
The `playlists.json` file maps Launchpad buttons to Spotify playlists and optional animations. Each mapping contains:
- `name`: The exact name of your Spotify playlist
- `animation` (optional): The animation to play when this playlist starts

Example configuration:
```json
{
    "mappings": {
        "0,7": {
            "name": "My Workout Mix",
            "animation": "rainbow"
        },
        "1,7": {
            "name": "Chill Vibes",
            "animation": "pulse"
        },
        "2,7": {
            "name": "Party Playlist"
            // No animation specified - will keep current animation
        }
    }
}
```

Available animations:
- `rainbow`: Color wave effect
- `matrix`: Matrix-style falling effect
- `pulse`: Pulsing rings
- `sparkle`: Random sparkling lights
- `wipe`: Color wipe effect
- `snake`: Moving snake pattern
- `fireworks`: Firework explosions
- `rain`: Falling rain effect
- `wave`: Wave collision pattern

The animation will automatically change when you start the playlist. If no animation is specified, the current animation will continue playing.

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

The script runs a web server on port 5125. Visit `http://localhost:5125` in your browser to see all available commands.

### Available Endpoints

#### Animations
- `GET /` - Show all available commands and documentation
- `GET /animation/<name>` - Start an animation
- `GET /stop` - Stop current animation
- `GET /list` - List available animations

#### Spotify Control
- `GET /devices` - List available Spotify devices
- `GET /device/<id>` - Select Spotify device by ID

### Example Usage
```bash
# List available animations
curl http://localhost:5125/list

# Start rainbow animation
curl http://localhost:5125/animation/rainbow

# Stop current animation
curl http://localhost:5125/stop

# List Spotify devices
curl http://localhost:5125/devices
```

## Launchpad Layout

### Grid Reference
The Launchpad MK2 has a 9x9 grid of buttons (including the top row and right column). The coordinates are mapped as follows:

```
   0   1   2   3   4   5   6   7   8  (x)
7  □   □   □   □   □   □   □   □   ▷
6  □   □   □   □   □   □   □   □   ▷
5  □   □   □   □   □   □   □   □   ▷
4  □   □   □   □   □   □   □   □   ▷
3  □   □   □   □   □   □   □   □   ▷
2  □   □   □   □   □   □   □   □   ▷
1  □   □   □   □   □   □   □   □   ▷
0  □   □   □   □   □   □   □   □   ▷
8  ▽   ▽   ▽   ▽   ▽   ▽   ▽   ▽   ⬚
(y)
```
- Main grid: (0,7) to (7,0)
- Top row: (0,8) to (7,8)
- Right column: (8,0) to (8,7)
- Top-right corner: (8,8)

Example coordinates:
- (0,7): Bottom-left corner
- (7,7): Bottom-right (excluding right column)
- (0,0): Top-left
- (7,0): Top-right (excluding right column)
- (8,8): Top-right corner (special function button)

### Control Buttons
- `l` - List all available playlists
- `a` - List and start animations
- `x` - Stop current animation
- `q` - Quit the application

## System Requirements & Compatibility

### Tested Environment
- macOS Sonoma 15.1.1
- Python 3.6 or higher
- Novation Launchpad MK2 (tested on MK2+)
- Spotify Premium account

### Important Notes
- Primary development and testing was done on macOS
- Other operating systems may require additional setup or have different behavior
- If using Windows or Linux, MIDI device setup process might differ

### macOS Setup
1. Open 'Audio MIDI Setup' application
2. Go to Window > Show MIDI Studio
3. Ensure Launchpad MK2 is visible and enabled
4. Connect Launchpad before starting the script

### Known Issues
- If Launchpad is not recognized:
  - Try unplugging and replugging the device
  - Restart the Audio MIDI Setup application
  - Ensure no other applications are using the Launchpad

If you successfully run this on other operating systems, please let us know so we can update the compatibility list.

## Notes

- Requires Spotify Premium for playback control
- Playlist names are case-insensitive but must otherwise match exactly
- The script must be run from a terminal that can handle input commands

## Running as a Service (macOS)

You can set up the script to run automatically on macOS startup:

1. Edit the service file:
   ```bash
   # Create a copy of the plist file
   cp com.launchpad.spotify.plist ~/Library/LaunchAgents/
   ```

2. Edit the plist file to match your system:
   - Replace `/full/path/to/your/mk2.py` with the actual path to your script
   - Replace `YOUR_USERNAME` with your macOS username
   - Update the `WorkingDirectory` to match your script's location

3. Set proper permissions:
   ```bash
   chmod 644 ~/Library/LaunchAgents/com.launchpad.spotify.plist
   ```

4. Load the service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.launchpad.spotify.plist
   ```

5. Start the service:
   ```bash
   launchctl start com.launchpad.spotify
   ```

### Service Management Commands
```bash
# Start the service
launchctl start com.launchpad.spotify

# Stop the service
launchctl stop com.launchpad.spotify

# Unload the service (remove from startup)
launchctl unload ~/Library/LaunchAgents/com.launchpad.spotify.plist

# Check service status
launchctl list | grep launchpad

# View logs
tail -f ~/Library/Logs/launchpad_spotify.log
tail -f ~/Library/Logs/launchpad_spotify_error.log
```

### Important Notes
- Make sure all setup steps (Spotify authentication, etc.) are completed before running as a service
- The service will start automatically on system boot
- Logs are stored in `~/Library/Logs/`
- If you update the script, restart the service for changes to take effect