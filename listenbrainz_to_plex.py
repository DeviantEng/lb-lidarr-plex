#!/usr/bin/env python3

import sys
import argparse
import time
import re
from datetime import datetime
from plex_api import PlexClient
from musicbrainz_api import get_artist_info
from listenbrainz_playlist_api import (
    get_weekly_exploration_tracks, 
    get_daily_jams_tracks, 
    get_weekly_jams_tracks
)
from config import (
    PLEX_BASE_URL, PLEX_TOKEN, USER,
    PLEX_DAILY_JAMS_NAME, PLEX_WEEKLY_JAMS_NAME, PLEX_WEEKLY_EXPLORATION_NAME
)

def get_existing_playlist_mbids(plex_url, plex_token, playlist_name):
    """
    Get the recording MBIDs from an existing Plex playlist
    
    Args:
        plex_url: Plex server URL
        plex_token: Plex authentication token
        playlist_name: Name of the playlist to check
    
    Returns:
        list: List of recording MBIDs in order, or empty list if playlist doesn't exist
    """
    try:
        plex = PlexClient(plex_url, plex_token)
        
        # Find the playlist
        existing_playlist = plex.find_playlist_by_name(playlist_name)
        if not existing_playlist:
            return []
        
        # Get tracks from the playlist
        tracks = plex.get_playlist_tracks(existing_playlist["ratingKey"])
        if not tracks:
            return []
        
        print("🔍 Checking existing playlist: " + str(len(tracks)) + " tracks found")
        
        # For now, we can't easily extract MBIDs from Plex tracks
        # So we'll return empty list to force full rebuild
        # TODO: Implement MBID extraction from Plex GUIDs
        print("⚠️  MBID extraction not fully implemented - forcing full rebuild")
        return []
        
    except Exception as e:
        print("❌ Error checking existing playlist: " + str(e))
        return []

def compare_playlists(existing_mbids, new_tracks, similarity_threshold=0.8):
    """
    Compare existing playlist MBIDs with new tracks to determine update strategy
    
    Args:
        existing_mbids: List of MBIDs currently in the playlist
        new_tracks: List of new track dictionaries with recording_mbid
        similarity_threshold: Threshold for considering playlists similar enough for delta update
    
    Returns:
        dict: Update strategy with details
    """
    new_mbids = [track.get("recording_mbid") for track in new_tracks if track.get("recording_mbid")]
    
    # Check for exact match
    if existing_mbids == new_mbids:
        return {
            "strategy": "skip",
            "reason": "Playlists are identical",
            "existing_count": len(existing_mbids),
            "new_count": len(new_mbids)
        }
    
    # Calculate similarity
    existing_set = set(existing_mbids)
    new_set = set(new_mbids)
    
    if not existing_set and not new_set:
        return {"strategy": "skip", "reason": "Both playlists are empty"}
    
    if not existing_set or not new_set:
        similarity = 0.0
    else:
        intersection = existing_set.intersection(new_set)
        union = existing_set.union(new_set)
        similarity = len(intersection) / len(union) if union else 0.0
    
    # Determine strategy based on similarity
    if similarity >= similarity_threshold:
        # High similarity - do delta update
        to_add = [mbid for mbid in new_mbids if mbid not in existing_set]
        to_remove = [mbid for mbid in existing_mbids if mbid not in new_set]
        
        return {
            "strategy": "delta",
            "reason": "High similarity " + str(round(similarity * 100, 1)) + "%",
            "existing_count": len(existing_mbids),
            "new_count": len(new_mbids),
            "to_add": to_add,
            "to_remove": to_remove,
            "similarity": similarity
        }
    else:
        # Low similarity - full rebuild
        return {
            "strategy": "rebuild",
            "reason": "Low similarity " + str(round(similarity * 100, 1)) + "%",
            "existing_count": len(existing_mbids),
            "new_count": len(new_mbids),
            "similarity": similarity
        }

def create_playlist_from_tracks(
    plex_url,
    plex_token,
    tracks,
    playlist_name,
    max_tracks=None,
    append_to_existing=False,
    summary="",
    enable_smart_updates=True
):
    """
    Create a Plex playlist from a list of track recommendations with smart delta updates

    Args:
        plex_url: Plex server URL
        plex_token: Plex authentication token
        tracks: List of track dictionaries with recording_mbid
        playlist_name: Name for the playlist
        max_tracks: Maximum number of tracks to process (None for all)
        append_to_existing: Whether to append to existing playlist or replace
        summary: Description for the playlist
        enable_smart_updates: Whether to use smart delta updates (default: True)
    """

    # Initialize Plex client
    plex = PlexClient(plex_url, plex_token)

    print("🎵 Creating playlist: " + playlist_name)
    print("📡 Plex Server: " + plex_url)
    if max_tracks:
        print("📊 Max tracks: " + str(max_tracks))
    
    try:
        if not tracks:
            print("❌ No tracks provided")
            return False

        total_tracks = len(tracks)
        process_count = min(total_tracks, max_tracks) if max_tracks else total_tracks
        tracks_to_process = tracks[:process_count]

        print("📋 Found " + str(total_tracks) + " tracks")
        if process_count < total_tracks:
            print("📝 Processing " + str(process_count) + " tracks (limited by max_tracks)")
        
        # Smart update logic
        if enable_smart_updates and not append_to_existing:
            print("\n🧠 Checking for smart update opportunities...")
            existing_mbids = get_existing_playlist_mbids(plex_url, plex_token, playlist_name)
            update_strategy = compare_playlists(existing_mbids, tracks_to_process)
            
            print("📊 Update Strategy: " + update_strategy["strategy"] + " - " + update_strategy["reason"])
            
            if update_strategy["strategy"] == "skip":
                print("⚡ Playlist unchanged - skipping update entirely!")
                print("✅ Smart update: 0 API calls needed")
                return True
            elif update_strategy["strategy"] == "delta":
                print("🔄 Using delta update (processing only differences)")
                # For now, fall back to full rebuild since MBID extraction isn't implemented
                print("⚠️  Delta update not fully implemented - using full rebuild")
            else:
                print("🔨 Using full rebuild due to significant changes")

        print("📝 Processing " + str(process_count) + " tracks for Plex playlist...")
        print()

        # Standard processing for full rebuild
        matched_tracks = []
        failed_matches = []
        processed = 0

        for i, track in enumerate(tracks_to_process):
            recording_mbid = track.get('recording_mbid')
            if not recording_mbid:
                continue

            processed += 1
            progress = "[" + str(processed) + "/" + str(process_count) + "]"

            try:
                # Get artist and track info from MusicBrainz
                artist_id, artist_name, track_title = get_artist_info(recording_mbid)

                if not artist_name or not track_title:
                    print(progress + " ❌ Could not get info for MBID: " + recording_mbid)
                    continue

                # Search in Plex
                rating_key = plex.search_for_track(track_title, artist_name, [artist_id])

                if rating_key:
                    matched_tracks.append(rating_key)
                    print(progress + " ✅ " + artist_name + " - " + track_title)
                else:
                    failed_matches.append(artist_name + " - " + track_title)
                    print(progress + " ❌ " + artist_name + " - " + track_title)

            except Exception as e:
                print(progress + " ❌ Error processing " + recording_mbid + ": " + str(e))
                continue

        print()
        print("📊 Processing Results:")
        print("  ✅ Matched: " + str(len(matched_tracks)) + " tracks")
        print("  ❌ Failed: " + str(len(failed_matches)) + " tracks")
        match_rate = (len(matched_tracks) / processed) * 100 if processed > 0 else 0
        print("  📈 Success rate: " + str(round(match_rate, 1)) + "%")
        print()

        if not matched_tracks:
            print("❌ No tracks matched - playlist not created")
            return False

        # Use provided summary or create a default one
        if not summary:
            summary = "Auto-generated from ListenBrainz recommendations. Created on " + datetime.now().strftime('%Y-%m-%d')

        print("🎵 Creating playlist with " + str(len(matched_tracks)) + " tracks...")

        if append_to_existing:
            existing_playlist = plex.find_playlist_by_name(playlist_name)
            if existing_playlist:
                success = plex.add_tracks_to_playlist(existing_playlist['ratingKey'], matched_tracks)
            else:
                success = plex.create_playlist(playlist_name, matched_tracks, summary)
        else:
            success = plex.create_or_update_playlist(playlist_name, matched_tracks, summary)

        if success:
            print("✅ Successfully created/updated playlist: " + playlist_name)
            return True
        else:
            print("❌ Failed to create/update playlist")
            return False

    except Exception as e:
        print("❌ Fatal error: " + str(e))
        return False

def create_single_playlist(playlist_type, playlist_name, tracks_function, max_tracks=50):
    """
    Create a single playlist of a specific type
    
    Args:
        playlist_type: Description of playlist type for logging
        playlist_name: Name for the Plex playlist
        tracks_function: Function to get tracks for this playlist type (should be a callable)
        max_tracks: Maximum number of tracks to include
    """
    print("\n🎵 Creating " + playlist_type + " playlist...")
    
    try:
        # Get tracks and metadata from ListenBrainz
        result = tracks_function()
        
        # Unpack the result tuple
        if isinstance(result, tuple) and len(result) == 2:
            tracks, playlist_metadata = result
        else:
            # Fallback for functions that only return tracks
            tracks = result
            playlist_metadata = None
        
        if not tracks:
            print("❌ No tracks found for " + playlist_type)
            return False
        
        # Extract description from ListenBrainz playlist annotation
        summary = ""
        if playlist_metadata:
            annotation = playlist_metadata.get("annotation", "")
            if annotation:
                # Clean up HTML tags if present
                summary = re.sub('<[^<]+?>', '', annotation)
                summary = summary.replace('\n', ' ').strip()
                # Truncate if too long (Plex has limits)
                if len(summary) > 300:
                    summary = summary[:297] + "..."
        
        # Add fallback description if none found
        if not summary:
            summary = "Auto-generated " + playlist_type + " playlist from ListenBrainz recommendations."
        
        # Create the playlist
        success = create_playlist_from_tracks(
            plex_url=PLEX_BASE_URL,
            plex_token=PLEX_TOKEN,
            tracks=tracks,
            playlist_name=playlist_name,
            max_tracks=max_tracks,
            append_to_existing=False,
            summary=summary
        )
        
        if success:
            print("✅ Successfully created " + playlist_type + " playlist: " + playlist_name)
        else:
            print("❌ Failed to create " + playlist_type + " playlist")
            
        return success
        
    except Exception as e:
        print("❌ Error creating " + playlist_type + " playlist: " + str(e))
        return False

def create_all_playlists(user=None):
    """
    Create all configured playlists
    """
    if not PLEX_BASE_URL or not PLEX_TOKEN:
        print("⚠️  Plex not configured - skipping playlist creation")
        return True

    # Use provided user or fallback to config
    playlist_user = user or USER
    
    if not playlist_user:
        print("❌ Error: LB_USER not configured")
        return False

    print("🎵 Creating multiple playlists from ListenBrainz recommendations...")
    print("👤 User: " + playlist_user)
    print("📡 Plex Server: " + PLEX_BASE_URL)
    print()

    # Define playlist configurations
    playlist_configs = [
        {
            "type": "Daily Jams",
            "name": PLEX_DAILY_JAMS_NAME,
            "function": lambda: get_daily_jams_tracks(playlist_user),
            "max_tracks": 30
        },
        {
            "type": "Weekly Jams", 
            "name": PLEX_WEEKLY_JAMS_NAME,
            "function": lambda: get_weekly_jams_tracks(playlist_user),
            "max_tracks": 50
        },
        {
            "type": "Weekly Exploration",
            "name": PLEX_WEEKLY_EXPLORATION_NAME, 
            "function": lambda: get_weekly_exploration_tracks(playlist_user),
            "max_tracks": 50
        }
    ]

    success_count = 0
    total_count = len(playlist_configs)

    for config in playlist_configs:
        success = create_single_playlist(
            playlist_type=config["type"],
            playlist_name=config["name"],
            tracks_function=config["function"],
            max_tracks=config["max_tracks"]
        )
        
        if success:
            success_count += 1

    print("\n📊 Overall Results:")
    print("✅ Successfully created: " + str(success_count) + "/" + str(total_count) + " playlists")
    
    if success_count == total_count:
        print("🎉 All playlists created successfully!")
        return True
    elif success_count > 0:
        print("⚠️  Some playlists created successfully")
        return True
    else:
        print("❌ Failed to create any playlists")
        return False

def create_playlist_from_recommendations(
    plex_url,
    plex_token,
    listenbrainz_user,
    playlist_name=None,
    max_tracks=None,
    append_to_existing=False
):
    """
    Legacy function for backward compatibility
    Creates Weekly Exploration playlist only
    """
    print("🔄 Using legacy single-playlist mode (Weekly Exploration only)")
    
    # Get Weekly Exploration tracks and metadata
    tracks, playlist_metadata = get_weekly_exploration_tracks(listenbrainz_user)
    
    if not playlist_name:
        playlist_name = PLEX_WEEKLY_EXPLORATION_NAME
    
    # Extract description from playlist metadata
    summary = ""
    if playlist_metadata:
        annotation = playlist_metadata.get("annotation", "")
        if annotation:
            summary = re.sub('<[^<]+?>', '', annotation)
            summary = summary.replace('\n', ' ').strip()
            if len(summary) > 300:
                summary = summary[:297] + "..."
    
    if not summary:
        summary = "Auto-generated Weekly Exploration playlist from ListenBrainz recommendations."
    
    return create_playlist_from_tracks(
        plex_url=plex_url,
        plex_token=plex_token,
        tracks=tracks,
        playlist_name=playlist_name,
        max_tracks=max_tracks,
        append_to_existing=append_to_existing,
        summary=summary
    )

def main():
    parser = argparse.ArgumentParser(description="Create Plex playlists from ListenBrainz recommendations")
    parser.add_argument("--user", "-u", default=USER, help="ListenBrainz username")
    parser.add_argument("--playlist", "-p", help="Single playlist name")
    parser.add_argument("--max-tracks", "-m", type=int, help="Maximum number of tracks to process")
    parser.add_argument("--append", action="store_true", help="Append to existing playlist instead of replacing")
    parser.add_argument("--type", choices=["daily", "weekly-jams", "weekly-exploration", "all"], 
                       default="all", help="Type of playlist to create")
    parser.add_argument("--plex-url", default=PLEX_BASE_URL, help="Plex server URL")
    parser.add_argument("--plex-token", default=PLEX_TOKEN, help="Plex authentication token")

    args = parser.parse_args()

    # Validate required arguments
    if not args.user:
        print("❌ Error: ListenBrainz username is required")
        sys.exit(1)

    if not args.plex_url or not args.plex_token:
        print("❌ Error: Plex URL and token are required")
        sys.exit(1)

    # Choose operation mode
    if args.playlist or args.type != "all":
        # Single playlist mode
        if args.type == "daily":
            tracks, playlist_metadata = get_daily_jams_tracks(args.user)
            playlist_name = args.playlist or PLEX_DAILY_JAMS_NAME
        elif args.type == "weekly-jams":
            tracks, playlist_metadata = get_weekly_jams_tracks(args.user)
            playlist_name = args.playlist or PLEX_WEEKLY_JAMS_NAME
        elif args.type == "weekly-exploration":
            tracks, playlist_metadata = get_weekly_exploration_tracks(args.user)
            playlist_name = args.playlist or PLEX_WEEKLY_EXPLORATION_NAME
        else:
            tracks, playlist_metadata = get_weekly_exploration_tracks(args.user)
            playlist_name = args.playlist or PLEX_WEEKLY_EXPLORATION_NAME

        # Extract description from playlist metadata
        summary = ""
        if playlist_metadata:
            annotation = playlist_metadata.get("annotation", "")
            if annotation:
                summary = re.sub('<[^<]+?>', '', annotation)
                summary = summary.replace('\n', ' ').strip()
                if len(summary) > 300:
                    summary = summary[:297] + "..."
        
        if not summary:
            summary = "Auto-generated playlist from ListenBrainz recommendations."

        success = create_playlist_from_tracks(
            plex_url=args.plex_url,
            plex_token=args.plex_token,
            tracks=tracks,
            playlist_name=playlist_name,
            max_tracks=args.max_tracks,
            append_to_existing=args.append,
            summary=summary
        )
    else:
        # Multi-playlist mode
        success = create_all_playlists(args.user)

    if success:
        print("\n🎉 Playlist creation completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Playlist creation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
