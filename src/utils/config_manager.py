"""Configuration manager for audio features and other settings."""

import json
import os
from typing import Dict, Any


class ConfigManager:
    """Manages configuration settings for the application."""

    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.audio_features_config = None
        self.load_configs()

    def load_configs(self):
        """Load all configuration files."""
        self.load_audio_features_config()

    def load_audio_features_config(self) -> Dict[str, Any]:
        """Load audio features configuration."""
        config_file = os.path.join(self.config_dir, "audio_features.json")

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.audio_features_config = json.load(f)
                    print(f"✅ Loaded audio features config from {config_file}")
            else:
                # Create default config
                self.audio_features_config = self.get_default_audio_config()
                self.save_audio_features_config()
                print(f"📄 Created default audio features config at {config_file}")

        except Exception as e:
            print(f"⚠️ Error loading audio features config: {e}")
            self.audio_features_config = self.get_default_audio_config()

        return self.audio_features_config

    def save_audio_features_config(self):
        """Save audio features configuration."""
        config_file = os.path.join(self.config_dir, "audio_features.json")

        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.audio_features_config, f, indent=2)
            print(f"💾 Saved audio features config to {config_file}")
        except Exception as e:
            print(f"⚠️ Error saving audio features config: {e}")

    def get_default_audio_config(self) -> Dict[str, Any]:
        """Get default audio features configuration."""
        return {
            "enabled": True,
            "auto_start": True,
            "update_interval": 2.0,
            "features": {
                "real_time_analysis": True,
                "auto_animation_selection": True,
                "adaptive_animations": True,
                "spectrum_visualization": True
            },
            "performance": {
                "cache_duration": 30,
                "api_timeout": 5.0,
                "max_retries": 3
            },
            "ui": {
                "show_status_messages": True,
                "verbose_logging": False,
                "show_feature_changes": True
            }
        }

    # Audio Features Config Getters
    def is_audio_features_enabled(self) -> bool:
        """Check if audio features are enabled."""
        return self.audio_features_config.get("enabled", True)

    def should_auto_start_analysis(self) -> bool:
        """Check if audio analysis should auto-start."""
        return self.audio_features_config.get("auto_start", True)

    def get_update_interval(self) -> float:
        """Get audio analysis update interval."""
        return self.audio_features_config.get("update_interval", 2.0)

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled."""
        features = self.audio_features_config.get("features", {})
        return features.get(feature_name, True)

    def get_performance_setting(self, setting_name: str, default=None):
        """Get a performance setting."""
        performance = self.audio_features_config.get("performance", {})
        return performance.get(setting_name, default)

    def get_ui_setting(self, setting_name: str, default=None):
        """Get a UI setting."""
        ui = self.audio_features_config.get("ui", {})
        return ui.get(setting_name, default)

    # Audio Features Config Setters
    def set_audio_features_enabled(self, enabled: bool):
        """Enable or disable audio features."""
        self.audio_features_config["enabled"] = enabled
        self.save_audio_features_config()
        status = "enabled" if enabled else "disabled"
        print(f"🎵 Audio features {status}")

    def set_feature_enabled(self, feature_name: str, enabled: bool):
        """Enable or disable a specific feature."""
        if "features" not in self.audio_features_config:
            self.audio_features_config["features"] = {}

        self.audio_features_config["features"][feature_name] = enabled
        self.save_audio_features_config()
        status = "enabled" if enabled else "disabled"
        print(f"🎵 Feature '{feature_name}' {status}")

    def set_update_interval(self, interval: float):
        """Set audio analysis update interval."""
        self.audio_features_config["update_interval"] = max(0.5, min(10.0, interval))
        self.save_audio_features_config()
        print(f"⏱️ Update interval set to {interval} seconds")

    def toggle_audio_features(self) -> bool:
        """Toggle audio features on/off."""
        current = self.is_audio_features_enabled()
        self.set_audio_features_enabled(not current)
        return not current

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.audio_features_config = self.get_default_audio_config()
        self.save_audio_features_config()
        print("🔄 Audio features config reset to defaults")

    def get_config_summary(self) -> str:
        """Get a summary of current configuration."""
        enabled = self.is_audio_features_enabled()
        status = "ENABLED" if enabled else "DISABLED"

        summary = f"""
🎵 **Audio Features Status: {status}**

**Core Settings:**
- Auto-start: {self.should_auto_start_analysis()}
- Update interval: {self.get_update_interval()}s

**Features:**
- Real-time analysis: {self.is_feature_enabled('real_time_analysis')}
- Auto animation selection: {self.is_feature_enabled('auto_animation_selection')}
- Adaptive animations: {self.is_feature_enabled('adaptive_animations')}
- Spectrum visualization: {self.is_feature_enabled('spectrum_visualization')}

**Performance:**
- Cache duration: {self.get_performance_setting('cache_duration', 30)}s
- API timeout: {self.get_performance_setting('api_timeout', 5.0)}s
- Max retries: {self.get_performance_setting('max_retries', 3)}

**UI:**
- Show status messages: {self.get_ui_setting('show_status_messages', True)}
- Verbose logging: {self.get_ui_setting('verbose_logging', False)}
- Show feature changes: {self.get_ui_setting('show_feature_changes', True)}
        """
        return summary.strip()


# Global instance
config_manager = ConfigManager()



