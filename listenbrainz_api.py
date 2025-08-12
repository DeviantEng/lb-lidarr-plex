import requests
from datetime import datetime, timedelta
from config import METABRAINZ_TOKEN

LISTENBRAINZ_API_URL = "https://api.listenbrainz.org/1/cf/recommendation/user"

def get_recommendations(user, null_only=True, days_filter=None):
    """
    Fetch recommendations from ListenBrainz for a given user
    
    Args:
        user (str): ListenBrainz username
        null_only (bool): Only return tracks that haven't been listened to
        days_filter (int): Only return tracks added within the last N days (None for all)
    
    Returns:
        list: List of recommendation dictionaries
    """
    offset = 0
    count = 100
    all_recs = []
    headers = {}
    
    if METABRAINZ_TOKEN:
        headers["Authorization"] = f"Token {METABRAINZ_TOKEN}"

    # Calculate cutoff date if filtering by days
    cutoff_date = None
    if days_filter:
        cutoff_date = datetime.now() - timedelta(days=days_filter)
        print(f"📅 Filtering recommendations to last {days_filter} days (since {cutoff_date.strftime('%Y-%m-%d')})")

    while True:
        url = f"{LISTENBRAINZ_API_URL}/{user}/recording"
        params = {"count": count, "offset": offset}
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            recs = data.get("payload", {}).get("mbids", [])
            
            if null_only:
                # Filter to only include tracks not previously listened to
                recs = [r for r in recs if r.get("latest_listened_at") is None]

            # Filter by date if specified
            if days_filter and cutoff_date:
                filtered_recs = []
                for rec in recs:
                    added_at = rec.get("added_at")
                    if added_at:
                        try:
                            # Parse the timestamp (assuming Unix timestamp)
                            added_date = datetime.fromtimestamp(added_at)
                            if added_date >= cutoff_date:
                                filtered_recs.append(rec)
                        except (ValueError, TypeError):
                            # If we can't parse the date, include it to be safe
                            filtered_recs.append(rec)
                    else:
                        # If no added_at field, include it to be safe
                        filtered_recs.append(rec)
                recs = filtered_recs

            all_recs.extend(recs)

            # Check if we've reached the end
            if len(data.get("payload", {}).get("mbids", [])) < count:
                break
                
            offset += count
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching recommendations: {e}")
            break

    return all_recs

def get_all_recommendations(user, null_only=True):
    """
    Get all recommendations for Lidarr artist discovery
    
    Args:
        user (str): ListenBrainz username
        null_only (bool): Only return tracks that haven't been listened to
    
    Returns:
        list: Full list of recommendations for artist discovery
    """
    print("📥 Fetching ALL recommendations for Lidarr artist discovery...")
    return get_recommendations(user, null_only=null_only, days_filter=None)

def get_recent_recommendations(user, null_only=True, days=14):
    """
    Get recent recommendations for Plex playlist creation
    
    Args:
        user (str): ListenBrainz username  
        null_only (bool): Only return tracks that haven't been listened to
        days (int): Number of days to look back
    
    Returns:
        list: Recent recommendations for playlist creation
    """
    print(f"📥 Fetching recommendations from last {days} days for Plex playlist...")
    return get_recommendations(user, null_only=null_only, days_filter=days)
