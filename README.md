# DEPRECATED -- FUNCTIONALITY WILL BE MOVED TO NEW PROJECT CALLED [DUCTARR](https://github.com/DeviantEng/ductarr) (NAME CHANGE LIKELY)

# ListenBrainz to Lidarr and Plex Integration

Automatically sync your ListenBrainz recommendations to create:
- **Lidarr custom import lists** for automated music discovery
- **Plex playlists** from your personalized ListenBrainz playlists (Daily Jams, Weekly Jams, Weekly Exploration)

## Features

- 🎵 **Multiple Plex Playlists**: Automatically creates and updates Daily Jams, Weekly Jams, and Weekly Exploration playlists
- 📚 **Lidarr Integration**: Provides a custom import list of artists from your ListenBrainz Weekly Exploration playlist
- 🔄 **Automatic Updates**: Configurable refresh intervals for both Lidarr and Plex
- 🌐 **HTTP API**: Built-in web server to host json list for Lidarr integration
- 📊 **Status Monitoring**: Health check and status endpoints
- 🐳 **Docker Ready**: Runs in a container with minimal configuration

## Requirements

### Essential
- **ListenBrainz account** with active scrobbling
  - You must be actively submitting listens to ListenBrainz
  - ListenBrainz needs listening history to generate personalized playlists
  - See [ListenBrainz tools](https://listenbrainz.org/add-data/) for scrobbling options (Plex, Spotify, music players, etc.)
- **MetaBrainz API token** for authentication
  - Get from [ListenBrainz Settings](https://listenbrainz.org/settings/) → API Tokens

### Runtime
- **Docker** (recommended) or Python 3.11+

### Optional Services
- **Plex Media Server** - Required only for playlist creation features
- **Lidarr** - Required only for artist import list features
- **Local MusicBrainz Mirror** - Dramatically improves performance
  - Removes API rate limiting (1 request/second on public API)
  - See [Self-Hosted MusicBrainz Mirror Setup Guide](https://github.com/blampe/hearring-aid/blob/main/docs/self-hosted-mirror-setup.md)

### ListenBrainz Playlist Requirements
For the playlists to be available:
- Must scrobble listens from Plex or some other source
  - [eavesdrop.fm](https://eavesdrop.fm/) can easily generate a webhook URL to be configured in Plex
- **Daily Jams**: Must enable list by creation following the troi-bot user; [GUIDE HERE](https://community.metabrainz.org/t/would-you-like-to-test-drive-our-first-recommendations-feature/626352)
- **Weekly Jams**: Requires at least a week of listening history
- **Weekly Exploration**: Requires sufficient listening history for recommendations (typically 2+ weeks)

Without sufficient listening data, ListenBrainz won't generate these playlists and the Plex playlist creation will skip them.

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
      - HTTP_PORT=8000   # python web server port
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
| `METABRAINZ_TOKEN` | API authentication token | [ListenBrainz Settings](https://listenbrainz.org/settings/) → User Token |

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
| `MB_MIRROR` | `musicbrainz.org` | MusicBrainz server for artist lookup (use local mirror for faster processing; `192.168.1.10:5000`) |
| `HTTP_PORT` | `8000` | Port for HTTP API server |
| `LIDARR_UPDATE_INTERVAL` | `86400` | How often to refresh Lidarr data (seconds) |
| `PLEX_UPDATE_INTERVAL` | `86400` | How often to update Plex playlists (seconds) |
| `ENABLE_LOGGING` | `FALSE` | Enable file logging to `/app/data/logs/` |

## Integration Setup

### Lidarr Configuration

1. Go to **Settings → Import Lists → Add List → Custom List**
2. Configure:
   - **Name**: `ListenBrainz Recommendations` (or your preference)
   - **List URL**: `http://your-docker-host:8000/`
3. Set your preferences:
   - **Monitor**: Artist and All Albums (or your preference)
   - **Quality Profile**: Your preferred quality
   - **Tags**: Optional tags for organization
4. Test and Save

The list will import unique artists based on your ListenBrainz listening history and recommendations.

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

### Lidarr Custom List Format

The `/` endpoint returns a JSON array in the format expected by Lidarr's Custom Import List:

```json
[
  {
    "MusicBrainzId": "65f4f0c5-ef9e-490c-aee3-909e7ae6b2ab",
    "ArtistName": "Metallica"
  },
  {
    "MusicBrainzId": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
    "ArtistName": "Radiohead"
  },
  {
    "MusicBrainzId": "9c9f1380-2516-4fc9-a3e6-f9f61941d090",
    "ArtistName": "Muse"
  }
]
```

**Important Notes:**
- The array must be at the root level (not wrapped in an object)
- `MusicBrainzId` is the only required field for Lidarr to function
- `ArtistName` is optional but helpful for debugging and human readability

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
  - MusicBrainz API response time
  - Your internet connection
- **Public MusicBrainz API** is rate-limited to 1 request/second
  - Processing 200 artists takes ~3-4 minutes just for API calls
- **Using a local MusicBrainz mirror** dramatically improves performance:
  - No rate limiting (10-20x faster processing)
  - More reliable (no network latency)
  - See [Self-Hosted MusicBrainz Mirror Setup Guide](https://github.com/blampe/hearring-aid/blob/main/docs/self-hosted-mirror-setup.md)
- The HTTP server starts immediately, returning empty data until processing completes
- Subsequent updates are typically much faster (only processing changes)

## Development

```bash
# Clone the repository
git clone https://github.com/DeviantEng/lb-lidarr-plex.git
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

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
