import requests
import time
from config import MB_MIRROR, LOCAL_MB_MIRROR

def get_musicbrainz_base_url():
    """Get the appropriate MusicBrainz base URL"""
    if LOCAL_MB_MIRROR:
        return f"http://{MB_MIRROR}/ws/2"
    else:
        return "https://musicbrainz.org/ws/2"

def get_artist_info(recording_mbid):
    """
    Get artist information from MusicBrainz for a recording MBID
    This is the legacy single-request method for backward compatibility
    
    Args:
        recording_mbid (str): MusicBrainz recording ID
    
    Returns:
        tuple: (artist_mbid, artist_name, track_title) or (None, None, None) if not found
    """
    base_url = get_musicbrainz_base_url()
    url = f"{base_url}/recording/{recording_mbid}"
    params = {"fmt": "json", "inc": "artists"}
    headers = {"User-Agent": "LB-to-Lidarr-Plex/1.0 ( https://github.com/your-repo )"}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        title = data.get("title", "")
        
        if "artist-credit" in data and data["artist-credit"]:
            artist = data["artist-credit"][0]["artist"]
            artist_mbid = artist.get("id")
            artist_name = artist.get("name", "")
            
            return artist_mbid, artist_name, title

        return None, None, None
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching artist info for {recording_mbid}: {e}")
        return None, None, None
    except (KeyError, IndexError) as e:
        print(f"Error parsing artist data for {recording_mbid}: {e}")
        return None, None, None

def get_artist_info_batch(recording_mbids, batch_size=50):
    """
    Get artist information for multiple recording MBIDs in batches (EFFICIENT METHOD)
    
    Args:
        recording_mbids (list): List of MusicBrainz recording IDs
        batch_size (int): Number of recordings to query per request (max 50 for public MB)
    
    Returns:
        dict: {recording_mbid: (artist_mbid, artist_name, track_title), ...}
    """
    base_url = get_musicbrainz_base_url()
    headers = {"User-Agent": "LB-to-Lidarr-Plex/1.0 ( https://github.com/your-repo )"}
    results = {}
    
    # Determine batch size based on whether using local mirror
    if LOCAL_MB_MIRROR:
        # Local mirrors can handle larger batches
        actual_batch_size = min(batch_size, 100)
        rate_limit_delay = 0.1  # Minimal delay for local mirrors
    else:
        # Public MusicBrainz: respect rate limits
        actual_batch_size = min(batch_size, 25)  # Conservative batch size
        rate_limit_delay = 1.1  # Just over 1 second to respect rate limits
    
    total_batches = (len(recording_mbids) + actual_batch_size - 1) // actual_batch_size
    print(f"🔄 Processing {len(recording_mbids)} recordings in {total_batches} batches of {actual_batch_size}")
    
    for i in range(0, len(recording_mbids), actual_batch_size):
        batch = recording_mbids[i:i+actual_batch_size]
        batch_num = (i // actual_batch_size) + 1
        
        print(f"  Batch {batch_num}/{total_batches}: {len(batch)} recordings...")
        
        try:
            # Build query URL with multiple recording IDs
            url = f"{base_url}/recording"
            params = {
                "recording": batch,  # Can pass multiple IDs
                "inc": "artists",
                "fmt": "json"
            }
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Parse the batch response
            recordings = data.get("recordings", [])
            
            for recording in recordings:
                recording_id = recording.get("id")
                title = recording.get("title", "")
                
                if "artist-credit" in recording and recording["artist-credit"]:
                    artist = recording["artist-credit"][0]["artist"]
                    artist_mbid = artist.get("id")
                    artist_name = artist.get("name", "")
                    
                    results[recording_id] = (artist_mbid, artist_name, title)
                else:
                    results[recording_id] = (None, None, title)
            
            # Rate limiting compliance
            if batch_num < total_batches:  # Don't delay after the last batch
                time.sleep(rate_limit_delay)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching batch {batch_num}: {e}")
            # Mark failed recordings as None
            for recording_id in batch:
                if recording_id not in results:
                    results[recording_id] = (None, None, None)
            continue
        except (KeyError, IndexError) as e:
            print(f"❌ Error parsing batch {batch_num}: {e}")
            # Mark failed recordings as None
            for recording_id in batch:
                if recording_id not in results:
                    results[recording_id] = (None, None, None)
            continue
    
    successful = sum(1 for result in results.values() if result[0] is not None)
    print(f"✅ Batch processing complete: {successful}/{len(recording_mbids)} recordings processed successfully")
    
    return results

def get_artist_info_smart(recording_mbids):
    """
    Smart wrapper that chooses the best method based on the number of recordings
    
    Args:
        recording_mbids (list): List of recording MBIDs
    
    Returns:
        dict: {recording_mbid: (artist_mbid, artist_name, track_title), ...}
    """
    if len(recording_mbids) <= 5:
        # For small numbers, use individual requests
        print(f"🔍 Using individual requests for {len(recording_mbids)} recordings")
        results = {}
        for recording_mbid in recording_mbids:
            results[recording_mbid] = get_artist_info(recording_mbid)
            if not LOCAL_MB_MIRROR:
                time.sleep(1.1)  # Rate limit for public API
        return results
    else:
        # For larger numbers, use batch processing
        print(f"🚀 Using batch processing for {len(recording_mbids)} recordings")
        return get_artist_info_batch(recording_mbids)
