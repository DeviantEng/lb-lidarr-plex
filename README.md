# ListenBrainz to Lidarr and Plex Integration

Automatically sync your ListenBrainz data to create:
- **Lidarr artist lists** for music discovery
- **Plex playlists** from your Weekly Exploration recommendations

## Quick Start

### Docker Compose (Recommended)

```yaml
version: '3.8'
services:
  lb-lidarr-plex:
    image: ghcr.io/devianteng/lb-lidarr-plex:latest
    container_name: lb-lidarr-plex
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - LB_USER=your_listenbrainz_username
      - METABRAINZ_TOKEN=your_metabrainz_token
      - PLEX_BASE_URL=http://your-plex-server:32400
      - PLEX_TOKEN=your_plex_token
      - PLEX_PLAYLIST_NAME=ListenBrainz Weekly Discovery
    volumes:
      - ./config:/config
```

### Docker Run

```bash
docker run -d \
  --name lb-lidarr-plex \
  -p 8000:8000 \
  -e LB_USER=your_username \
  -e METABRAINZ_TOKEN=your_token \
  -e PLEX_BASE_URL=http://plex:32400 \
  -e PLEX_TOKEN=your_plex_token \
  ghcr.io/devianteng/lb-lidarr-plex:latest
```

## Configuration

### Required Settings
- `LB_USER` - Your ListenBrainz username
- `METABRAINZ_TOKEN` - Get from [ListenBrainz settings](https://listenbrainz.org/settings/)

### Optional Settings
- `PLEX_BASE_URL` - Plex server URL (for playlist creation)
- `PLEX_TOKEN` - Plex authentication token
- `PLEX_PLAYLIST_NAME` - Custom playlist name (default: "ListenBrainz Weekly Discovery")
- `HTTP_PORT` - API port (default: 8000)
- `LIDARR_UPDATE_INTERVAL` - Update frequency in seconds (default: 86400)
- `PLEX_UPDATE_INTERVAL` - Playlist update frequency in seconds (default: 86400)

## How It Works

### For Lidarr (Artist Discovery)
1. Fetches recommendations from ListenBrainz collaborative filtering
2. Extracts unique artist MBIDs (~150-200 artists)
3. Serves JSON API at `http://localhost:8000/` for Lidarr import

### For Plex (Weekly Playlist)
1. Gets tracks from your ListenBrainz Weekly Exploration playlist
2. Matches tracks in your Plex library (typically 95%+ success rate)
3. Creates/updates playlist with matched tracks

## Integration Setup

### Lidarr
1. Go to **Settings → Import Lists**
2. Add **Custom Import List**:
   - URL: `http://your-docker-host:8000/`
   - Method: GET
3. Set update schedule (daily/weekly recommended)

### Plex
Playlists are created automatically. The app will:
- Create playlist on first run
- Update same playlist on subsequent runs
- Use tracks from your Weekly Exploration playlist

## API Endpoints

- `GET /` - Lidarr artist import list (JSON)
- `GET /health` - Health check and status

## Requirements

- **ListenBrainz account** with listening history
- **MetaBrainz token** for API access
- **Plex server** (optional, for playlists)
- **Lidarr** (optional, for artist imports)

## Troubleshooting

### Check Status
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
docker logs lb-lidarr-plex
```

### Common Issues
- **No recommendations**: Verify LB_USER and METABRAINZ_TOKEN
- **Plex playlist empty**: Check PLEX_BASE_URL and PLEX_TOKEN
- **Lidarr can't connect**: Verify port 8000 is accessible

### Manual Run
```bash
# Run once and exit (useful for testing)
docker run --rm -e LB_USER=... -e METABRAINZ_TOKEN=... ghcr.io/devianteng/lb-lidarr-plex:latest python main.py --mode once
```

## Development

```bash
git clone <repo>
cd lb-lidarr-plex
pip install -r requirements.txt

# Set environment variables
export LB_USER=your_username
export METABRAINZ_TOKEN=your_token

# Run once
python main.py --mode once

# Run server
python main.py --mode daemon
```

## License

MIT License
