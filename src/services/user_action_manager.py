"""User mode pad action mappings (User 1 / User 2)."""

import json
import os

CONFIG_PATH = 'config/user_actions.json'
PROFILES = ('user1', 'user2')


def load_user_actions(path=CONFIG_PATH):
    """Load user action banks from JSON.

    Returns:
        dict: {'user1': {(x,y): action}, 'user2': {...}}
    """
    banks = {p: {} for p in PROFILES}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for profile in PROFILES:
            raw = data.get(profile) or {}
            for coord, action in raw.items():
                try:
                    x, y = map(int, coord.split(','))
                except (ValueError, AttributeError):
                    continue
                if isinstance(action, dict) and action.get('type'):
                    banks[profile][(x, y)] = action
    except FileNotFoundError:
        print(f"Warning: {path} not found, using empty user actions")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {path}")
    except Exception as e:
        print(f"Error loading user actions: {e}")
    return banks


class UserActionManager:
    """Manages per-profile pad → action mappings."""

    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self.banks = {p: {} for p in PROFILES}
        self.load()

    def load(self):
        """Reload banks from disk."""
        self.banks = load_user_actions(self.path)

    def save(self):
        """Persist banks to disk."""
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        payload = {}
        for profile in PROFILES:
            string_map = {}
            for (x, y), action in self.banks[profile].items():
                string_map[f"{x},{y}"] = action
            payload[profile] = string_map
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def get(self, profile, x, y):
        """Get action for profile coordinates, or None."""
        if profile not in PROFILES:
            return None
        return self.banks[profile].get((x, y))

    def set(self, profile, x, y, action):
        """Set action for profile coordinates."""
        if profile not in PROFILES:
            raise ValueError(f"Invalid profile: {profile}")
        if not isinstance(action, dict) or not action.get('type'):
            raise ValueError("Action must be a dict with a 'type' field")
        self.banks[profile][(x, y)] = action

    def delete(self, profile, x, y):
        """Delete action at coordinates. Returns True if removed."""
        if profile not in PROFILES:
            return False
        key = (x, y)
        if key in self.banks[profile]:
            del self.banks[profile][key]
            return True
        return False

    def list_profile(self, profile):
        """Return JSON-serializable mapping for one profile."""
        if profile not in PROFILES:
            return {}
        out = {}
        for (x, y), action in sorted(
            self.banks[profile].items(), key=lambda i: (i[0][1], i[0][0])
        ):
            out[f"{x},{y}"] = {
                'coordinates': [x, y],
                **action,
            }
        return out

    def list_all(self):
        """Return both profiles as JSON-serializable dict."""
        return {p: self.list_profile(p) for p in PROFILES}
