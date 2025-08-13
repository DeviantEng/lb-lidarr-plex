import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    Get artist information for multiple recording MBIDs using individual requests with rate limiting
    NOTE: MusicBrainz doesn't support true batch queries for recordings, so we do efficient individual requests

    Args:
        recording_mbids (list): List of MusicBrainz recording IDs
        batch_size (int): Number of concurrent requests (ignored for public MB due to rate limits)

    Returns:
        dict: {recording_mbid: (artist_mbid, artist_name, track_title), ...}
    """
    results = {}
    total = len(recording_mbids)

    if LOCAL_MB_MIRROR:
        # Use threading for local mirrors since there are no rate limits
        print(f"🚀 Using concurrent requests for {total} recordings (local mirror)")
        return _get_artist_info_concurrent(recording_mbids, max_workers=min(10, batch_size))
    else:
        # Use sequential requests with rate limiting for public API
        print(f"🔄 Using sequential requests for {total} recordings (public API with rate limiting)")
        return _get_artist_info_sequential(recording_mbids)

def _get_artist_info_sequential(recording_mbids):
    """Sequential processing with rate limiting for public MusicBrainz API"""
    results = {}
    total = len(recording_mbids)

    for i, recording_mbid in enumerate(recording_mbids, 1):
        print(f"  Processing {i}/{total}: {recording_mbid}")
        results[recording_mbid] = get_artist_info(recording_mbid)

        # Rate limiting: MusicBrainz allows 1 request per second
        if i < total:  # Don't delay after the last request
            time.sleep(1.1)  # Slightly over 1 second to be safe

    successful = sum(1 for result in results.values() if result[0] is not None)
    print(f"✅ Sequential processing complete: {successful}/{total} recordings processed successfully")

    return results

def _get_artist_info_concurrent(recording_mbids, max_workers=10):
    """Concurrent processing for local MusicBrainz mirrors"""
    results = {}
    total = len(recording_mbids)
    processed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all requests
        future_to_mbid = {
            executor.submit(get_artist_info, mbid): mbid
            for mbid in recording_mbids
        }

        # Collect results as they complete
        for future in as_completed(future_to_mbid):
            mbid = future_to_mbid[future]
            processed += 1

            try:
                result = future.result()
                results[mbid] = result

                # Progress indicator
                if processed % 50 == 0 or processed == total:
                    print(f"  Processed {processed}/{total} recordings...")

            except Exception as e:
                print(f"Error processing {mbid}: {e}")
                results[mbid] = (None, None, None)

    successful = sum(1 for result in results.values() if result[0] is not None)
    print(f"✅ Concurrent processing complete: {successful}/{total} recordings processed successfully")

    return results

def get_artist_info_smart(recording_mbids):
    """
    Smart wrapper that chooses the best method based on the number of recordings and API type

    Args:
        recording_mbids (list): List of recording MBIDs

    Returns:
        dict: {recording_mbid: (artist_mbid, artist_name, track_title), ...}
    """
    total = len(recording_mbids)

    if total == 0:
        return {}
    elif total <= 5:
        # For small numbers, use individual requests
        print(f"🔍 Using individual requests for {total} recordings")
        results = {}
        for recording_mbid in recording_mbids:
            results[recording_mbid] = get_artist_info(recording_mbid)
            if not LOCAL_MB_MIRROR and len(recording_mbids) > 1:
                time.sleep(1.1)  # Rate limit for public API
        return results
    else:
        # For larger numbers, use the batch processing method
        print(f"🚀 Using batch processing for {total} recordings")
        return get_artist_info_batch(recording_mbids)

# Legacy function name for backward compatibility
def get_artist_info_batch_legacy(recording_mbids, batch_size=50):
    """
    DEPRECATED: This was the old broken batch implementation
    Use get_artist_info_batch() or get_artist_info_smart() instead
    """
    print("⚠️  Warning: Using deprecated batch function. Consider using get_artist_info_smart() instead.")
    return get_artist_info_batch(recording_mbids, batch_size)
