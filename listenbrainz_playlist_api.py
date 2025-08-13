import requests
from config import METABRAINZ_TOKEN

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
        
        print(f"📋 Raw playlist response contains {len(tracks)} tracks")
        
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

def get_user_playlists(user, include_private=True):
    """
    Get all playlists for a user
    
    Args:
        user (str): ListenBrainz username
        include_private (bool): Whether to include private playlists (requires auth)
    
    Returns:
        list: List of playlist metadata dictionaries
    """
    print(f"🔍 Fetching playlists for user: {user}")
    
    url = f"https://api.listenbrainz.org/1/user/{user}/playlists"
    headers = {}
    
    if METABRAINZ_TOKEN and include_private:
        headers["Authorization"] = f"Token {METABRAINZ_TOKEN}"
    
    all_playlists = []
    offset = 0
    count = 50  # API default
    
    try:
        while True:
            params = {"count": count, "offset": offset}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            playlists = data.get("playlists", [])
            if not playlists:
                break
                
            all_playlists.extend(playlists)
            
            # Check if we've got all playlists
            if len(playlists) < count:
                break
                
            offset += count
        
        print(f"📋 Found {len(all_playlists)} total playlists for user {user}")
        return all_playlists
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching user playlists: {e}")
        return []

def get_user_recommendation_playlists(user):
    """
    Get recommendation playlists created for a user (Weekly Exploration, Daily Jams, etc.)
    
    Args:
        user (str): ListenBrainz username
    
    Returns:
        list: List of recommendation playlist metadata dictionaries
    """
    print(f"🎯 Fetching recommendation playlists for user: {user}")
    
    url = f"https://api.listenbrainz.org/1/user/{user}/playlists/createdfor"
    headers = {}
    
    if METABRAINZ_TOKEN:
        headers["Authorization"] = f"Token {METABRAINZ_TOKEN}"
    
    all_playlists = []
    offset = 0
    count = 50
    
    try:
        while True:
            params = {"count": count, "offset": offset}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            playlists = data.get("playlists", [])
            if not playlists:
                break
                
            all_playlists.extend(playlists)
            
            if len(playlists) < count:
                break
                
            offset += count
        
        print(f"🎯 Found {len(all_playlists)} recommendation playlists for user {user}")
        return all_playlists
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching recommendation playlists: {e}")
        return []

def find_weekly_exploration_playlist(user):
    """
    Find the most recent Weekly Exploration playlist for a user.
    Weekly Exploration playlists are system-generated, so they're only found in "created for" playlists.
    
    Args:
        user (str): ListenBrainz username
    
    Returns:
        dict or None: Playlist metadata if found, None otherwise
    """
    print(f"🔥 Searching for Weekly Exploration playlist for user: {user}")
    
    # Get recommendation playlists (created for user) - this is where system-generated playlists live
    rec_playlists = get_user_recommendation_playlists(user)
    
    # Look for Weekly Exploration in recommendation playlists
    weekly_exploration_playlists = []
    for playlist_wrapper in rec_playlists:
        # Extract the actual playlist data from the wrapper
        playlist = playlist_wrapper.get("playlist", {})
        title = playlist.get("title", "").lower()
        
        # Look for various possible names for weekly exploration playlists
        if any(term in title for term in ["weekly exploration", "weekly discovery"]):
            weekly_exploration_playlists.append(playlist)
    
    if not weekly_exploration_playlists:
        print("❌ No Weekly Exploration playlist found in system-generated playlists")
        print("📋 This may mean:")
        print("   - User doesn't have enough listening history for recommendations")
        print("   - Weekly playlists haven't been generated yet")
        print("   - User account may not be eligible for recommendations")
        
        # Debug: Show what playlists were found
        print("🔍 Available recommendation playlists:")
        for playlist_wrapper in rec_playlists:
            playlist = playlist_wrapper.get("playlist", {})
            title = playlist.get("title", "Unknown")
            print(f"   - \"{title}\"")
        
        return None
    
    # Sort by date and get the most recent one
    # The API should return playlists in order, but let's be safe
    if len(weekly_exploration_playlists) > 1:
        print(f"📋 Found {len(weekly_exploration_playlists)} Weekly Exploration playlists, using the first one")
        # Could add more sophisticated sorting here if needed
    
    selected_playlist = weekly_exploration_playlists[0]
    playlist_title = selected_playlist.get('title', 'Unknown')
    playlist_id = selected_playlist.get('identifier', '').split('/')[-1] if selected_playlist.get('identifier') else 'Unknown'
    
    print(f"✅ Found Weekly Exploration playlist: '{playlist_title}' (ID: {playlist_id})")
    
    return selected_playlist

def find_playlist_by_type(user, search_terms, prefer_current_week=True):
    """
    Find a playlist by type (Daily Jams, Weekly Jams, Weekly Exploration, etc.)
    
    Args:
        user (str): ListenBrainz username
        search_terms (list): List of terms to search for in playlist titles
        prefer_current_week (bool): Whether to prefer current week over previous weeks
    
    Returns:
        dict or None: Playlist metadata if found, None otherwise
    """
    print(f"🔍 Searching for playlist with terms: {search_terms}")
    
    # Get recommendation playlists (created for user)
    rec_playlists = get_user_recommendation_playlists(user)
    
    # Look for playlists matching the search terms
    matching_playlists = []
    for playlist_wrapper in rec_playlists:
        playlist = playlist_wrapper.get("playlist", {})
        title = playlist.get("title", "").lower()
        
        # Check if any search term is in the title
        if any(term.lower() in title for term in search_terms):
            matching_playlists.append(playlist)
    
    if not matching_playlists:
        print(f"❌ No playlist found matching terms: {search_terms}")
        return None
    
    if prefer_current_week and len(matching_playlists) > 1:
        # Sort by date (most recent first) to prefer current week
        try:
            matching_playlists.sort(key=lambda p: p.get('date', ''), reverse=True)
            print(f"📅 Found {len(matching_playlists)} matching playlists, using most recent")
        except:
            print(f"📋 Found {len(matching_playlists)} matching playlists, using first one")
    
    selected_playlist = matching_playlists[0]
    playlist_title = selected_playlist.get('title', 'Unknown')
    playlist_id = selected_playlist.get('identifier', '').split('/')[-1] if selected_playlist.get('identifier') else 'Unknown'
    
    print(f"✅ Found playlist: '{playlist_title}' (ID: {playlist_id})")
    return selected_playlist

def get_tracks_by_playlist_type(user, search_terms, prefer_current_week=True):
    """
    Get tracks from a playlist by type
    
    Args:
        user (str): ListenBrainz username
        search_terms (list): List of terms to search for in playlist titles
        prefer_current_week (bool): Whether to prefer current week over previous weeks
    
    Returns:
        list: List of track dictionaries compatible with existing code format
    """
    print(f"🔥 Fetching tracks for playlist type: {search_terms}")
    
    # Find the playlist
    playlist = find_playlist_by_type(user, search_terms, prefer_current_week)
    if not playlist:
        print(f"❌ Could not find playlist matching: {search_terms}")
        return []
    
    # Extract playlist ID from the identifier URL
    playlist_identifier = playlist.get("identifier", "")
    if not playlist_identifier:
        print("❌ Could not extract playlist identifier")
        return []
    
    # Extract the UUID from the URL
    playlist_id = playlist_identifier.split('/')[-1] if '/' in playlist_identifier else playlist_identifier
    
    print(f"📋 Using playlist ID: {playlist_id}")
    
    # Get tracks from the playlist
    tracks = get_playlist_tracks(playlist_id)
    
    if tracks:
        print(f"✅ Successfully fetched {len(tracks)} tracks from playlist")
        recommendations = []
        for track in tracks:
            recommendations.append({
                "recording_mbid": track["recording_mbid"],
                "score": 1.0
            })
        return recommendations
    else:
        print(f"❌ Could not access playlist tracks")
        return []

# Updated function using the new generic approach that returns metadata
def get_weekly_exploration_tracks(user):
    """
    Get tracks from the user's most recent Weekly Exploration playlist
    
    Args:
        user (str): ListenBrainz username
    
    Returns:
        tuple: (tracks_list, playlist_metadata) or ([], None) if not found
    """
    return get_tracks_by_playlist_type(user, ["weekly exploration"], prefer_current_week=True)

def get_daily_jams_tracks(user):
    """
    Get tracks from the user's most recent Daily Jams playlist
    
    Args:
        user (str): ListenBrainz username
    
    Returns:
        tuple: (tracks_list, playlist_metadata) or ([], None) if not found
    """
    return get_tracks_by_playlist_type(user, ["daily jams"], prefer_current_week=True)

def get_weekly_jams_tracks(user):
    """
    Get tracks from the user's most recent Weekly Jams playlist
    
    Args:
        user (str): ListenBrainz username
    
    Returns:
        tuple: (tracks_list, playlist_metadata) or ([], None) if not found
    """
    return get_tracks_by_playlist_type(user, ["weekly jams"], prefer_current_week=True)

def get_all_recommendations(user):
    """
    For Lidarr, we use the collaborative filtering API
    to get a broad range of artists for discovery
    
    Args:
        user (str): ListenBrainz username
    
    Returns:
        list: Full list of recommendations for artist discovery
    """
    print("🔥 Fetching ALL recommendations for Lidarr artist discovery...")
    
    # Use the collaborative filtering API for broad artist discovery
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
            
            # Get all recommendations (no filtering)
            all_recs.extend(recs)

            # Check if we've reached the end
            if len(data.get("payload", {}).get("mbids", [])) < count:
                break
                
            offset += count
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching recommendations: {e}")
            break

    return all_recs
