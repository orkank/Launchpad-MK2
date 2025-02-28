# Launchpad MK2 Spotify Controller

This project was created to repurpose an old Novation Launchpad MK2 as a Spotify controller. The script allows you to control Spotify playback and create LED animations through both direct interaction and HTTP requests, enabling integration with other applications.

![Launchpad MK2 Spotify Controller](giphy.gif)

## Disclaimer
- This is a personal project created for my own use with an old Launchpad MK2
- Use this script at your own risk
- No warranty or guarantee is provided
- The code and documentation may have conflicts or inconsistencies
- If you encounter issues, please open a GitHub issue for discussion

### Features
- Spotify playlist, play/pause and next/previous control through Launchpad buttons
- LED animations controllable via HTTP requests
- Device selection for Spotify playback
- Customizable playlist mappings with animations

## Updates

### New Features (Latest) - 27/02/2025
- Automatic playlist mapping with 'g' command
  - Sort by newest playlists
  - Sort by most popular playlists
  - Sort by all playlists
  - Random animation assignment for new mappings (this action does not remove your existing records in playlists.json)
- Random playlist selection using mixer button (7,8)
- UTF-8 support for playlist names with emojis
- Config files moved to config folder

### Default Device Support - 04/12/2024
Added support for automatically using a default Spotify device when no active device is found.

To configure:
1. Add your preferred device ID to `.secret`:
```
client_id=YOUR_CLIENT_ID
client_secret=YOUR_CLIENT_SECRET
default_device_id=YOUR_DEFAULT_DEVICE_ID
```

2. To find your device ID:
   - Use the 'S' command to show available devices
   - Copy the ID of your preferred device
   - Add it to `.secret` as shown above

This fixes the "No active device found" error that occurred when:
- Spotify closes and opens
- No device was actively playing
- Multiple devices were available but none active

Note: Make sure Spotify is open on your default device for this to work properly.

### Real-time Spotify Integration
The controller maintains real-time synchronization with Spotify, detecting changes made from any source:

- Changes made in Spotify desktop/mobile app
- Third-party apps

When a playlist change is detected from any sources, the controller automatically:
1. Identifies the new playlist
2. Checks if it matches a configured playlist in `playlists.json`
3. Switches to the corresponding animation if configured
4. Detects play/pause state and stops animation or switches to last animation

This means you can control your music from anywhere, and the Launchpad will always stay in sync with the correct animation for your current playlist.

## TODO

### Coming Soon
- [ ] HomeKit/Homebridge Integration
  - Control Spotify playback from Home app
  - Change animations via HomeKit scenes
  - Control volume with HomeKit sliders
  - View playback status in Home app

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

### Option 1: Direct Installation
1. Install required packages:
```bash
pip install python-rtmidi flask spotipy watchdog
```

2. Run the script:
```bash
python3 mk2.py
```

### Option 2: Using Virtual Environment (Recommended)
Using a virtual environment helps avoid package conflicts between projects.

1. Create and activate virtual environment:
```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate  # On macOS/Linux
.\venv\Scripts\activate   # On Windows
```

2. Install required packages:
```bash
pip install python-rtmidi flask spotipy watchdog
```

3. Run the script:
```bash
python3 mk2.py
```

4. When finished:
```bash
deactivate  # Exit virtual environment
```

### System Dependencies
- macOS: `brew install portaudio`
- Linux: `sudo apt-get install python3-pyaudio`

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
            "description": "Optional description",
            "animation": "rainbow"
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
            "description": "Bottom-left - Chill vibes",
            "animation": "pulse"
        },
        "0,0": {
            "name": "Trip",
            "description": "Top-left - Travel playlist",
            "animation": "classical"
        }
    }
}
```

  - [Grid Reference](#grid-reference)

To configure:
1. Use 'l' command to list available playlists
2. Copy exact playlist names
3. Edit playlists.json
4. New playlist mappings will be loaded automatically

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
| `g` | Generate playlist mappings automatically

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
- `equalizer`: equalizer_animation,

### Genre-based animations

- `electronic`: electronic_animation,
- `classical`: classical_animation,
- `rock`: rock_animation,
- `jazz`: jazz_animation,
- `ambient`: ambient_animation,

- ~~Temperature~~ (temporarily disabled)

Note: Temperature animation is currently disabled pending further development.

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
The Launchpad MK2 has a 9x9 grid layout. The coordinate system works as follows:

```
   0   1   2   3   4   5   6   7   8  (x)
8  +   -   <   >   □   □   □   □   S   Controls
7  □   □   □   □   □   □   □   □   ▷   Playlists
6  □   □   □   □   □   □   □   □   ▷
5  □   □   □   □   □   □   □   □   ▷
4  □   □   □   □   □   □   □   □   ▷
3  □   □   □   □   □   □   □   □   ▷
2  □   □   □   □   □   □   □   □   ▷
1  □   □   □   □   □   □   □   □   ▷
0  □   □   □   □   □   □   □   □   ▷
(y)
```

- x increases from left to right (0-8)
- y decreases from top to bottom (8-0)
- Upper row is y=8 (for special functions)
- Main playlist buttons are typically on row y=7
- The right column (x=8) contains control buttons (▷)

Example coordinates:
- Top row buttons: (0,8), (1,8), etc.
- First playlist position: (0,7)
- Second playlist position: (1,7)
- Third playlist position: (2,7)
- Spotify device selection: (8,8)

When configuring your playlists.json, use these coordinates:
```json
{
    "mappings": {
        "0,7": {
            "name": "First Playlist",
            "animation": "rainbow"
        },
        "1,7": {
            "name": "Second Playlist",
            "animation": "matrix"
        }
    }
}
```

### Control Buttons
- `l` - List all available playlists
- `a` - List and start animations
- `x` - Stop current animation
- `q` - Quit the application
- Mixer (7,8) - Play random playlist

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

If you successfully run this on other operating systems, please let me know so I can update the compatibility list.

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
