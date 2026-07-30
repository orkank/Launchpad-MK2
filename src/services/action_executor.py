"""Execute user-mode pad actions (shell, URL, HTTP, app toggle, AppleScript)."""

import json
import subprocess
import threading
import urllib.error
import urllib.request
import webbrowser


class ActionExecutor:
    """Runs configured pad actions off the MIDI thread."""

    def __init__(self):
        self.last_message = None  # {'type': 'success'|'error'|'warning', 'message': str}
        self._lock = threading.Lock()

    def run(self, action, sync=False):
        """Execute an action dict asynchronously (default) or synchronously.

        Args:
            action: Action configuration dict
            sync: If True, run on the calling thread

        Returns:
            threading.Thread | dict: Thread when async; result dict when sync
        """
        if sync:
            return self._execute(action)

        thread = threading.Thread(target=self._execute, args=(action,), daemon=True)
        thread.start()
        return thread

    def _set_message(self, msg_type, message):
        with self._lock:
            self.last_message = {'type': msg_type, 'message': message}
        print(f"[user-action] {message}")

    def pop_last_message(self):
        """Return and clear the last status message."""
        with self._lock:
            msg = self.last_message
            self.last_message = None
            return msg

    def _execute(self, action):
        if not action or not isinstance(action, dict):
            self._set_message('error', 'Invalid action')
            return {'ok': False, 'error': 'Invalid action'}

        action_type = action.get('type')
        label = action.get('label') or action_type or 'action'

        try:
            if action_type == 'shell':
                result = self._run_shell(action)
            elif action_type == 'open_url':
                result = self._run_open_url(action)
            elif action_type == 'http_request':
                result = self._run_http_request(action)
            elif action_type == 'app_toggle':
                result = self._run_app_toggle(action)
            elif action_type == 'applescript':
                result = self._run_applescript(action)
            else:
                result = {'ok': False, 'error': f'Unknown action type: {action_type}'}

            if result.get('ok'):
                self._set_message('success', result.get('message') or f'OK: {label}')
            else:
                self._set_message('error', result.get('error') or f'Failed: {label}')
            return result
        except Exception as e:
            self._set_message('error', f'{label}: {e}')
            return {'ok': False, 'error': str(e)}

    def _run_shell(self, action):
        command = (action.get('command') or '').strip()
        if not command:
            return {'ok': False, 'error': 'shell: empty command'}

        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode != 0:
            err = (completed.stderr or completed.stdout or '').strip()
            return {
                'ok': False,
                'error': f'shell exit {completed.returncode}' + (f': {err[:200]}' if err else ''),
            }
        out = (completed.stdout or '').strip()
        msg = f'shell OK' + (f': {out[:120]}' if out else '')
        return {'ok': True, 'message': msg}

    def _run_open_url(self, action):
        url = (action.get('url') or '').strip()
        if not url:
            return {'ok': False, 'error': 'open_url: empty url'}
        opened = webbrowser.open(url)
        if not opened:
            return {'ok': False, 'error': f'open_url: browser failed for {url}'}
        return {'ok': True, 'message': f'Opened {url}'}

    def _run_http_request(self, action):
        url = (action.get('url') or '').strip()
        if not url:
            return {'ok': False, 'error': 'http_request: empty url'}

        method = (action.get('method') or 'GET').upper()
        headers = action.get('headers') or {}
        if isinstance(headers, str):
            try:
                headers = json.loads(headers) if headers.strip() else {}
            except json.JSONDecodeError:
                return {'ok': False, 'error': 'http_request: headers must be JSON object'}
        if not isinstance(headers, dict):
            return {'ok': False, 'error': 'http_request: headers must be an object'}

        body = action.get('body')
        data = None
        if body is not None and body != '' and method not in ('GET', 'HEAD'):
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode('utf-8')
                headers = {**headers, 'Content-Type': headers.get('Content-Type', 'application/json')}
            else:
                data = str(body).encode('utf-8')

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = getattr(resp, 'status', 200)
                return {'ok': True, 'message': f'HTTP {method} {status}'}
        except urllib.error.HTTPError as e:
            return {'ok': False, 'error': f'HTTP {method} failed: {e.code} {e.reason}'}
        except urllib.error.URLError as e:
            return {'ok': False, 'error': f'HTTP {method} failed: {e.reason}'}

    @staticmethod
    def list_running_apps(include_background=False):
        """List running macOS application process names.

        Args:
            include_background: If True, include background-only processes

        Returns:
            list[str]: Sorted unique app/process names
        """
        if include_background:
            script = 'tell application "System Events" to get name of every process'
        else:
            script = (
                'tell application "System Events" to '
                'get name of every process whose background only is false'
            )
        completed = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if completed.returncode != 0:
            err = (completed.stderr or '').strip()
            raise RuntimeError(err or 'Failed to list running apps')

        raw = completed.stdout.strip()
        if not raw:
            return []

        # osascript returns comma-separated names; names themselves rarely contain commas
        names = [part.strip() for part in raw.split(',') if part.strip()]
        # Stable unique sorted list
        return sorted(set(names), key=str.lower)

    def _app_is_running(self, app_name):
        script = (
            f'tell application "System Events" to '
            f'(name of processes) contains "{app_name}"'
        )
        completed = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return completed.returncode == 0 and completed.stdout.strip().lower() == 'true'

    def _quit_app(self, app_name, force_kill=False):
        quit_script = f'tell application "{app_name}" to quit'
        completed = subprocess.run(
            ['osascript', '-e', quit_script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if completed.returncode == 0:
            return {'ok': True, 'message': f'Quit {app_name}'}

        if force_kill:
            kill = subprocess.run(
                ['killall', '-9', app_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if kill.returncode == 0:
                return {'ok': True, 'message': f'Force-killed {app_name}'}
            err = (kill.stderr or completed.stderr or '').strip()
            return {'ok': False, 'error': f'Force kill failed for {app_name}: {err[:200]}'}

        err = (completed.stderr or '').strip()
        return {'ok': False, 'error': f'Quit failed for {app_name}' + (f': {err[:200]}' if err else '')}

    def _open_app(self, app_name):
        completed = subprocess.run(
            ['open', '-a', app_name],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if completed.returncode != 0:
            err = (completed.stderr or '').strip()
            return {'ok': False, 'error': f'open failed for {app_name}' + (f': {err[:200]}' if err else '')}
        return {'ok': True, 'message': f'Opened {app_name}'}

    def _run_app_toggle(self, action):
        app_name = (action.get('app_name') or '').strip()
        if not app_name:
            return {'ok': False, 'error': 'app_toggle: empty app_name'}
        force_kill = bool(action.get('force_kill'))

        if self._app_is_running(app_name):
            return self._quit_app(app_name, force_kill=force_kill)
        return self._open_app(app_name)

    def _run_applescript(self, action):
        script = (action.get('script') or '').strip()
        if not script:
            return {'ok': False, 'error': 'applescript: empty script'}

        completed = subprocess.run(
            ['osascript'],
            input=script,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            err = (completed.stderr or '').strip()
            return {'ok': False, 'error': f'applescript failed' + (f': {err[:200]}' if err else '')}
        out = (completed.stdout or '').strip()
        return {'ok': True, 'message': 'AppleScript OK' + (f': {out[:120]}' if out else '')}
