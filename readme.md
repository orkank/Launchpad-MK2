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
- **🎉 NEW: Rich colorized terminal interface** with beautiful help and status displays
- **🎉 NEW: Web control panel** with real-time status and controls
- **🎉 NEW: Enhanced playlist mapping preview** with visual grid layout

## Updates

## 🚀 Major Update: Refactored Architecture (September 2025)

### 📂 **New Modular Code Structure**
The monolithic 2,216-line `mk2.py` file has been completely refactored into a clean, maintainable architecture:

```
src/
├── animations/
├── core/
├── effects/
├── hardware/
├── services/
├── api/
├── utils/
└── main.py
```

### 🎨 **Enhanced Terminal Experience**
- **Rich colorized interface** using the Rich library
- **Smart help system**: Simple commands on startup, detailed help with `h` command
- **Beautiful status displays** with tables, colors, and emojis
- **Playlist mapping preview** with `v` command showing grid layout and utilization

### 🌐 **New Web Control Panel**
Access via `http://localhost:5125/` for:
- **🎵 Now Playing** - Current track display with play/pause controls
- **✨ Animation Control** - Dropdown selection with one-click start/stop
- **📊 Real-time Status** - Live stats for playlists, animations, Spotify connection
- **📋 Mapping Browser** - Visual preview of all playlist-animation mappings
- **📱 Mobile-friendly** - Responsive design with glassmorphism UI

### 🎯 **Enhanced Commands**
- `h` - Beautiful colorized help with organized sections
- `v` - Preview playlist-animation mappings with visual table
- All existing commands enhanced with better formatting and feedback

### 🔧 **Technical Improvements**
- **Better error handling** - cleaner, more informative error messages
- **Improved logging** - Flask request logging disabled for cleaner console
- **Enhanced performance** - modular loading and efficient resource management
- **Future-ready** - easy to extend with new features and integrations

### 📋 **New API Endpoints**
- `GET /` - Modern web control panel
- `GET /status` - Real-time system status (JSON)
- `GET /mappings` - Playlist mappings with coordinates (JSON)
- `POST /play|/pause|/next|/previous` - Direct Spotify controls

**Migration:** The refactored version maintains 100% compatibility with existing configurations and playlists. Simply run `python main.py` instead of `python mk2.py`.

### New Features (Latest) - 04/03/2025
- Added animation selection mode:
  - Press session button (4,8) to enter selection mode
  - Grid buttons (0,7 to 7,0) map to available animations
  - Press any grid button to instantly switch animations
  - Press session button again to exit selection mode
  - Visual guide in terminal shows which button activates each animation
- Added play/pause and stop buttons:
  - Play/Pause button (5,8) - Toggle playback.
- 5 More animations added

### New Features - 03/03/2025
- Added new mood-based animations:
  - `synthwave` - Retro synthwave style with sunset colors
  - `lofi` - Calm, smooth transitions for lo-fi music
  - `meditation` - Peaceful breathing effect for meditation
  - `party` - Energetic, colorful animation for party music
  - `focus` - Subtle, non-distracting for study/focus
- New 'r' command to randomize animations:
  - Randomly assigns animations to all playlists
  - Preserves existing mappings and coordinates
  - Shows before/after changes for each playlist
  - Updates playlists.json automatically

### New Features - 27/02/2025
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

## Installation

### Option 1: Direct Installation
1. Install required packages:
```bash
# macOS
brew install portaudio  # Required for audio processing
pip install -r requirements.txt

# Linux
sudo apt-get install python3-dev portaudio19-dev
pip install -r requirements.txt

# Windows
pip install -r requirements.txt  # No additional dependencies needed
```

2. Run the script:
```bash
python3 mk2.py
```

### Option 2: Using Virtual Environment (Recommended)
Virtual environments (venv) provide an isolated Python environment for your project. This is recommended because:
- Prevents conflicts between package versions
- Keeps your system Python clean
- Makes it easy to manage dependencies
- Ensures reproducible environments across different machines

1. Create and activate virtual environment:
```bash
# Navigate to project directory
cd path/to/Launchpad-MK2

# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate  # On macOS/Linux
.\venv\Scripts\activate   # On Windows

# Your prompt should now show (venv) at the beginning
# Example: (venv) user@computer:~/Launchpad-MK2$
```

2. Install required packages:
```bash
# macOS
brew install portaudio  # Required for audio processing
pip install -r requirements.txt

# Linux
sudo apt-get install python3-dev portaudio19-dev
pip install -r requirements.txt

# Windows
pip install -r requirements.txt  # No additional dependencies needed

# Note: requirements.txt now includes Rich library for enhanced terminal interface
```

3. Run the script:
```bash
# New refactored version (recommended)
python main.py

# Or use the original file (legacy)
python3 mk2.py
```

4. When finished:
```bash
deactivate  # Exit virtual environment
```

### Using the Virtual Environment

Every time you want to run the script:
```bash
# Navigate to project directory
cd path/to/Launchpad-MK2

# Activate the virtual environment
source venv/bin/activate  # On macOS/Linux
.\venv\Scripts\activate   # On Windows

# Run the script
python3 mk2.py

# When done, deactivate the environment
deactivate
```

### Managing the Virtual Environment

Useful commands:
```bash
# Update pip in virtual environment
pip install --upgrade pip

# Show installed packages
pip list

# Export requirements (if you add new packages)
pip freeze > requirements.txt

# Remove virtual environment (if needed)
deactivate  # Make sure to deactivate first
rm -rf venv  # On macOS/Linux
rmdir /s /q venv  # On Windows
```

Note: The virtual environment directory (venv) is already in .gitignore, so it won't be committed to version control.

### System Requirements
- Python 3.7+
- Novation Launchpad MK2
- Spotify Premium account

### Troubleshooting Installation
If you encounter issues installing the requirements:

1. PyAudio Installation Fails:
   - Make sure you have the system dependencies installed first
   - Try installing portaudio before PyAudio

2. python-rtmidi Installation Fails:
   - macOS: Make sure Xcode command line tools are installed
   - Linux: Install libasound2-dev and libjack-dev
   ```bash
   sudo apt-get install libasound2-dev libjack-dev
   ```

3. Other Issues:
   - Make sure you have the latest pip: `pip install --upgrade pip`
   - Try installing requirements one by one to identify problematic packages

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
| **`h`** | 🎨 **Show detailed colorized help** with hardware controls and tips |
| **`v`** | 📋 **Preview playlist-animation mappings** with visual grid layout |
| `s` | 📱 Show and select available Spotify devices |
| `p` | 📥 Fetch and save your Spotify playlists to `.playlists` file |
| `l` | 📋 List all available playlists |
| `a` | 🎨 List and start animations manually |
| `x` | ⏹️ Stop current animation |
| `g` | 🤖 Generate playlist mappings automatically |
| `r` | 🎲 Randomize animations for all playlists |
| `q` | 🚪 Quit the application |

### 🎯 **New Enhanced Commands:**
- **`h`** - Beautiful Rich-formatted help with organized sections:
  - Hardware button reference for Launchpad controls
  - Web interface endpoints and features
  - Pro tips and troubleshooting
- **`v`** - Visual playlist mapping preview:
  - Grid layout showing coordinates and assignments
  - Animation status indicators
  - Grid utilization statistics

### 💡 **Command Tips:**
- On startup, you'll see a **Quick Status** display with essential information
- Use `h` for comprehensive help when you need detailed guidance
- Use `v` to quickly verify your playlist mappings and find empty slots

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

### Mood-based animations
- `synthwave`
- `lofi`
- `meditation`
- `party`
- `focus`
- `starfield` - Twinkling stars in space
- `geometric` - Forming and transforming geometric shapes
- `sunset` - Sunset gradient with fade to night
- `heartbeat` - Pulsing heart animation
- `bloom` - Flower blooming from center

You can start animations either through:
1. Command line: Use 'a' to list and select animations
2. Web interface: Visit `http://localhost:5125/animation/<name>`
3. Stop any running animation with the 'x' command

## 🌐 Web Interface

### 🎮 **Modern Control Panel**
Visit **`http://localhost:5125`** for a beautiful, modern web control panel featuring:

- **🎵 Now Playing Section**
  - Current track display with artist and title
  - Play/pause/next/previous controls
  - Real-time playback status

- **✨ Animation Control**
  - Dropdown selection of all available animations
  - One-click start/stop buttons
  - Current animation status display

- **📊 Live Status Dashboard**
  - Mapped playlists count
  - Current animation name
  - Spotify connection status
  - Auto-refreshing every 5 seconds

- **📋 Playlist Mappings Browser**
  - Visual grid showing all button assignments
  - Playlist names, coordinates, and animations
  - Refresh button for latest mappings

### 📋 **API Endpoints**

#### 🎨 Animation Control
- `GET /` - Modern web control panel (HTML interface)
- `GET /animation/<name>` - Start an animation
- `GET /stop` - Stop current animation
- `GET /list` - List available animations (JSON)

#### 🎧 Spotify Control
- `GET /devices` - List available Spotify devices (JSON)
- `GET /device/<id>` - Select Spotify device by ID
- `POST /play` - Start playback
- `POST /pause` - Pause playback
- `POST /next` - Next track
- `POST /previous` - Previous track

#### 📊 Status & Data
- `GET /status` - Real-time system status (JSON)
- `GET /mappings` - Playlist mappings with coordinates (JSON)

### 💻 **Command Line Examples**
```bash
# Get current system status
curl http://localhost:5125/status

# Get playlist mappings
curl http://localhost:5125/mappings

# Start rainbow animation
curl http://localhost:5125/animation/rainbow

# Control Spotify playback
curl -X POST http://localhost:5125/play
curl -X POST http://localhost:5125/pause

# List Spotify devices
curl http://localhost:5125/devices
```

### 📱 **Mobile Friendly**
The web interface is fully responsive and works great on:
- 📱 **Mobile phones** - Touch-friendly controls
- 💻 **Desktop browsers** - Full feature access
- 📟 **Tablets** - Optimized layout

**Pro Tip:** Bookmark `http://localhost:5125` for quick access to your Launchpad controls from any device on your network!

## Launchpad Layout

### Grid Reference
The Launchpad MK2 has a 9x9 grid layout. The coordinate system works as follows:

```
   0   1   2   3   4   5   6   7   8  (x)
8  +   -   <   >   □   ▶   ■   □   S   Controls
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
- Volume Up (0,8)
- Volume Down (1,8)
- Previous Track (2,8)
- Next Track (3,8)
- Animation Selection Mode (4,8)
- Play/Pause (5,8)
- Random Playlist (7,8)

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

<!-- ### Service Management Commands
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
``` -->

### Important Notes
- Make sure all setup steps (Spotify authentication, etc.) are completed before running as a service
- The service will start automatically on system boot
- Logs are stored in `~/Library/Logs/`
- If you update the script, restart the service for changes to take effect
