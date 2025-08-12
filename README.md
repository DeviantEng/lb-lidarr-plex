# ListenBrainz to Lidarr and Plex Integration

A Docker application that fetches your ListenBrainz weekly recommendations and:
1. **Serves a JSON API** for Lidarr custom import lists (artist MBIDs)
2. **Creates Plex playlists** with matched tracks from your library

## Features

- 🎵 **Dual Integration**: Lidarr (artist discovery from ALL historical data) + Plex (playlist creation from recent tracks)
- 🐋 **Docker Ready**: Complete containerized solution
- ⚙️ **Flexible Config**: File-based or environment variable configuration
- 🌐 **HTTP API**: RESTful endpoint for Lidarr integration
- 🎯 **Smart Matching**: Fuzzy track matching with scoring system
- 📊 **Health Monitoring**: Built-in health checks and status endpoints
- 📅 **Date Filtering**: Lidarr gets all artists, Plex gets recent tracks (configurable days)

## Quick Start

### 1. Using Docker Compose (Recommended)

```bash
# Clone and configure
git clone <repo>
cd lb-to-lidarr_plex

# Edit docker-compose.yml with your credentials
vim docker-compose.yml

# Start the service
docker-compose up -d
```

### 2. Using Docker Swarm Stack

```bash
# Edit docker-stack.yml with your credentials
vim docker-stack.yml

# Deploy the stack
docker stack deploy -c docker-stack.yml lb-lidarr-plex

# Check status
docker service ls
docker service logs lb-lidarr-plex_lb-lidarr-plex
```

### 3. Using Docker Run

```bash
docker run -d \
  --name lb-lidarr-plex \
  -p 8000:8000 \
  -v ./config:/config \
  -e LB_USER=your_username \
  -e METABRAINZ_TOKEN=your_token \
  -e PLEX_BASE_URL=http://plex:32400 \
  -e PLEX_TOKEN=your_plex_token \
  ghcr.io/devianteng/lb-lidarr-plex:latest
```

## Configuration

Configuration is loaded in this priority order:
1. `/config/config.env` file (highest priority)
2. Docker environment variables 
3. Default values (lowest priority)

### Required Variables

```bash
LB_USER=your_listenbrainz_username
METABRAINZ_TOKEN=your_metabrainz_token
```

### Optional Variables

```bash
# MusicBrainz
MB_MIRROR=musicbrainz.org  # or your local mirror like 192.168.1.100:5000

# Plex (required for playlist creation)
PLEX_BASE_URL=http://your-plex-server:32400
PLEX_TOKEN=your_plex_token

# Application
HTTP_PORT=8000
NULLONLY=FALSE  # Set to TRUE to only include unlistened recommendations
PLEX_DAYS_FILTER=14  # Days to look back for Plex playlists (Lidarr uses all historical data)
LIDARR_UPDATE_INTERVAL=86400  # Lidarr update interval in seconds (24 hours)
PLEX_UPDATE_INTERVAL=86400    # Plex update interval in seconds (24 hours)
```

## Usage

### Server Mode (Default)
Runs HTTP server for continuous Lidarr integration:

```bash
docker run listenbrainz-integration
# or
python main.py --mode server
```

**Endpoints:**
- `http://localhost:8000/` - Lidarr custom import list (JSON)
- `http://localhost:8000/health` - Health check and status

### One-Time Mode
Process once and save to file:

```bash
python main.py --mode once
```

## Lidarr Integration

1. **Add Custom Import List** in Lidarr:
   - Type: `Custom`
   - URL: `http://your-docker-host:8000/`
   - Method: `GET`

2. **Configure Schedule**:
   - Set update interval (e.g., daily/weekly)
   - Enable automatic import

## Plex Integration

The application automatically creates weekly playlists in Plex:
- **Playlist Name**: `ListenBrainz Weekly - YYYY-MM-DD`
- **Track Source**: Only tracks added in the last 14 days (configurable)
- **Track Limit**: 50 tracks (configurable)
- **Matching**: Smart fuzzy matching with scoring
- **Updates**: New playlist created each run
- **Separate from Lidarr**: Lidarr uses ALL historical data for artist discovery

## API Response Format

### `/` (Lidarr Import List)
```json
{
  "artists": [
    {
      "MusicBrainzId": "artist-mbid-here",
      "title": "Artist Name"
    }
  ],
  "count": 25,
  "last_updated": "2025-01-12T10:30:00Z",
  "source": "ListenBrainz Weekly Recommendations"
}
```

### `/health` (Health Check)
```json
{
  "status": "healthy",
  "artists_count": 25,
  "last_updated": "2025-01-12T10:30:00Z",
  "config": {
    "user": "your_username",
    "null_only": true,
    "plex_configured": true
  }
}
```

## File Structure

```
/app/
├── main.py                    # Main application
├── config.py                  # Configuration management
├── listenbrainz_api.py        # ListenBrainz integration
├── musicbrainz_api.py         # MusicBrainz integration
├── listenbrainz_to_plex.py    # Plex integration
├── plex_api.py                # Plex search functionality
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
├── docker-compose.yml        # Compose configuration
└── docker-stack.yml          # Docker Swarm stack

/config/
└── config.env               # Persistent configuration
```

## Development

### Local Development
```bash
pip install -r requirements.txt
export LB_USER=your_username
export METABRAINZ_TOKEN=your_token
python main.py --mode once
```

### Building Docker Image
```bash
docker build -t listenbrainz-integration .
```

## Troubleshooting

### Check Service Health
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
docker-compose logs -f
```

### Common Issues

1. **No recommendations found**: Check LB_USER and METABRAINZ_TOKEN
2. **Plex playlist not created**: Verify PLEX_BASE_URL and PLEX_TOKEN
3. **Lidarr can't connect**: Check firewall and port configuration
4. **MusicBrainz errors**: Verify MB_MIRROR setting

## License

MIT License - see LICENSE file for details.
