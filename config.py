import os

CONFIG_PATH = "./config.env"

def load_config():
    """Load configuration from file or environment variables"""
    config = {}

    # First, try to load from config file
    if os.path.isfile(CONFIG_PATH):
        print(f"Loading config from {CONFIG_PATH}")
        with open(CONFIG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

    # Then, check environment variables and update config
    env_vars = {
        "LB_USER": os.getenv("LB_USER"),
        "METABRAINZ_TOKEN": os.getenv("METABRAINZ_TOKEN"),
        "MB_MIRROR": os.getenv("MB_MIRROR"),
	"LOCAL_MB_MIRROR": os.getenv("LOCAL_MB_MIRROR"),
        "PLEX_BASE_URL": os.getenv("PLEX_BASE_URL"),
        "PLEX_TOKEN": os.getenv("PLEX_TOKEN"),
        "HTTP_PORT": os.getenv("HTTP_PORT"),
        "PLEX_DAYS_FILTER": os.getenv("PLEX_DAYS_FILTER"),
        "LIDARR_UPDATE_INTERVAL": os.getenv("LIDARR_UPDATE_INTERVAL"),
        "PLEX_UPDATE_INTERVAL": os.getenv("PLEX_UPDATE_INTERVAL"),
        "PLEX_PLAYLIST_NAME": os.getenv("PLEX_PLAYLIST_NAME"),
        "LIDARR_UPDATE_INTERVAL": os.getenv("LIDARR_UPDATE_INTERVAL"),
        "PLEX_UPDATE_INTERVAL": os.getenv("PLEX_UPDATE_INTERVAL"),
    }

    # Update config with environment variables (they override file values)
    config_updated = False
    for key, value in env_vars.items():
        if value is not None:
            if key not in config or config[key] != value:
                config[key] = value
                config_updated = True

    # Apply defaults for missing values
    defaults = {
        "MB_MIRROR": "musicbrainz.org",
	"LOCAL_MB_MIRROR": "FALSE",
        "HTTP_PORT": "8000",
        "PLEX_DAYS_FILTER": "14",
        "LIDARR_UPDATE_INTERVAL": "86400",  # 24 hours in seconds
        "PLEX_UPDATE_INTERVAL": "86400",    # 24 hours in seconds
        "PLEX_PLAYLIST_NAME": "ListenBrainz Weekly Discovery",
        "MB_MIRROR": "musicbrainz.org",     # Public MusicBrainz or your local mirror
        "LIDARR_UPDATE_INTERVAL": "86400",  # 24 hours in seconds
        "PLEX_UPDATE_INTERVAL": "86400",  # 24 hours in seconds
    }

    for key, default_value in defaults.items():
        if key not in config or not config[key]:
            config[key] = default_value
            config_updated = True

    # Save config file if it was updated or doesn't exist
    if config_updated or not os.path.isfile(CONFIG_PATH):
        save_config(config)

    return config

def save_config(config):
    """Save configuration to file"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    with open(CONFIG_PATH, "w") as f:
        f.write("# ListenBrainz to Lidarr and Plex Configuration\n")
        f.write("# This file is auto-generated from environment variables\n\n")

        f.write("# ListenBrainz Settings\n")
        f.write(f"LB_USER={config.get('LB_USER', '')}\n")
        f.write(f"METABRAINZ_TOKEN={config.get('METABRAINZ_TOKEN', '')}\n\n")

        f.write("# MusicBrainz Settings\n")
        f.write(f"MB_MIRROR={config.get('MB_MIRROR', 'musicbrainz.org')}\n\n")

        f.write("# Plex Settings\n")
        f.write(f"PLEX_BASE_URL={config.get('PLEX_BASE_URL', '')}\n")
        f.write(f"PLEX_TOKEN={config.get('PLEX_TOKEN', '')}\n")
        f.write(f"PLEX_PLAYLIST_NAME={config.get('PLEX_PLAYLIST_NAME', 'ListenBrainz Weekly Discovery')}\n\n")

        f.write("# Application Settings\n")
        f.write(f"HTTP_PORT={config.get('HTTP_PORT', '8000')}\n")
        f.write(f"PLEX_DAYS_FILTER={config.get('PLEX_DAYS_FILTER', '14')}\n")
        f.write(f"LIDARR_UPDATE_INTERVAL={config.get('LIDARR_UPDATE_INTERVAL', '86400')}\n")
        f.write(f"PLEX_UPDATE_INTERVAL={config.get('PLEX_UPDATE_INTERVAL', '86400')}\n")
        f.write(f"LIDARR_UPDATE_INTERVAL={config.get('LIDARR_UPDATE_INTERVAL', '86400')}\n")
        f.write(f"PLEX_UPDATE_INTERVAL={config.get('PLEX_UPDATE_INTERVAL', '86400')}\n")

    print(f"Configuration saved to {CONFIG_PATH}")

# Load configuration on import
_config = load_config()

# Export configuration variables
USER = _config.get('LB_USER')
METABRAINZ_TOKEN = _config.get('METABRAINZ_TOKEN')
MB_MIRROR = _config.get('MB_MIRROR', 'musicbrainz.org')
LOCAL_MB_MIRROR = _config.get('LOCAL_MB_MIRROR', 'FALSE').strip().lower() == 'true'
PLEX_BASE_URL = _config.get('PLEX_BASE_URL')
PLEX_TOKEN = _config.get('PLEX_TOKEN')
PLEX_PLAYLIST_NAME = _config.get('PLEX_PLAYLIST_NAME', 'ListenBrainz Weekly Discovery')
HTTP_PORT = int(_config.get('HTTP_PORT', 8000))
PLEX_DAYS_FILTER = int(_config.get('PLEX_DAYS_FILTER', 14))
LIDARR_UPDATE_INTERVAL = int(_config.get('LIDARR_UPDATE_INTERVAL', 86400))
PLEX_UPDATE_INTERVAL = int(_config.get('PLEX_UPDATE_INTERVAL', 86400))
LIDARR_UPDATE_INTERVAL = int(_config.get('LIDARR_UPDATE_INTERVAL', 86400))  # seconds
PLEX_UPDATE_INTERVAL = int(_config.get('PLEX_UPDATE_INTERVAL', 86400))  # seconds

# Legacy compatibility
OUTPUT_FILE = "lidarr_custom_list.json"
