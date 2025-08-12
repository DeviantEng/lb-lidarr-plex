#!/usr/bin/env python3

import json
import argparse
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from config import (USER, NULLONLY, HTTP_PORT, PLEX_BASE_URL, PLEX_TOKEN, 
                   PLEX_DAYS_FILTER, LIDARR_UPDATE_INTERVAL, PLEX_UPDATE_INTERVAL)
from listenbrainz_api import get_all_recommendations, get_recent_recommendations
from musicbrainz_api import get_artist_info_smart

# Global variables to store processed data
artist_data = {}
last_updated = None
lidarr_last_updated = None
plex_last_updated = None

# Thread lock for safe data updates
data_lock = threading.Lock()

class LibraryHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving Lidarr custom import list"""
    
    def do_GET(self):
        global artist_data, last_updated, lidarr_last_updated
        
        if self.path == '/':
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
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            with data_lock:
                health = {
                    "status": "healthy",
                    "artists_count": len(artist_data),
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "lidarr_last_updated": lidarr_last_updated.isoformat() if lidarr_last_updated else None,
                    "plex_last_updated": plex_last_updated.isoformat() if plex_last_updated else None,
                    "config": {
                        "user": USER,
                        "null_only": NULLONLY,
                        "plex_configured": bool(PLEX_BASE_URL and PLEX_TOKEN),
                        "lidarr_update_interval": LIDARR_UPDATE_INTERVAL,
                        "plex_update_interval": PLEX_UPDATE_INTERVAL,
                        "plex_days_filter": PLEX_DAYS_FILTER
                    }
                }
            
            self.wfile.write(json.dumps(health, indent=2).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # Custom logging format
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HTTP: {format % args}")

def process_listenbrainz_data():
    """Process ListenBrainz recommendations and extract artist data"""
    global artist_data, last_updated, lidarr_last_updated
    
    if not USER:
        print("❌ Error: LB_USER not configured")
        return False
    
    try:
        print(f"📥 Fetching ALL recommendations for user: {USER}")
        recommendations = get_all_recommendations(USER, null_only=NULLONLY)
        
        if not recommendations:
            print("❌ No recommendations found")
            return False
        
        print(f"📋 Found {len(recommendations)} total recommendations for Lidarr")
        
        # Extract all recording MBIDs for batch processing
        recording_mbids = []
        for item in recommendations:
            recording_mbid = item.get("recording_mbid")
            if recording_mbid:
                recording_mbids.append(recording_mbid)
        
        print(f"🔄 Processing {len(recording_mbids)} recording MBIDs for artist data...")
        
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
                    print(f"  Processed {processed} unique artists...")
        
        # Thread-safe update of global data
        with data_lock:
            artist_data.clear()
            artist_data.update(seen_artists)
            last_updated = datetime.now()
            lidarr_last_updated = datetime.now()
        
        # Save data to file for backup/debugging
        lidarr_list = list(seen_artists.values())
        with open("lidarr_custom_list.json", "w", encoding="utf-8") as f:
            json.dump(lidarr_list, f, indent=2)
        
        print(f"✅ Processed {len(seen_artists)} unique artists for Lidarr from {len(recommendations)} total recommendations")
        print(f"💾 Updated JSON file and HTTP server data")
        return True
        
    except Exception as e:
        print(f"❌ Error processing ListenBrainz data: {e}")
        return False

def create_plex_playlist():
    """Create Plex playlist from the processed recommendations"""
    if not PLEX_BASE_URL or not PLEX_TOKEN:
        print("⚠️  Plex not configured - skipping playlist creation")
        return True
    
    try:
        # Import the working Plex functionality
        from working_listenbrainz_to_plex import create_playlist_from_recommendations_working
        
        print("🎵 Creating Plex playlist from recent recommendations...")
        
        # Use current date for playlist name
        playlist_name = f"ListenBrainz Weekly - {datetime.now().strftime('%Y-%m-%d')}"
        
        success = create_playlist_from_recommendations_working(
            plex_url=PLEX_BASE_URL,
            plex_token=PLEX_TOKEN,
            listenbrainz_user=USER,
            playlist_name=playlist_name,
            null_only=NULLONLY,
            max_tracks=50,  # Reasonable limit for weekly playlist
            append_to_existing=False,
            days_filter=PLEX_DAYS_FILTER  # Use configured days filter
        )
        
        if success:
            print(f"✅ Successfully created Plex playlist: {playlist_name}")
        else:
            print("❌ Failed to create Plex playlist")
            
        return success
        
    except Exception as e:
        print(f"❌ Error creating Plex playlist: {e}")
        return False

def lidarr_update_task():
    """Background task for updating Lidarr data"""
    def run():
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Starting Lidarr data update...")
                process_listenbrainz_data()
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏰ Next Lidarr update in {LIDARR_UPDATE_INTERVAL} seconds")
            except Exception as e:
                print(f"❌ Error in Lidarr update task: {e}")
            
            time.sleep(LIDARR_UPDATE_INTERVAL)
    
    thread = threading.Thread(target=run, daemon=True, name="LidarrUpdater")
    thread.start()
    return thread

def plex_update_task():
    """Background task for updating Plex playlists"""
    def run():
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🎵 Starting Plex playlist update...")
                create_plex_playlist()
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏰ Next Plex update in {PLEX_UPDATE_INTERVAL} seconds")
            except Exception as e:
                print(f"❌ Error in Plex update task: {e}")
            
            time.sleep(PLEX_UPDATE_INTERVAL)
    
    thread = threading.Thread(target=run, daemon=True, name="PlexUpdater")
    thread.start()
    return thread

def run_http_server():
    """Run the HTTP server for Lidarr integration"""
    try:
        server = HTTPServer(('0.0.0.0', HTTP_PORT), LibraryHandler)
        print(f"🌐 HTTP server started on port {HTTP_PORT}")
        print(f"📡 Lidarr custom list URL: http://localhost:{HTTP_PORT}/")
        print(f"🏥 Health check URL: http://localhost:{HTTP_PORT}/health")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 HTTP server stopped")
    except Exception as e:
        print(f"❌ HTTP server error: {e}")

def run_once():
    """Run the processing once and exit"""
    print("🔄 Running ListenBrainz processing (one-time mode)")
    
    # Process ListenBrainz data
    if not process_listenbrainz_data():
        return False
    
    # Create Plex playlist
    create_plex_playlist()
    
    # Save data to file for Lidarr
    with data_lock:
        lidarr_list = list(artist_data.values())
    
    with open("lidarr_custom_list.json", "w", encoding="utf-8") as f:
        json.dump(lidarr_list, f, indent=2)
    
    print(f"💾 Saved {len(lidarr_list)} artists to lidarr_custom_list.json")
    print("✅ Processing complete")
    
    return True

def run_daemon_mode():
    """Run in daemon mode with scheduled updates and HTTP server"""
    print("🚀 Starting daemon mode")
    print(f"📊 Lidarr update interval: {LIDARR_UPDATE_INTERVAL} seconds ({LIDARR_UPDATE_INTERVAL/3600:.1f} hours)")
    print(f"🎵 Plex update interval: {PLEX_UPDATE_INTERVAL} seconds ({PLEX_UPDATE_INTERVAL/3600:.1f} hours)")
    print(f"📅 Plex playlist days filter: {PLEX_DAYS_FILTER} days")
    print()
    
    # Run initial data processing
    print("🔄 Running initial data processing...")
    process_listenbrainz_data()
    
    # Start scheduled tasks
    print("⏰ Starting background update tasks...")
    lidarr_thread = lidarr_update_task()
    plex_thread = plex_update_task()
    
    print("✅ Background tasks started")
    print()
    
    # Start HTTP server (blocks until stopped)
    run_http_server()

def main():
    parser = argparse.ArgumentParser(description="ListenBrainz to Lidarr and Plex integration")
    parser.add_argument("--mode", choices=["daemon", "once"], default="daemon",
                       help="Run mode: 'daemon' for continuous operation with scheduled updates, 'once' for single run")
    parser.add_argument("--lidarr-interval", type=int, default=LIDARR_UPDATE_INTERVAL,
                       help=f"Lidarr update interval in seconds (default: {LIDARR_UPDATE_INTERVAL})")
    parser.add_argument("--plex-interval", type=int, default=PLEX_UPDATE_INTERVAL,
                       help=f"Plex update interval in seconds (default: {PLEX_UPDATE_INTERVAL})")
    
    args = parser.parse_args()
    
    # Override config with command line arguments
    global LIDARR_UPDATE_INTERVAL, PLEX_UPDATE_INTERVAL
    LIDARR_UPDATE_INTERVAL = args.lidarr_interval
    PLEX_UPDATE_INTERVAL = args.plex_interval
    
    # Validate configuration
    if not USER:
        print("❌ Error: LB_USER is required")
        print("Set LB_USER environment variable or add to /config/config.env")
        sys.exit(1)
    
    print(f"🎵 ListenBrainz to Lidarr and Plex Integration")
    print(f"👤 User: {USER}")
    print(f"🎯 Null only: {NULLONLY}")
    print(f"🔗 Plex configured: {'Yes' if PLEX_BASE_URL and PLEX_TOKEN else 'No'}")
    print(f"🌐 HTTP port: {HTTP_PORT}")
    print(f"📅 Plex days filter: {PLEX_DAYS_FILTER} days")
    print()
    
    if args.mode == "once":
        success = run_once()
        sys.exit(0 if success else 1)
    else:
        run_daemon_mode()

if __name__ == "__main__":
    main()
