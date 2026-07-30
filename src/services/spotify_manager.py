"""Spotify integration and management."""

import logging
import os
import platform
import subprocess
import threading
import time
import webbrowser

import spotipy
from spotipy.oauth2 import SpotifyOAuth


class _SuppressTransientSpotipyLogs(logging.Filter):
    """Hide Spotipy's noisy logs for brief token races (controller still works)."""

    def filter(self, record):
        try:
            msg = record.getMessage().lower()
        except Exception:
            return True
        if 'access token missing' in msg:
            return False
        return True


def configure_spotipy_logging():
    """Install filters so transient token races don't spam the console."""
    for name in ('spotipy', 'spotipy.client', 'spotipy.oauth2'):
        logger = logging.getLogger(name)
        # Avoid stacking duplicate filters on reload
        if not any(isinstance(f, _SuppressTransientSpotipyLogs) for f in logger.filters):
            logger.addFilter(_SuppressTransientSpotipyLogs())

TOKEN_CACHE_PATH = '.cache'
SECRET_FILE = os.path.join('config', '.secret')
SAMPLE_SECRET_FILE = os.path.join('config', 'sample.secret')
DEFAULT_SECRET_TEMPLATE = (
    "client_id=\n"
    "client_secret=\n"
    "default_device_id=\n"
)

# Spotify no longer allows "localhost" (Insecure). Loopback HTTP is still OK
# as an explicit IP: https://developer.spotify.com/documentation/web-api/concepts/redirect_uri
# Callback is handled by our Flask app (default API port 5125) so we can show
# a proper success/error page. Must match Spotify Developer Dashboard.
OAUTH_REDIRECT_URI = 'http://127.0.0.1:5125/callback'

SPOTIFY_SCOPES = [
    'user-read-playback-state',
    'user-modify-playback-state',
    'user-read-currently-playing',
    'playlist-read-private',
    'playlist-read-collaborative',
    'app-remote-control',
    'streaming',
    'user-read-playback-position',
    'user-read-recently-played',
]

_AUTH_FAILURE_MARKERS = (
    'invalid_grant',
    'refresh token revoked',
    'the access token expired',
    'no token provided',
    'authorization failed',
)

# Spotipy/cache races can briefly surface this while another thread refreshes.
_TRANSIENT_TOKEN_MARKERS = (
    'access token missing',
)


def set_oauth_redirect_uri(uri: str):
    """Set OAuth redirect URI (must match Dashboard + Flask /callback)."""
    global OAUTH_REDIRECT_URI
    OAUTH_REDIRECT_URI = uri
    print(f"Spotify OAuth redirect URI: {OAUTH_REDIRECT_URI}")


def get_oauth_redirect_uri() -> str:
    return OAUTH_REDIRECT_URI


def is_auth_failure(exc) -> bool:
    """Return True if the exception indicates Spotify auth/token failure."""
    msg = str(exc).lower()
    if is_transient_token_error(exc):
        return False
    return any(marker in msg for marker in _AUTH_FAILURE_MARKERS)


def is_transient_token_error(exc) -> bool:
    """True for short-lived token races (retry; do not force re-auth)."""
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_TOKEN_MARKERS)


def is_audio_features_restricted(exc) -> bool:
    """True when Spotify blocks deprecated audio-features / audio-analysis (403)."""
    msg = str(exc).lower()
    if '403' not in msg:
        return False
    return any(
        marker in msg
        for marker in ('audio-features', 'audio_features', 'audio-analysis', 'audio_analysis')
    )


def clear_token_cache(cache_path=TOKEN_CACHE_PATH):
    """Delete the Spotify token cache file if it exists."""
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print(f"Removed Spotify token cache: {cache_path}")
            return True
    except OSError as e:
        print(f"Could not remove token cache: {e}")
    return False


class SpotifyManager:
    """Manages Spotify client and related operations."""

    def __init__(self):
        self.spotify = None
        self.needs_reauth = False
        self._auth_failure_reported = False
        self._pending_auth_manager = None
        self._oauth_event = None
        self._oauth_result = None
        self._oauth_error = None
        self._oauth_lock = threading.Lock()
        # Serialize API use — Spotipy token refresh/cache is not thread-safe
        self._api_lock = threading.RLock()
        # Ensure config/.secret exists on first run after clone
        ensure_secret_file()

    @property
    def credentials_configured(self) -> bool:
        """True when config/.secret has non-empty client_id and client_secret."""
        return are_spotify_credentials_configured()

    def initialize(self, force_reauth=False):
        """Initialize Spotify client with required scopes."""
        ensure_secret_file()
        client = initialize_spotify(force_reauth=force_reauth)
        if client:
            self.spotify = client
            self.needs_reauth = False
            self._auth_failure_reported = False
            return True
        return False

    def validate_connection(self):
        """Validate the current Spotify session with a lightweight API call.

        Returns:
            bool: True if the session is usable
        """
        if not self.spotify:
            return False
        try:
            self.spotify.current_user()
            self.needs_reauth = False
            self._auth_failure_reported = False
            return True
        except Exception as e:
            if is_auth_failure(e):
                self.mark_auth_failed(e)
            else:
                print(f"Error validating Spotify connection: {e}")
            return False

    def mark_auth_failed(self, exc=None):
        """Mark the session as needing re-authentication.

        Stops further API use until reauthenticate() succeeds.
        Prints a recovery hint once to avoid log spam.
        """
        self.needs_reauth = True
        self.spotify = None
        if not self._auth_failure_reported:
            self._auth_failure_reported = True
            detail = f" ({exc})" if exc else ""
            print("\n" + "=" * 60)
            print(f"Spotify authentication failed{detail}")
            print("Refresh token is invalid or revoked.")
            print("Type 'auth' in the terminal (or use Re-auth in the web UI)")
            print("to sign in again and get a new token.")
            print("=" * 60 + "\n")

    def handle_api_error(self, exc) -> bool:
        """Handle an API exception. Returns True if it was an auth failure."""
        if is_auth_failure(exc):
            self.mark_auth_failed(exc)
            return True
        return False

    def begin_oauth(self, open_browser=True):
        """Start interactive OAuth; callback lands on our Flask /callback page.

        Returns:
            str: Spotify authorize URL, or None on failure
        """
        with self._oauth_lock:
            clear_token_cache()
            self.spotify = None
            self.needs_reauth = False
            self._auth_failure_reported = False
            self._oauth_result = None
            self._oauth_error = None
            self._oauth_event = threading.Event()

            # open_browser=False: Spotipy must NOT bind :5125 (Flask owns it)
            if not are_spotify_credentials_configured():
                self.needs_reauth = True
                self._oauth_error = 'missing_credentials'
                print(
                    "Spotify Client ID/Secret missing. "
                    "Add them in the web UI (Settings → Spotify API Credentials) "
                    f"or edit {SECRET_FILE}."
                )
                return None

            auth_manager = create_auth_manager(show_dialog=True, open_browser=False)
            if not auth_manager:
                self.needs_reauth = True
                self._oauth_error = 'missing_credentials'
                return None

            self._pending_auth_manager = auth_manager
            auth_url = auth_manager.get_authorize_url()

        print("\nStarting Spotify re-authentication...")
        print(f"After login you should see our callback page at: {OAUTH_REDIRECT_URI}")
        print(f"Authorize URL:\n{auth_url}\n")

        if open_browser:
            try:
                webbrowser.open(auth_url)
                print("Opened Spotify login in your browser.")
            except Exception as e:
                print(f"Could not open browser automatically: {e}")
                print("Open the authorize URL above manually.")

        return auth_url

    def complete_oauth(self, code=None, error=None, state=None):
        """Finish OAuth after Spotify redirects to Flask /callback."""
        with self._oauth_lock:
            if error:
                self._oauth_error = error
                self._oauth_result = False
                self.needs_reauth = True
                if self._oauth_event:
                    self._oauth_event.set()
                print(f"Spotify authorization denied/failed: {error}")
                return False

            if not code:
                self._oauth_error = 'missing_code'
                self._oauth_result = False
                self.needs_reauth = True
                if self._oauth_event:
                    self._oauth_event.set()
                return False

            auth_manager = self._pending_auth_manager
            if not auth_manager:
                self._oauth_error = 'no_pending_login'
                self._oauth_result = False
                self.needs_reauth = True
                if self._oauth_event:
                    self._oauth_event.set()
                print("OAuth callback received but no login is in progress. Use 'auth' or Re-auth.")
                return False

            if state and auth_manager.state and state != auth_manager.state:
                self._oauth_error = 'state_mismatch'
                self._oauth_result = False
                self.needs_reauth = True
                if self._oauth_event:
                    self._oauth_event.set()
                print("Spotify OAuth state mismatch — possible CSRF or stale login.")
                return False

            try:
                auth_manager.get_access_token(code, as_dict=False, check_cache=False)
                client = spotipy.Spotify(auth_manager=auth_manager)
                client.current_user()
                self.spotify = client
                self.needs_reauth = False
                self._auth_failure_reported = False
                self._pending_auth_manager = None
                self._oauth_result = True
                self._oauth_error = None
                print("Spotify re-authenticated successfully.")
                if self._oauth_event:
                    self._oauth_event.set()
                return True
            except Exception as e:
                self._oauth_error = str(e)
                self._oauth_result = False
                self.needs_reauth = True
                self.spotify = None
                print(f"Failed to exchange Spotify auth code: {e}")
                if self._oauth_event:
                    self._oauth_event.set()
                return False

    def wait_for_oauth(self, timeout=180):
        """Block until complete_oauth runs or timeout."""
        event = self._oauth_event
        if not event:
            return False
        finished = event.wait(timeout=timeout)
        if not finished:
            print("Timed out waiting for Spotify login callback.")
            self.needs_reauth = True
            return False
        return bool(self._oauth_result)

    def reauthenticate(self, open_browser=True, timeout=180):
        """Clear tokens and run interactive OAuth via Flask callback page.

        Returns:
            bool: True if re-authentication succeeded
        """
        auth_url = self.begin_oauth(open_browser=open_browser)
        if not auth_url:
            if not are_spotify_credentials_configured():
                print(
                    f"Re-authentication failed: set Client ID and Secret in {SECRET_FILE} "
                    "(or Settings → Spotify API Credentials in the web UI)."
                )
            else:
                print("Re-authentication failed. Check credentials in config/.secret")
            print(f"Confirm Redirect URI in Spotify Dashboard: {OAUTH_REDIRECT_URI}")
            self.needs_reauth = True
            return False

        print("Waiting for Spotify login in the browser...")
        return self.wait_for_oauth(timeout=timeout)

    def ensure_ready(self):
        """Return True if Spotify client is available and auth is OK."""
        if self.needs_reauth:
            # Hint is printed once by mark_auth_failed; stay quiet afterwards
            if not self._auth_failure_reported:
                self.mark_auth_failed()
            return False
        if not self.spotify:
            if not self._auth_failure_reported:
                print("Spotify not initialized. Type 'auth' to connect.")
                self._auth_failure_reported = True
            return False
        return True

    def get_devices(self):
        """Get available Spotify devices."""
        if not self.ensure_ready():
            return None
        try:
            return self.api_call('devices', quiet=True)
        except Exception as e:
            if not self.handle_api_error(e):
                print(f"Error getting devices: {e}")
            return None

    def get_current_playback(self):
        """Get current playback information (thread-safe)."""
        try:
            return self.api_call('current_playback', quiet=True)
        except Exception:
            return None

    def _ensure_access_token(self):
        """Load/refresh access token under the API lock before any request."""
        auth_manager = getattr(self.spotify, 'auth_manager', None)
        if not auth_manager:
            return
        # Force a coherent token read/refresh while we hold _api_lock
        token = auth_manager.get_access_token(as_dict=False)
        if not token:
            raise RuntimeError('Access token missing')

    def api_call(self, method_name, *args, quiet=False, retry_transient=True, **kwargs):
        """Call a spotipy client method under a lock (safe across monitor/API threads).

        Args:
            method_name: Name of method on the spotipy client
            quiet: If True, suppress non-auth error prints and return None on error
            retry_transient: Retry once on brief 'access token missing' races
        """
        with self._api_lock:
            if self.needs_reauth or not self.spotify:
                return None
            method = getattr(self.spotify, method_name, None)
            if not callable(method):
                print(f"Unknown Spotify API method: {method_name}")
                return None
            try:
                self._ensure_access_token()
                return method(*args, **kwargs)
            except Exception as e:
                if retry_transient and is_transient_token_error(e):
                    time.sleep(0.2)
                    try:
                        self._ensure_access_token()
                        return method(*args, **kwargs)
                    except Exception as e2:
                        e = e2
                if self.handle_api_error(e):
                    return None
                if quiet:
                    return None
                print(f"Spotify API error ({method_name}): {e}")
                raise


def ensure_secret_file():
    """Create config/.secret from sample (or a blank template) if missing.

    Returns:
        bool: True if the file exists after this call
    """
    if os.path.exists(SECRET_FILE):
        return True

    os.makedirs(os.path.dirname(SECRET_FILE) or 'config', exist_ok=True)
    try:
        if os.path.exists(SAMPLE_SECRET_FILE):
            with open(SAMPLE_SECRET_FILE, 'r', encoding='utf-8') as src:
                content = src.read()
            if not content.strip():
                content = DEFAULT_SECRET_TEMPLATE
        else:
            content = DEFAULT_SECRET_TEMPLATE

        with open(SECRET_FILE, 'w', encoding='utf-8') as dest:
            dest.write(content if content.endswith('\n') else content + '\n')
        print(f"Created {SECRET_FILE} from sample — add your Spotify Client ID and Secret.")
        return True
    except OSError as e:
        print(f"Could not create {SECRET_FILE}: {e}")
        return False


def read_secret_values():
    """Read key=value pairs from config/.secret (creates file if missing)."""
    ensure_secret_file()
    secrets = {}
    try:
        with open(SECRET_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' not in line:
                    continue
                key, value = line.strip().split('=', 1)
                secrets[key] = value
    except OSError as e:
        print(f"Error reading {SECRET_FILE}: {e}")
    return secrets


def write_secret_values(updates):
    """Merge updates into config/.secret and write the file.

    Args:
        updates: dict of keys to set (None values are written as empty string)
    """
    ensure_secret_file()
    secrets = read_secret_values()
    for key, value in (updates or {}).items():
        secrets[key] = '' if value is None else str(value)

    # Stable preferred order, then any extra keys
    preferred = ('client_id', 'client_secret', 'default_device_id')
    lines = []
    seen = set()
    for key in preferred:
        if key in secrets:
            lines.append(f"{key}={secrets[key]}")
            seen.add(key)
    for key, value in secrets.items():
        if key not in seen:
            lines.append(f"{key}={value}")

    with open(SECRET_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def _load_spotify_credentials():
    """Load client_id / client_secret from config/.secret."""
    secrets = read_secret_values()
    client_id = (secrets.get('client_id') or '').strip()
    client_secret = (secrets.get('client_secret') or '').strip()
    if not client_id or not client_secret:
        return None, None
    return client_id, client_secret


def are_spotify_credentials_configured() -> bool:
    """True when both Spotify API credentials are present in config/.secret."""
    client_id, client_secret = _load_spotify_credentials()
    return bool(client_id and client_secret)


def save_spotify_credentials(client_id, client_secret):
    """Persist Spotify API credentials to config/.secret.

    Returns:
        bool: True on success
    """
    client_id = (client_id or '').strip()
    client_secret = (client_secret or '').strip()
    if not client_id or not client_secret:
        raise ValueError('Both client_id and client_secret are required')
    write_secret_values({
        'client_id': client_id,
        'client_secret': client_secret,
    })
    return True


def create_auth_manager(show_dialog=False, open_browser=False):
    """Build a SpotifyOAuth manager using the Flask callback redirect URI."""
    try:
        ensure_secret_file()
        client_id, client_secret = _load_spotify_credentials()
        if not client_id or not client_secret:
            print(
                f"Missing Spotify credentials in {SECRET_FILE}. "
                "Set Client ID and Secret (Settings in the web UI, or edit the file)."
            )
            return None

        return SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=OAUTH_REDIRECT_URI,
            scope=' '.join(SPOTIFY_SCOPES),
            open_browser=open_browser,
            cache_path=TOKEN_CACHE_PATH,
            show_dialog=show_dialog,
        )
    except Exception as e:
        print(f"Error creating Spotify auth manager: {e}")
        return None


def initialize_spotify(force_reauth=False):
    """Initialize Spotify from cached tokens only (no interactive browser).

    Interactive login uses begin_oauth() → Flask /callback (nice welcome page).

    Args:
        force_reauth: If True, clear cache before connecting.

    Returns:
        spotipy.Spotify: Initialized Spotify client or None on failure
    """
    configure_spotipy_logging()
    try:
        ensure_secret_file()
        if not are_spotify_credentials_configured():
            print(
                f"Spotify API credentials not set in {SECRET_FILE}. "
                "Open the web panel → Settings → Spotify API Credentials."
            )
            return None

        if force_reauth:
            clear_token_cache(TOKEN_CACHE_PATH)

        auth_manager = create_auth_manager(show_dialog=False, open_browser=False)
        if not auth_manager:
            return None

        token_info = auth_manager.get_cached_token()
        if not token_info:
            # Loud banner is printed later by AuthAlertService
            return None

        spotify = spotipy.Spotify(auth_manager=auth_manager)

        # Fail fast if the cached refresh token is already revoked
        try:
            spotify.current_user()
        except Exception as e:
            if is_auth_failure(e):
                print(f"Spotify token invalid: {e}")
                print("Cached credentials were rejected. Run 'auth' to sign in again.")
                return None
            raise

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
        if is_auth_failure(e):
            print("Spotify auth failed. Type 'auth' to reconnect.")


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


def get_local_machine_names():
    """Return lowercase names that may identify this Mac in Spotify Connect."""
    names = set()
    host = platform.node() or ''
    if host:
        names.add(host)
        names.add(host.split('.')[0])
    for key in ('ComputerName', 'LocalHostName'):
        try:
            completed = subprocess.run(
                ['scutil', '--get', key],
                capture_output=True,
                text=True,
                timeout=5,
            )
            value = (completed.stdout or '').strip()
            if completed.returncode == 0 and value:
                names.add(value)
        except Exception:
            pass
    return {n.lower() for n in names if n}


def is_local_spotify_device(device):
    """True if this Spotify Connect device looks like the machine running the controller.

    Requires type Computer and a name that matches this Mac's hostname / ComputerName.
    """
    if not device or not isinstance(device, dict):
        return False
    if (device.get('type') or '').lower() != 'computer':
        return False
    name = (device.get('name') or '').strip().lower()
    if not name:
        return False
    for local in get_local_machine_names():
        if local and (local in name or name in local):
            return True
    return False


def read_default_device_id():
    """Read default_device_id from config/.secret."""
    try:
        secrets = read_secret_values()
        return (secrets.get('default_device_id') or '').strip()
    except Exception:
        return ''


def annotate_devices_with_local(devices_payload):
    """Add is_local flags to a Spotify devices() response (mutates in place)."""
    if not devices_payload or 'devices' not in devices_payload:
        return devices_payload
    for device in devices_payload.get('devices') or []:
        device['is_local'] = is_local_spotify_device(device)
    return devices_payload


def is_default_device_local(devices_list=None):
    """Whether the configured default device is this machine.

    Args:
        devices_list: Optional list of device dicts; if omitted, locality is
            unknown when the device is offline (returns False).
    """
    default_id = read_default_device_id()
    if not default_id:
        return False
    if not devices_list:
        return False
    for device in devices_list:
        if device.get('id') == default_id:
            return is_local_spotify_device(device)
    return False


def _spotify_desktop_running():
    """Check if the Spotify macOS app process is running."""
    try:
        from .action_executor import ActionExecutor
        return ActionExecutor()._app_is_running('Spotify')
    except Exception:
        return False


def _launch_spotify_desktop():
    """Open the Spotify macOS app."""
    completed = subprocess.run(
        ['open', '-a', 'Spotify'],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return completed.returncode == 0


def _sync_auto_launch_with_devices(device_list):
    """Turn off auto-launch if the saved default device is visible and not local."""
    from ..utils.config_manager import config_manager

    if not config_manager.is_auto_launch_spotify_enabled():
        return
    default_id = read_default_device_id()
    if not default_id or not device_list:
        return
    for device in device_list:
        if device.get('id') == default_id:
            if not is_local_spotify_device(device):
                print("Default device is not this Mac — disabling Auto-launch Spotify")
                config_manager.set_auto_launch_spotify(False)
            return


def _maybe_auto_launch_spotify(_call, devices_payload):
    """If enabled and default device is this Mac, launch Spotify when closed.

    Args:
        _call: Spotify API caller
        devices_payload: Current devices() response (may be empty)

    Returns:
        dict: devices payload (possibly refreshed after launch)
    """
    from ..utils.config_manager import config_manager

    if not devices_payload:
        devices_payload = {'devices': []}

    device_list = devices_payload.get('devices') or []
    _sync_auto_launch_with_devices(device_list)

    if not config_manager.is_auto_launch_spotify_enabled():
        return devices_payload

    default_id = read_default_device_id()
    if not default_id:
        return devices_payload

    # If default is online and not local, already disabled above
    for device in device_list:
        if device.get('id') == default_id and not is_local_spotify_device(device):
            return devices_payload

    if _spotify_desktop_running():
        return devices_payload

    print("Spotify app is not running — auto-launching (default device is this Mac)...")
    if not _launch_spotify_desktop():
        print("Failed to launch Spotify app")
        return devices_payload

    for _ in range(12):
        time.sleep(1)
        try:
            devices = _call('devices')
        except Exception:
            continue
        if devices and devices.get('devices'):
            print("Spotify Connect devices available after auto-launch")
            return devices

    print("Spotify launched but no Connect devices appeared yet")
    return devices_payload


def get_active_or_default_device(spotify, manager=None):
    """Get active device, default device, or first available device.

    Args:
        spotify: Spotify client instance
        manager: Optional SpotifyManager for auth-failure handling

    Returns:
        str: Device ID or None
    """
    if manager is not None:
        if manager.needs_reauth or not manager.spotify:
            manager.ensure_ready()
            return None
        spotify = manager.spotify

    if spotify is None:
        print("Spotify not initialized")
        return None

    def _call(name, *args, **kwargs):
        if manager is not None:
            return manager.api_call(name, *args, quiet=False, **kwargs)
        return getattr(spotify, name)(*args, **kwargs)

    try:
        # Get available devices (may auto-launch Spotify on this Mac)
        devices = _call('devices')
        devices = _maybe_auto_launch_spotify(_call, devices)

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
                default_device_id = read_default_device_id()
                if default_device_id:
                    print(f"Using default device from .secret")
                    _call('start_playback', device_id=default_device_id)
                    time.sleep(1)  # Wait for device activation
                    device_id = default_device_id
            except Exception as e:
                if manager and manager.handle_api_error(e):
                    return None
                print(f"Could not use default device: {e}")

        # If still no device, use the first available one
        if not device_id and devices['devices']:
            first_device = devices['devices'][0]
            device_id = first_device['id']
            print(f"No active or default device found. Using first available device: {first_device['name']}")
            _call('start_playback', device_id=device_id)
            time.sleep(2)  # Wait for device activation

        return device_id

    except Exception as e:
        if manager and manager.handle_api_error(e):
            return None
        if is_auth_failure(e):
            print(f"Error getting device: {e}")
            print("Spotify auth failed. Type 'auth' to reconnect.")
            return None
        if is_transient_token_error(e):
            return None
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
        if is_auth_failure(e):
            print("Spotify auth failed. Type 'auth' to reconnect.")
            return None
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
            print("Try re-authenticating with the 'auth' command")
        return None
