#!/usr/bin/env python3

import sys
import argparse
import time
from datetime import datetime
from plex_api import PlexClient
from musicbrainz_api import get_artist_info
from listenbrainz_playlist_api import get_weekly_exploration_tracks
from config import PLEX_BASE_URL, PLEX_TOKEN, USER

def create_playlist_from_recommendations(
    plex_url,
    plex_token,
    listenbrainz_user,
    playlist_name=None,
    max_tracks=None,
    append_to_existing=False,
    days_filter=14
):
    """
    Main function to create a Plex playlist from ListenBrainz recommendations

    Args:
        plex_url: Plex server URL
        plex_token: Plex authentication token
        listenbrainz_user: ListenBrainz username
        playlist_name: Name for the playlist (auto-generated if None)
        max_tracks: Maximum number of tracks to process (None for all)
        append_to_existing: Whether to append to existing playlist or replace
        days_filter: Number of days to look back for recommendations (ignored - uses playlist)
    """

    # Initialize Plex client
    plex = PlexClient(plex_url, plex_token)

    # Test Plex connection first
    if not plex.test_plex_connection():
        print("❌ Plex connection test failed - aborting playlist creation")
        return False

    # Generate playlist name if not provided
    if not playlist_name:
        # Use a simple name without timestamp for recurring updates
        playlist_name = f"ListenBrainz Weekly Discovery"

    print(f"🎵 Creating playlist: {playlist_name}")
    print(f"👤 User: {listenbrainz_user}")
    print(f"📡 Plex Server: {plex_url}")
    if max_tracks:
        print(f"📊 Max tracks: {max_tracks}")
    print()

    try:
        # Get tracks from ListenBrainz Weekly Exploration playlist
        print("📥 Fetching tracks from ListenBrainz Weekly Exploration playlist...")
        recommendations = get_weekly_exploration_tracks(listenbrainz_user)

        if not recommendations:
            print("❌ No recommendations found")
            return False

        total_recs = len(recommendations)
        process_count = min(total_recs, max_tracks) if max_tracks else total_recs

        print(f"📋 Found {total_recs} tracks in Weekly Exploration playlist")
        print(f"🔄 Processing {process_count} tracks for Plex playlist...")
        print()

        # Process recommendations and match to Plex
        matched_tracks = []
        failed_matches = []
        processed = 0

        for i, rec in enumerate(recommendations[:process_count]):
            recording_mbid = rec.get('recording_mbid')
            if not recording_mbid:
                continue

            processed += 1
            progress = f"[{processed}/{process_count}]"

            try:
                # Get artist and track info from MusicBrainz
                artist_id, artist_name, track_title = get_artist_info(recording_mbid)

                if not artist_name or not track_title:
                    print(f"{progress} ❌ Could not get info for MBID: {recording_mbid}")
                    continue

                # Search in Plex
                rating_key = plex.search_for_track(track_title, artist_name, [artist_id])

                if rating_key:
                    matched_tracks.append(rating_key)
                    print(f"{progress} ✅ {artist_name} - {track_title}")
                else:
                    failed_matches.append(f"{artist_name} - {track_title}")
                    print(f"{progress} ❌ {artist_name} - {track_title}")

            except Exception as e:
                print(f"{progress} ❌ Error processing {recording_mbid}: {e}")
                continue

        print()
        print("📊 Processing Results:")
        print(f"  ✅ Matched: {len(matched_tracks)} tracks")
        print(f"  ❌ Failed: {len(failed_matches)} tracks")
        match_rate = (len(matched_tracks) / processed) * 100 if processed > 0 else 0
        print(f"  📈 Success rate: {match_rate:.1f}%")
        print()

        if not matched_tracks:
            print("❌ No tracks matched - playlist not created")
            return False

        # Create or update playlist with simplified summary
        summary = f"Auto-generated from ListenBrainz Weekly Exploration playlist for {listenbrainz_user}"
        # Simplified date format to avoid URL encoding issues
        summary += f". Created on {datetime.now().strftime('%Y-%m-%d')}"

        print(f"🎵 Creating playlist with {len(matched_tracks)} tracks...")

        if append_to_existing:
            existing_playlist = plex.find_playlist_by_name(playlist_name)
            if existing_playlist:
                success = plex.add_tracks_to_playlist(existing_playlist['ratingKey'], matched_tracks)
            else:
                success = plex.create_playlist(playlist_name, matched_tracks, summary)
        else:
            success = plex.create_or_update_playlist(playlist_name, matched_tracks, summary)

        if success:
            print(f"✅ Successfully created/updated playlist: {playlist_name}")

            # Final verification - check actual playlist contents
            print(f"\n🔍 Verifying playlist contents...")
            time.sleep(3)  # Give Plex more time to fully update

            final_playlist = plex.find_playlist_by_name(playlist_name)
            if final_playlist:
                try:
                    # Use the new helper method for verification
                    actual_tracks = plex.get_playlist_tracks(final_playlist['ratingKey'])

                    print(f"📊 Final verification results:")
                    print(f"   Reported track count: {final_playlist.get('leafCount', 'unknown')}")
                    print(f"   Actual tracks found: {len(actual_tracks)}")

                    if len(actual_tracks) > 0:
                        print(f"✅ SUCCESS! Playlist contains {len(actual_tracks)} tracks:")
                        for i, track in enumerate(actual_tracks[:10], 1):  # Show first 10
                            artist = track.get('grandparentTitle', 'Unknown Artist')
                            title = track.get('title', 'Unknown Title')
                            print(f"   {i}. {artist} - {title}")
                        if len(actual_tracks) > 10:
                            print(f"   ... and {len(actual_tracks) - 10} more tracks")
                    else:
                        print(f"❌ VERIFICATION FAILED: Playlist is empty despite successful API calls")
                        print(f"   This indicates a timing or API issue with track addition")

                        # Try to get more debug info
                        print(f"🔍 Debug info:")
                        print(f"   Playlist ratingKey: {final_playlist.get('ratingKey')}")
                        print(f"   First few track ratingKeys we tried to add: {matched_tracks[:5]}")

                except Exception as e:
                    print(f"❌ Error verifying playlist contents: {e}")
            else:
                print(f"❌ Could not find playlist for verification")

            # Show some failed matches for debugging
            if failed_matches:
                print(f"\n❌ Failed to match {len(failed_matches)} tracks:")
                for track in failed_matches[:10]:  # Show first 10 failures
                    print(f"  - {track}")
                if len(failed_matches) > 10:
                    print(f"  ... and {len(failed_matches) - 10} more")

            return True
        else:
            print("❌ Failed to create/update playlist")
            return False

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create Plex playlists from ListenBrainz recommendations")
    parser.add_argument("--user", "-u", default=USER, help="ListenBrainz username")
    parser.add_argument("--playlist", "-p", help="Playlist name (auto-generated if not provided)")
    parser.add_argument("--max-tracks", "-m", type=int, help="Maximum number of tracks to process")
    parser.add_argument("--append", action="store_true", help="Append to existing playlist instead of replacing")
    parser.add_argument("--days", "-d", type=int, default=14, help="Days to look back for recommendations (ignored - uses Weekly Exploration playlist)")
    parser.add_argument("--plex-url", default=PLEX_BASE_URL, help="Plex server URL")
    parser.add_argument("--plex-token", default=PLEX_TOKEN, help="Plex authentication token")

    args = parser.parse_args()

    # Validate required arguments
    if not args.user:
        print("❌ Error: ListenBrainz username is required")
        print("Set LB_USER environment variable or use --user argument")
        sys.exit(1)

    if not args.plex_url or not args.plex_token:
        print("❌ Error: Plex URL and token are required")
        print("Set PLEX_BASE_URL and PLEX_TOKEN environment variables or use --plex-url and --plex-token arguments")
        sys.exit(1)

    # Run the main function
    success = create_playlist_from_recommendations(
        plex_url=args.plex_url,
        plex_token=args.plex_token,
        listenbrainz_user=args.user,
        playlist_name=args.playlist,
        max_tracks=args.max_tracks,
        append_to_existing=args.append,
        days_filter=args.days
    )

    if success:
        print("\n🎉 Playlist creation completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Playlist creation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
