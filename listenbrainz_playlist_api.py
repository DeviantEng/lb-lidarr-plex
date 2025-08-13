import requests
from config import METABRAINZ_TOKEN

def get_user_playlists(user):
    """
    Get all playlists for a user from ListenBrainz

    Args:
        user (str): ListenBrainz username

    Returns:
        list: List of playlist metadata dictionaries
    """
    url = f"https://api.listenbrainz.org/1/user/{user}/playlists"
    headers = {}

    if METABRAINZ_TOKEN:
        headers["Authorization"] = f"Token {METABRAINZ_TOKEN}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        playlists = data.get("payload", {}).get("playlists", [])
        return playlists

    except requests.exceptions.RequestException as e:
        print(f"Error fetching user playlists: {e}")
        return []

def find_weekly_exploration_playlist(user):
    """
    Find the "Weekly Exploration" playlist for a user

    Args:
        user (str): ListenBrainz username

    Returns:
        dict: Playlist metadata if found, None otherwise
    """
    playlists = get_user_playlists(user)

    # Look for playlists with "weekly exploration" in the name (case insensitive)
    for playlist in playlists:
        title = playlist.get("playlist", {}).get("title", "").lower()
        if "weekly exploration" in title:
            return playlist

    # Also check for other variations
    for playlist in playlists:
        title = playlist.get("playlist", {}).get("title", "").lower()
        if any(term in title for term in ["weekly", "exploration", "discover"]):
            print(f"🔍 Found potential weekly playlist: {playlist.get('playlist', {}).get('title', 'Unknown')}")
            return playlist

    return None

def get_playlist_tracks(playlist_mbid):
    """
    Get all tracks from a specific playlist

    Args:
        playlist_mbid (str): The playlist MBID

    Returns:
        list: List of track dictionaries with recording MBIDs
    """
    url = f"https://api.listenbrainz.org/1/playlist/{playlist_mbid}"
    headers = {}

    if METABRAINZ_TOKEN:
        headers["Authorization"] = f"Token {METABRAINZ_TOKEN}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract tracks from JSPF format
        playlist_data = data.get("playlist", {})
        tracks = playlist_data.get("track", [])

        print(f"🔍 Raw playlist response contains {len(tracks)} tracks")

        # Convert to our expected format
        track_list = []
        for i, track in enumerate(tracks):
            # Get recording MBID from track identifier
            identifier = track.get("identifier", "")

            # Handle different identifier formats (could be string or list)
            recording_mbid = None
            identifiers_to_check = []

            if isinstance(identifier, list):
                identifiers_to_check = identifier
            elif isinstance(identifier, str):
                identifiers_to_check = [identifier]

            # Try to find MusicBrainz recording identifier
            for ident in identifiers_to_check:
                if isinstance(ident, str):
                    if ident.startswith("https://musicbrainz.org/recording/"):
                        recording_mbid = ident.replace("https://musicbrainz.org/recording/", "")
                        break
                    elif ident.startswith("musicbrainz:recording:"):
                        recording_mbid = ident.replace("musicbrainz:recording:", "")
                        break

            # If still no MBID, try extension metadata
            if not recording_mbid:
                extension = track.get("extension", {})
                mb_extension = extension.get("https://musicbrainz.org/doc/jspf#track", {})
                recording_mbid = mb_extension.get("recording_mbid")

            if recording_mbid:
                track_list.append({
                    "recording_mbid": recording_mbid,
                    "title": track.get("title", ""),
                    "creator": track.get("creator", ""),
                    "album": track.get("album", "")
                })

                # Debug: show first few tracks
                if len(track_list) <= 3:
                    print(f"  Track {len(track_list)}: {track.get('creator', 'Unknown')} - {track.get('title', 'Unknown')} ({recording_mbid})")
            else:
                print(f"⚠️  Could not extract recording MBID from track {i+1}: {track.get('title', 'Unknown')} by {track.get('creator', 'Unknown')}")
                # Debug: show the identifier structure for the first few failed tracks
                if i < 3:
                    print(f"    Identifier structure: {identifier}")
                    print(f"    Extension structure: {track.get('extension', {})}")

        print(f"✅ Successfully extracted {len(track_list)} tracks with MBIDs out of {len(tracks)} total tracks")
        return track_list

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching playlist tracks: {e}")
        return []

def get_weekly_exploration_tracks(user):
    """
    Get tracks from the user's Weekly Exploration playlist
    Since Weekly Exploration playlists are created by the system, we need to use a different approach

    Args:
        user (str): ListenBrainz username

    Returns:
        list: List of track dictionaries compatible with existing code format
    """
    print(f"📥 Fetching Weekly Exploration playlist for user: {user}")

    # Weekly Exploration playlists are created by ListenBrainz system, not the user
    # We need to search for playlists created FOR the user, not BY the user

    # Try to get playlists created for the user
    try:
        url = f"https://api.listenbrainz.org/1/user/{user}/playlists/createdfor"
        headers = {}

        if METABRAINZ_TOKEN:
            headers["Authorization"] = f"Token {METABRAINZ_TOKEN}"

        print(f"🔍 Searching for playlists created for user: {user}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        playlists = data.get("payload", {}).get("playlists", [])
        print(f"📋 Found {len(playlists)} playlists created for user")

        # Look for the Weekly Exploration playlist
        weekly_playlist = None
        for playlist in playlists:
            playlist_info = playlist.get("playlist", {})
            title = playlist_info.get("title", "").lower()
            if "weekly exploration" in title:
                weekly_playlist = playlist
                break

        if weekly_playlist:
            playlist_info = weekly_playlist.get("playlist", {})
            playlist_title = playlist_info.get("title", "Unknown")
            playlist_mbid = playlist_info.get("identifier", "").replace("https://listenbrainz.org/playlist/", "")

            print(f"✅ Found Weekly Exploration playlist: {playlist_title}")
            print(f"📋 Playlist MBID: {playlist_mbid}")

            # Get tracks from the playlist
            tracks = get_playlist_tracks(playlist_mbid)

            if not tracks:
                print(f"❌ No tracks found in playlist")
                return []

            print(f"🎵 Found {len(tracks)} tracks in Weekly Exploration playlist")

            # Convert to format expected by existing code
            recommendations = []
            for track in tracks:
                recommendations.append({
                    "recording_mbid": track["recording_mbid"],
                    "score": 1.0  # All tracks from playlist get equal weight
                })

            return recommendations

    except Exception as e:
        print(f"⚠️  Could not fetch 'created for' playlists: {e}")

    # Fallback: If we know a specific playlist MBID, use it directly
    # This is a temporary solution - you could hardcode your current playlist MBID here
    print(f"🔄 Trying direct playlist access as fallback...")

    # For now, let's try the known playlist ID from your URL
    known_playlist_id = "11cba6bd-0399-4be7-990a-58ff13b23a0c"
    tracks = get_playlist_tracks(known_playlist_id)

    if tracks:
        print(f"✅ Successfully fetched {len(tracks)} tracks from known Weekly Exploration playlist")
        recommendations = []
        for track in tracks:
            recommendations.append({
                "recording_mbid": track["recording_mbid"],
                "score": 1.0
            })
        return recommendations
    else:
        print(f"❌ Could not access Weekly Exploration playlist")
        return []

def get_recent_recommendations(user, days=14):
    """
    Get tracks from Weekly Exploration playlist (replaces the old recommendation API)

    Args:
        user (str): ListenBrainz username
        days (int): Ignored - we get the current weekly playlist

    Returns:
        list: Tracks from Weekly Exploration playlist
    """
    return get_weekly_exploration_tracks(user)

def get_all_recommendations(user):
    """
    For Lidarr, we still want to use the collaborative filtering API
    to get a broad range of artists for discovery

    Args:
        user (str): ListenBrainz username

    Returns:
        list: Full list of recommendations for artist discovery
    """
    print("📥 Fetching ALL recommendations for Lidarr artist discovery...")

    # Use the original collaborative filtering API for broad artist discovery
    offset = 0
    count = 100
    all_recs = []
    headers = {}

    if METABRAINZ_TOKEN:
        headers["Authorization"] = f"Token {METABRAINZ_TOKEN}"

    while True:
        url = f"https://api.listenbrainz.org/1/cf/recommendation/user/{user}/recording"
        params = {"count": count, "offset": offset}

        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            recs = data.get("payload", {}).get("mbids", [])

            # Get all recommendations (no null_only filtering)
            all_recs.extend(recs)

            # Check if we've reached the end
            if len(data.get("payload", {}).get("mbids", [])) < count:
                break

            offset += count

        except requests.exceptions.RequestException as e:
            print(f"Error fetching recommendations: {e}")
            break

    return all_recs
