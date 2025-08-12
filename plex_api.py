import requests
from urllib.parse import quote_plus

class PlexClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _get(self, path, params=None):
        if params is None:
            params = {}
        params["X-Plex-Token"] = self.token
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
        }
        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

    def get_music_libraries(self):
        """Get all music library sections"""
        results = self._get("/library/sections")
        media_container = results.get("MediaContainer", {})
        sections = media_container.get("Directory", [])
        
        music_sections = []
        for section in sections:
            if section.get("type") in ("artist", "music"):
                music_sections.append({
                    "key": section["key"],
                    "title": section.get("title", ""),
                    "type": section.get("type", "")
                })
        
        return music_sections

    def search_tracks_in_library(self, library_key, query):
        """Search for tracks in a specific library section"""
        params = {
            "type": 10,  # Track type
            "query": query
        }
        
        try:
            results = self._get(f"/library/sections/{library_key}/search", params=params)
            media_container = results.get("MediaContainer", {})
            tracks = media_container.get("Metadata", [])
            return tracks
        except Exception as e:
            print(f"Error searching library {library_key}: {e}")
            return []

    def search_for_track(self, track_name, artist_name, mbids=None):
        """
        Search for a track by name and artist across all music libraries.
        Optionally use MusicBrainz IDs for more precise matching.
        Returns the track's ratingKey if found, else None.
        """
        music_libraries = self.get_music_libraries()
        if not music_libraries:
            print("No music libraries found")
            return None

        # Try different search strategies
        search_queries = [
            f"{artist_name} {track_name}",  # Artist + Track
            f"{track_name} {artist_name}",  # Track + Artist  
            track_name,                     # Just track name
            artist_name                     # Just artist name
        ]

        best_match = None
        best_score = 0

        for library in music_libraries:
            library_key = library["key"]

            for query in search_queries:
                tracks = self.search_tracks_in_library(library_key, query)
                
                for track in tracks:
                    score = self._score_track_match(track, track_name, artist_name, mbids)
                    
                    if score > best_score:
                        best_score = score
                        best_match = track

        if best_match and best_score >= 50:  # Minimum threshold for a match
            return best_match["ratingKey"]
        
        return None

    def _score_track_match(self, track, target_track_name, target_artist_name, mbids=None):
        """
        Score how well a Plex track matches our target track.
        Returns a score from 0-200 (higher is better).
        """
        score = 0
        
        # Get track info from Plex metadata
        plex_track_title = track.get("title", "").lower()
        plex_artist_name = track.get("grandparentTitle", "").lower()  # Artist is grandparent
        plex_album_name = track.get("parentTitle", "").lower()        # Album is parent
        
        target_track_lower = target_track_name.lower()
        target_artist_lower = target_artist_name.lower()
        
        # Score track title match
        if plex_track_title == target_track_lower:
            score += 100  # Exact match
        elif target_track_lower in plex_track_title or plex_track_title in target_track_lower:
            score += 70   # Partial match
        elif self._fuzzy_match(plex_track_title, target_track_lower):
            score += 50   # Fuzzy match
        
        # Score artist name match
        if plex_artist_name == target_artist_lower:
            score += 100  # Exact match
        elif target_artist_lower in plex_artist_name or plex_artist_name in target_artist_lower:
            score += 70   # Partial match
        elif self._fuzzy_match(plex_artist_name, target_artist_lower):
            score += 50   # Fuzzy match
        
        # Bonus for MusicBrainz ID match if available
        if mbids:
            plex_guid = track.get("guid", "").lower()
            for mbid in mbids:
                if mbid.lower() in plex_guid:
                    score += 50  # MusicBrainz ID bonus
                    break
        
        return score

    def _fuzzy_match(self, str1, str2, threshold=0.8):
        """
        Simple fuzzy string matching using character overlap.
        Returns True if strings are similar enough.
        """
        if not str1 or not str2:
            return False
            
        # Remove common words that might cause false matches
        common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after']
        
        def clean_string(s):
            words = s.split()
            return ' '.join([w for w in words if w not in common_words])
        
        clean_str1 = clean_string(str1)
        clean_str2 = clean_string(str2)
        
        # Character overlap ratio
        set1 = set(clean_str1.replace(' ', ''))
        set2 = set(clean_str2.replace(' ', ''))
        
        if not set1 or not set2:
            return False
            
        overlap = len(set1.intersection(set2))
        total = len(set1.union(set2))
        
        return (overlap / total) >= threshold
