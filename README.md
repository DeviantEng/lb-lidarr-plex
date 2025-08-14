# ListenBrainz to Lidarr and Plex Integration

Automatically sync your ListenBrainz recommendations to create:
- **Lidarr custom import lists** for automated music discovery
- **Plex playlists** from your personalized ListenBrainz playlists (Daily Jams, Weekly Jams, Weekly Exploration)

## Features

- 🎵 **Multiple Plex Playlists**: Automatically creates and updates Daily Jams, Weekly Jams, and Weekly Exploration playlists
- 📚 **Lidarr Integration**: Provides a custom import list of ~150-200 recommended artists
- 🔄 **Automatic Updates**: Configurable refresh intervals for both Lidarr and Plex
- 🌐 **HTTP API**: Built-in web server for Lidarr integration
- 📊 **Status Monitoring**: Health check and status endpoints
- 🐳 **Docker Ready**: Runs in a container with minimal configuration

## Quick Start

### Docker Compose (Recommended)

1. Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  listenbrainz-integration:
    image: ghcr.io/devianteng/lb-lidarr-plex:latest
    container_name: listenbrainz-integration
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data  # Persistent storage for config and logs
    environment:
      # Required
      - LB_USER=your_listenbrainz_username
      - METABRAINZ_TOKEN=your_metabrainz_token
      
      # Optional - Plex Configuration
      - PLEX_BASE_URL=http://your-plex-server:32400
      - PLEX_TOKEN=your_plex_token
      
      # Optional - Playlist Names (defaults shown)
      - PLEX_DAILY_JAMS_NAME=ListenBrainz Daily Jams
      - PLEX_WEEKLY_JAMS_NAME=ListenBrainz Weekly Jams
      - PLEX_WEEKLY_EXPLORATION_NAME=ListenBrainz Weekly Discovery
      
      # Optional - Advanced Settings
      - MB_MIRROR=musicbrainz.org  # Or local mirror like 192.168.1.10:5000
      - HTTP_PORT=8000
      - LIDARR_UPDATE_INTERVAL=86400  # 24 hours in seconds
      - PLEX_UPDATE_INTERVAL=86400    # 24 hours in seconds
      - ENABLE_LOGGING=FALSE          # Set to TRUE for file logging
```

2. Start the container:
```bash
docker-compose up -d
```

### Docker Run

```bash
docker run -d \
  --name listenbrainz-integration \
  -p 8000:8000 \
  -v ./data:/app/data \
  -e LB_USER=your_username \
  -e METABRAINZ_TOKEN=your_token \
  -e PLEX_BASE_URL=http://plex:32400 \
  -e PLEX_TOKEN=your_plex_token \
  ghcr.io/devianteng/lb-lidarr-plex:latest
```

## Configuration

### Required Settings

| Variable | Description | How to Get |
|----------|-------------|------------|
| `LB_USER` | Your ListenBrainz username | Your profile URL: `listenbrainz.org/user/[username]` |
| `METABRAINZ_TOKEN` | API authentication token | [ListenBrainz Settings](https://listenbrainz.org/settings/) → API Tokens |

### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| **Plex Configuration** | | |
| `PLEX_BASE_URL` | - | Plex server URL (e.g., `http://192.168.1.100:32400`) |
| `PLEX_TOKEN` | - | [Find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) |
| `PLEX_DAILY_JAMS_NAME` | `ListenBrainz Daily Jams` | Name for Daily Jams playlist |
| `PLEX_WEEKLY_JAMS_NAME` | `ListenBrainz Weekly Jams` | Name for Weekly Jams playlist |
| `PLEX_WEEKLY_EXPLORATION_NAME` | `ListenBrainz Weekly Discovery` | Name for Weekly Exploration playlist |
| **Application Settings** | | |
| `MB_MIRROR` | `musicbrainz.org` | MusicBrainz server (use local mirror for faster processing) |
| `HTTP_PORT` | `8000` | Port for HTTP API server |
| `LIDARR_UPDATE_INTERVAL` | `86400` | How often to refresh Lidarr data (seconds) |
| `PLEX_UPDATE_INTERVAL` | `86400` | How often to update Plex playlists (seconds) |
| `ENABLE_LOGGING` | `FALSE` | Enable file logging to `/app/data/logs/` |

## Integration Setup

### Lidarr Configuration

1. Go to **Settings → Import Lists → Add List → Custom List**
2. Configure:
   - **Name**: `ListenBrainz Recommendations` (or your preference)
   - **URL**: `http://your-docker-host:8000/`
   - **Method**: GET
3. Set your preferences:
   - **Monitor**: Artist and All Albums (or your preference)
   - **Quality Profile**: Your preferred quality
   - **Tags**: Optional tags for organization
4. Test and Save

The list will import ~150-200 unique artists based on your ListenBrainz listening history and recommendations.

### Plex Playlists

Playlists are created automatically when Plex is configured. The app will:
- Create three playlists on first run (Daily Jams, Weekly Jams, Weekly Exploration)
- Update the same playlists on subsequent runs (replaces content)
- Match tracks from ListenBrainz with your Plex library
- Typically achieves 90-95% match rate if your library is well-tagged

## API Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `GET /` | Lidarr import list | JSON array of artists with MusicBrainzId |
| `GET /status` | Detailed status information | JSON object with counts, timestamps, and processing status |
| `GET /health` | Health check | JSON object with service status |

## Troubleshooting

### Check Service Status
```bash
# View container logs
docker logs listenbrainz-integration

# Check health endpoint
curl http://localhost:8000/health

# View current artist count
curl http://localhost:8000/status
```

### Common Issues

**No recommendations found**
- Verify `LB_USER` is correct
- Check `METABRAINZ_TOKEN` is valid
- Ensure you have sufficient listening history on ListenBrainz

**Plex playlists empty or missing**
- Verify `PLEX_BASE_URL` is accessible from the container
- Check `PLEX_TOKEN` is valid
- Ensure your Plex library has music that matches your ListenBrainz recommendations
- Check container logs for matching statistics

**Lidarr import fails**
- Wait for initial processing to complete (can take 10-15 minutes on first run)
- Check the endpoint returns a valid JSON array: `curl http://localhost:8000/`
- Ensure Lidarr can reach the container's IP and port

**Container keeps restarting**
- Initial processing takes time; the health endpoint is available immediately
- Check logs for specific errors: `docker logs listenbrainz-integration`

### Manual Testing
```bash
# Run once and exit (useful for testing)
docker run --rm \
  -e LB_USER=your_username \
  -e METABRAINZ_TOKEN=your_token \
  ghcr.io/devianteng/lb-lidarr-plex:latest \
  python main.py --mode once

# Test with custom intervals
docker run --rm \
  -e LB_USER=your_username \
  -e METABRAINZ_TOKEN=your_token \
  ghcr.io/devianteng/lb-lidarr-plex:latest \
  python main.py --mode daemon --lidarr-interval 3600 --plex-interval 7200
```

## How It Works

### For Lidarr (Artist Discovery)
1. Fetches collaborative filtering recommendations from ListenBrainz API
2. Processes all recommendations to extract unique artist MBIDs
3. Queries MusicBrainz for artist details
4. Serves JSON array at `http://localhost:8000/` for Lidarr import
5. Updates automatically based on configured interval

### For Plex (Playlist Creation)
1. Fetches your personalized playlists from ListenBrainz:
   - Daily Jams (daily personalized mix)
   - Weekly Jams (weekly favorites)
   - Weekly Exploration (discovery playlist)
2. Extracts track MBIDs from each playlist
3. Looks up track/artist information from MusicBrainz
4. Searches your Plex library for matching tracks
5. Creates or updates playlists with matched tracks
6. Updates automatically based on configured interval

## Performance Notes

- **Initial processing** can take 10-15 minutes depending on:
  - Number of recommendations
  - MusicBrainz API response time (public API is rate-limited to 1 request/second)
  - Your internet connection
- **Using a local MusicBrainz mirror** dramatically improves performance (no rate limiting)
- The HTTP server starts immediately, returning empty data until processing completes
- Subsequent updates are typically much faster (only processing changes)

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/lb-lidarr-plex.git
cd lb-lidarr-plex

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export LB_USER=your_username
export METABRAINZ_TOKEN=your_token
export PLEX_BASE_URL=http://localhost:32400
export PLEX_TOKEN=your_plex_token

# Run in development
python main.py --mode once  # Single run
python main.py --mode daemon  # Continuous mode

# Build Docker image locally
docker build -t lb-lidarr-plex:local .
```

## File Structure

```
/app/data/
├── config.env              # Persistent configuration
├── lidarr_custom_list.json # Cached artist list
└── logs/                   # Application logs (if enabled)
    └── listenbrainz-integration-YYYY-MM-DD.log
```

## Requirements

- **ListenBrainz account** with listening history
- **MetaBrainz API token** for authentication
- **Docker** or Python 3.11+
- **Plex Media Server** (optional, for playlist features)
- **Lidarr** (optional, for artist import features)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
