import os
import logging
from datetime import datetime

# Use different paths for local vs Docker
if os.path.exists("/app"):
    # Docker environment
    CONFIG_PATH = "/app/data/config.env"
    LOG_DIR = "/app/data/logs"
else:
    # Local development
    CONFIG_PATH = "./config.env"
    LOG_DIR = "./logs"

def setup_logging(enable_logging=False):
    """Setup logging configuration"""
    if not enable_logging:
        # Disable logging by setting level to CRITICAL+1
        logging.getLogger().setLevel(logging.CRITICAL + 1)
        return
    
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Generate log filename with date
    log_filename = f"listenbrainz-integration-{datetime.now().strftime('%Y-%m-%d')}.log"
    log_path = os.path.join(LOG_DIR, log_filename)
    
    # Configure logging - just use INFO level since we don't have different log levels in the app
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Set up both file and console logging
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_path, mode='a', encoding='utf-8'),
            logging.StreamHandler()  # Keep console output
        ]
    )
    
    print(f"📝 Logging enabled: {log_path}")

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
        "PLEX_BASE_URL": os.getenv("PLEX_BASE_URL"),
        "PLEX_TOKEN": os.getenv("PLEX_TOKEN"),
        "HTTP_PORT": os.getenv("HTTP_PORT"),
        "LIDARR_UPDATE_INTERVAL": os.getenv("LIDARR_UPDATE_INTERVAL"),
        "PLEX_UPDATE_INTERVAL": os.getenv("PLEX_UPDATE_INTERVAL"),
        # Multi-playlist configuration
        "PLEX_DAILY_JAMS_NAME": os.getenv("PLEX_DAILY_JAMS_NAME"),
        "PLEX_WEEKLY_JAMS_NAME": os.getenv("PLEX_WEEKLY_JAMS_NAME"), 
        "PLEX_WEEKLY_EXPLORATION_NAME": os.getenv("PLEX_WEEKLY_EXPLORATION_NAME"),
        # Logging configuration
        "ENABLE_LOGGING": os.getenv("ENABLE_LOGGING"),
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
        "HTTP_PORT": "8000",
        "LIDARR_UPDATE_INTERVAL": "86400",  # 24 hours in seconds
        "PLEX_UPDATE_INTERVAL": "86400",    # 24 hours in seconds
        # Multi-playlist configuration
        "PLEX_DAILY_JAMS_NAME": "ListenBrainz Daily Jams",
        "PLEX_WEEKLY_JAMS_NAME": "ListenBrainz Weekly Jams", 
        "PLEX_WEEKLY_EXPLORATION_NAME": "ListenBrainz Weekly Discovery",
        "ENABLE_LOGGING": "FALSE",
    }

    for key, default_value in defaults.items():
        if key not in config or not config[key]:
            config[key] = default_value
            config_updated = True

    # Save config file if it was updated or doesn't exist
    if config_updated or not os.path.isfile(CONFIG_PATH):
        save_config(config)

    # Setup logging based on configuration
    enable_logging = config.get('ENABLE_LOGGING', 'FALSE').strip().lower() == 'true'
    setup_logging(enable_logging)

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
        f.write(f"PLEX_DAILY_JAMS_NAME={config.get('PLEX_DAILY_JAMS_NAME', 'ListenBrainz Daily Jams')}\n")
        f.write(f"PLEX_WEEKLY_JAMS_NAME={config.get('PLEX_WEEKLY_JAMS_NAME', 'ListenBrainz Weekly Jams')}\n")
        f.write(f"PLEX_WEEKLY_EXPLORATION_NAME={config.get('PLEX_WEEKLY_EXPLORATION_NAME', 'ListenBrainz Weekly Discovery')}\n\n")

        f.write("# Application Settings\n")
        f.write(f"HTTP_PORT={config.get('HTTP_PORT', '8000')}\n")
        f.write(f"LIDARR_UPDATE_INTERVAL={config.get('LIDARR_UPDATE_INTERVAL', '86400')}\n")
        f.write(f"PLEX_UPDATE_INTERVAL={config.get('PLEX_UPDATE_INTERVAL', '86400')}\n\n")

        f.write("# Logging Settings\n")
        f.write(f"ENABLE_LOGGING={config.get('ENABLE_LOGGING', 'FALSE')}\n")

    print(f"Configuration saved to {CONFIG_PATH}")

# Load configuration on import
_config = load_config()

# Export configuration variables
USER = _config.get('LB_USER')
METABRAINZ_TOKEN = _config.get('METABRAINZ_TOKEN')
MB_MIRROR = _config.get('MB_MIRROR', 'musicbrainz.org')
PLEX_BASE_URL = _config.get('PLEX_BASE_URL')
PLEX_TOKEN = _config.get('PLEX_TOKEN')
# Multi-playlist configuration
PLEX_DAILY_JAMS_NAME = _config.get('PLEX_DAILY_JAMS_NAME', 'ListenBrainz Daily Jams')
PLEX_WEEKLY_JAMS_NAME = _config.get('PLEX_WEEKLY_JAMS_NAME', 'ListenBrainz Weekly Jams')
PLEX_WEEKLY_EXPLORATION_NAME = _config.get('PLEX_WEEKLY_EXPLORATION_NAME', 'ListenBrainz Weekly Discovery')

HTTP_PORT = int(_config.get('HTTP_PORT', 8000))
LIDARR_UPDATE_INTERVAL = int(_config.get('LIDARR_UPDATE_INTERVAL', 86400))
PLEX_UPDATE_INTERVAL = int(_config.get('PLEX_UPDATE_INTERVAL', 86400))

# Logging configuration
ENABLE_LOGGING = _config.get('ENABLE_LOGGING', 'FALSE').strip().lower() == 'true'

# Calculate LOCAL_MB_MIRROR after MB_MIRROR is properly loaded from config
LOCAL_MB_MIRROR = MB_MIRROR != 'musicbrainz.org'  # True if using a local mirror

# Legacy compatibility
OUTPUT_FILE = "lidarr_custom_list.json"
