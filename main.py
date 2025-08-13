#!/usr/bin/env python3

import json
import argparse
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from config import (USER, HTTP_PORT, PLEX_BASE_URL, PLEX_TOKEN,
                   LIDARR_UPDATE_INTERVAL, PLEX_UPDATE_INTERVAL)
from listenbrainz_playlist_api import get_all_recommendations, get_weekly_exploration_tracks
from musicbrainz_api import get_artist_info_smart

# Global variables to store processed data
artist_data = {}
last_updated = None
lidarr_last_updated = None
plex_last_updated = None
initial_processing_complete = False
initial_processing_status = "Starting..."

# Thread lock for safe data updates
data_lock = threading.Lock()

class LibraryHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving Lidarr custom import list"""

    def do_GET(self):
        global artist_data, last_updated, lidarr_last_updated, initial_processing_complete, initial_processing_status

        if self.path == '/':
            if not initial_processing_complete:
                # Return empty list during initial processing
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    "artists": [],
                    "count": 0,
                    "status": "initial_processing",
                    "message": initial_processing_status,
                    "last_updated": None,
                    "source": "ListenBrainz Historical Recommendations"
                }
                self.wfile.write(json.dumps(response, indent=2).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                with data_lock:
                    response = {
                        "artists": list(artist_data.values()),
                        "count": len(artist_data),
                        "last_updated": last_updated.isoformat() if last_updated else None,
                        "lidarr_last_updated": lidarr_last_updated.isoformat() if lidarr_last_updated else None,
                        "source": "ListenBrainz Historical Recommendations"
                    }

                self.wfile.write(json.dumps(response, indent=2).encode())

        elif self.path == '/health':
            # Always return healthy - the service IS running even if still processing
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            with data_lock:
                health = {
                    "status": "healthy",
                    "initial_processing_complete": initial_processing_complete,
                    "initial_processing_status": initial_processing_status,
                    "artists_count": len(artist_data),
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "lidarr_last_updated": lidarr_last_updated.isoformat() if lidarr_last_updated else None,
                    "plex_last_updated": plex_last_updated.isoformat() if plex_last_updated else None,
                    "config": {
                        "user": USER,
                        "plex_configured": bool(PLEX_BASE_URL and PLEX_TOKEN),
                        "lidarr_update_interval": LIDARR_UPDATE_INTERVAL,
                        "plex_update_interval": PLEX_UPDATE_INTERVAL,
                    }
                }

            self.wfile.write(json.dumps(health, indent=2).encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        # Suppress routine HTTP logs to reduce noise
        if '/health' not in format % args:  # Don't log health checks
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HTTP: {format % args}", flush=True)

def process_listenbrainz_data():
    """Process ListenBrainz recommendations and extract artist data"""
    global artist_data, last_updated, lidarr_last_updated, initial_processing_status

    if not USER:
        print("❌ Error: LB_USER not configured", flush=True)
        initial_processing_status = "Error: LB_USER not configured"
        return False

    try:
        print(f"🔥 Fetching ALL recommendations for user: {USER}", flush=True)
        initial_processing_status = f"Fetching recommendations for {USER}..."
        recommendations = get_all_recommendations(USER)

        if not recommendations:
            print("❌ No recommendations found", flush=True)
            initial_processing_status = "Error: No recommendations found"
            return False

        print(f"📋 Found {len(recommendations)} total recommendations for Lidarr", flush=True)
        initial_processing_status = f"Processing {len(recommendations)} recommendations..."

        # Extract all recording MBIDs for batch processing
        recording_mbids = []
        for item in recommendations:
            recording_mbid = item.get("recording_mbid")
            if recording_mbid:
                recording_mbids.append(recording_mbid)

        print(f"🔍 Processing {len(recording_mbids)} recording MBIDs for artist data...", flush=True)
        initial_processing_status = f"Looking up {len(recording_mbids)} tracks from MusicBrainz..."

        # Use batch processing for efficiency
        batch_results = get_artist_info_smart(recording_mbids)

        # Process results to extract unique artists
        seen_artists = {}
        processed = 0

        for recording_mbid, (artist_mbid, artist_name, track_title) in batch_results.items():
            if artist_mbid and artist_mbid not in seen_artists:
                seen_artists[artist_mbid] = {
                    "MusicBrainzId": artist_mbid,
                    "title": artist_name
                }
                processed += 1

                if processed % 25 == 0:
                    print(f"  Processed {processed} unique artists...", flush=True)
                    initial_processing_status = f"Processed {processed} unique artists..."

        # Thread-safe update of global data
        with data_lock:
            artist_data.clear()
            artist_data.update(seen_artists)
            last_updated = datetime.now()
            lidarr_last_updated = datetime.now()

        # Save data to file for backup/debugging
        lidarr_list = list(seen_artists.values())
        with open("/app/data/lidarr_custom_list.json", "w", encoding="utf-8") as f:
            json.dump(lidarr_list, f, indent=2)

        print(f"✅ Processed {len(seen_artists)} unique artists for Lidarr from {len(recommendations)} total recommendations", flush=True)
        print(f"💾 Updated JSON file and HTTP server data", flush=True)
        initial_processing_status = f"Complete: {len(seen_artists)} artists ready"
        return True

    except Exception as e:
        print(f"❌ Error processing ListenBrainz data: {e}", flush=True)
        initial_processing_status = f"Error: {str(e)}"
        import traceback
        traceback.print_exc()
        return False

def create_plex_playlists():
    """Create Plex playlists from ListenBrainz recommendations"""
    global plex_last_updated, initial_processing_status

    if not PLEX_BASE_URL or not PLEX_TOKEN:
        print("⚠️  Plex not configured - skipping playlist creation", flush=True)
        return True

    try:
        # Import the multi-playlist functionality
        from listenbrainz_to_plex import create_all_playlists
        
        print("🎵 Creating playlists from ListenBrainz recommendations...", flush=True)
        initial_processing_status = "Creating Plex playlists..."
        success = create_all_playlists(USER)

        if success:
            print(f"✅ Successfully created Plex playlists", flush=True)
            with data_lock:
                plex_last_updated = datetime.now()
        else:
            print("❌ Failed to create Plex playlists", flush=True)

        return success

    except Exception as e:
        print(f"❌ Error creating Plex playlists: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

def initial_processing_task():
    """Run initial processing in background"""
    global initial_processing_complete, initial_processing_status
    
    try:
        print("🔍 Starting initial data processing in background...", flush=True)
        
        # Process Lidarr data
        print("📊 Processing Lidarr data...", flush=True)
        initial_processing_status = "Processing Lidarr data..."
        success = process_listenbrainz_data()
        
        if not success:
            print("⚠️  Initial Lidarr processing had issues but continuing...", flush=True)
        
        # Process Plex playlists
        if PLEX_BASE_URL and PLEX_TOKEN:
            print("🎵 Creating initial Plex playlists...", flush=True)
            initial_processing_status = "Creating Plex playlists..."
            create_plex_playlists()
        
        initial_processing_complete = True
        initial_processing_status = "Ready"
        print("✅ Initial processing complete!", flush=True)
        
    except Exception as e:
        print(f"❌ Error in initial processing: {e}", flush=True)
        initial_processing_status = f"Error: {str(e)}"
        import traceback
        traceback.print_exc()
        # Mark as complete even on error so scheduled tasks can retry
        initial_processing_complete = True

def lidarr_update_task(update_interval):
    """Background task for updating Lidarr data"""
    def run():
        # Wait for initial processing to complete
        while not initial_processing_complete:
            time.sleep(5)
        
        # Wait for the first interval before running again
        time.sleep(update_interval)
        
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 Starting scheduled Lidarr data update...", flush=True)
                process_listenbrainz_data()
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏰ Next Lidarr update in {update_interval} seconds", flush=True)
            except Exception as e:
                print(f"❌ Error in Lidarr update task: {e}", flush=True)
                import traceback
                traceback.print_exc()

            time.sleep(update_interval)

    thread = threading.Thread(target=run, daemon=True, name="LidarrUpdater")
    thread.start()
    return thread

def plex_update_task(update_interval):
    """Background task for updating Plex playlists"""
    def run():
        # Wait for initial processing to complete
        while not initial_processing_complete:
            time.sleep(5)
        
        # Wait for the first interval before running again
        time.sleep(update_interval)
        
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🎵 Starting scheduled Plex playlists update...", flush=True)
                create_plex_playlists()
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏰ Next Plex update in {update_interval} seconds", flush=True)
            except Exception as e:
                print(f"❌ Error in Plex update task: {e}", flush=True)
                import traceback
                traceback.print_exc()

            time.sleep(update_interval)

    thread = threading.Thread(target=run, daemon=True, name="PlexUpdater")
    thread.start()
    return thread

def run_http_server():
    """Run the HTTP server for Lidarr integration"""
    try:
        server = HTTPServer(('0.0.0.0', HTTP_PORT), LibraryHandler)
        print(f"🌐 HTTP server started on port {HTTP_PORT}", flush=True)
        print(f"📡 Lidarr custom list URL: http://localhost:{HTTP_PORT}/", flush=True)
        print(f"🏥 Health check URL: http://localhost:{HTTP_PORT}/health", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 HTTP server stopped", flush=True)
    except Exception as e:
        print(f"❌ HTTP server error: {e}", flush=True)
        import traceback
        traceback.print_exc()

def run_once():
    """Run the processing once and exit"""
    print("🔍 Running ListenBrainz processing (one-time mode)", flush=True)

    # Process ListenBrainz data for Lidarr
    if not process_listenbrainz_data():
        return False

    # Create Plex playlists from recommendations
    create_plex_playlists()

    # Save data to file for Lidarr
    with data_lock:
        lidarr_list = list(artist_data.values())

    with open("/app/data/lidarr_custom_list.json", "w", encoding="utf-8") as f:
        json.dump(lidarr_list, f, indent=2)

    print(f"💾 Saved {len(lidarr_list)} artists to lidarr_custom_list.json", flush=True)
    print("✅ Processing complete", flush=True)

    return True

def run_daemon_mode(lidarr_interval=None, plex_interval=None):
    """Run in daemon mode with scheduled updates and HTTP server"""
    global initial_processing_status
    
    # Use provided intervals or defaults
    lidarr_update_interval = lidarr_interval or LIDARR_UPDATE_INTERVAL
    plex_update_interval = plex_interval or PLEX_UPDATE_INTERVAL

    print("🚀 Starting daemon mode", flush=True)
    print(f"📊 Lidarr update interval: {lidarr_update_interval} seconds ({lidarr_update_interval/3600:.1f} hours)", flush=True)
    print(f"🎵 Plex update interval: {plex_update_interval} seconds ({plex_update_interval/3600:.1f} hours)", flush=True)
    print(f"🎯 Plex mode: Auto-create Daily Jams, Weekly Jams, and Weekly Exploration playlists", flush=True)
    print("", flush=True)

    # Start HTTP server immediately in a separate thread
    print("🌐 Starting HTTP server immediately...", flush=True)
    http_thread = threading.Thread(target=run_http_server, daemon=True, name="HTTPServer")
    http_thread.start()
    
    # Give the HTTP server a moment to start
    time.sleep(2)
    
    # Start initial processing in background
    initial_thread = threading.Thread(target=initial_processing_task, daemon=True, name="InitialProcessing")
    initial_thread.start()
    
    # Start scheduled update tasks (they'll wait for initial processing to complete)
    print("⏰ Starting scheduled update tasks...", flush=True)
    lidarr_thread = lidarr_update_task(lidarr_update_interval)
    plex_thread = plex_update_task(plex_update_interval)

    print("✅ All services started", flush=True)
    print("📝 Initial processing is running in the background...", flush=True)
    print("", flush=True)

    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
            # Optional: Add periodic status check here
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...", flush=True)
        sys.exit(0)

def main():
    # Global config override from command line
    global LIDARR_UPDATE_INTERVAL, PLEX_UPDATE_INTERVAL

    parser = argparse.ArgumentParser(description="ListenBrainz to Lidarr and Plex integration")
    parser.add_argument("--mode", choices=["daemon", "once"], default="daemon",
                       help="Run mode: 'daemon' for continuous operation with scheduled updates, 'once' for single run")
    parser.add_argument("--lidarr-interval", type=int, default=LIDARR_UPDATE_INTERVAL,
                       help=f"Lidarr update interval in seconds (default: {LIDARR_UPDATE_INTERVAL})")
    parser.add_argument("--plex-interval", type=int, default=PLEX_UPDATE_INTERVAL,
                       help=f"Plex update interval in seconds (default: {PLEX_UPDATE_INTERVAL})")

    args = parser.parse_args()

    # Override config with command line arguments
    LIDARR_UPDATE_INTERVAL = args.lidarr_interval
    PLEX_UPDATE_INTERVAL = args.plex_interval

    # Validate configuration
    if not USER:
        print("❌ Error: LB_USER is required", flush=True)
        print("Set LB_USER environment variable or add to config.env", flush=True)
        sys.exit(1)

    print(f"🎵 ListenBrainz to Lidarr and Plex Integration", flush=True)
    print(f"👤 User: {USER}", flush=True)
    print(f"🔗 Plex configured: {'Yes' if PLEX_BASE_URL and PLEX_TOKEN else 'No'}", flush=True)
    print(f"🌐 HTTP port: {HTTP_PORT}", flush=True)
    print(f"📊 Lidarr source: Collaborative filtering recommendations", flush=True)
    print(f"🎵 Plex mode: Auto-create available playlists (Daily Jams, Weekly Jams, Weekly Exploration)", flush=True)
    print("", flush=True)

    if args.mode == "once":
        success = run_once()
        sys.exit(0 if success else 1)
    else:
        run_daemon_mode()

if __name__ == "__main__":
    main()
