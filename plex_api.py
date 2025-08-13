import requests
import time
import xml.etree.ElementTree as ET
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

        # Handle both XML and JSON responses
        content_type = r.headers.get('content-type', '').lower()
        if 'xml' in content_type:
            return self._parse_xml_response(r.text)
        elif r.text.strip():
            try:
                return r.json()
            except ValueError:
                print(f"Warning: Non-JSON response from {path}: {r.text[:100]}")
                return {}
        else:
            print(f"Warning: Empty response from {path}")
            return {}

    def _post(self, path, params=None, data=None):
        """POST request to Plex API"""
        if params is None:
            params = {}
        params["X-Plex-Token"] = self.token
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
        }
        r = requests.post(url, params=params, data=data, headers=headers)
        r.raise_for_status()

        # Handle both XML and JSON responses
        content_type = r.headers.get('content-type', '').lower()
        if 'xml' in content_type:
            return self._parse_xml_response(r.text)
        elif r.text.strip():
            try:
                return r.json()
            except ValueError:
                print(f"Warning: Non-JSON response from {path}: {r.text[:100]}")
                return {}
        else:
            print(f"Warning: Empty response from {path}")
            return {}

    def _put(self, path, params=None, data=None):
        """PUT request to Plex API"""
        if params is None:
            params = {}
        params["X-Plex-Token"] = self.token
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
        }
        r = requests.put(url, params=params, data=data, headers=headers)
        r.raise_for_status()

        # Handle both XML and JSON responses
        content_type = r.headers.get('content-type', '').lower()
        if 'xml' in content_type:
            return self._parse_xml_response(r.text)
        elif r.text.strip():
            try:
                return r.json()
            except ValueError:
                return {}
        else:
            return {}

    def _delete(self, path, params=None):
        """DELETE request to Plex API"""
        if params is None:
            params = {}
        params["X-Plex-Token"] = self.token
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
        }
        r = requests.delete(url, params=params, headers=headers)
        r.raise_for_status()
        return {} if not r.content else {}

    def _parse_xml_response(self, xml_text):
        """Parse XML response and convert to JSON-like structure"""
        try:
            root = ET.fromstring(xml_text)
            result = {"MediaContainer": self._xml_element_to_dict(root)}
            return result
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return {}

    def _xml_element_to_dict(self, element):
        """Convert XML element to dictionary"""
        result = {}

        # Add attributes
        if element.attrib:
            result.update(element.attrib)

        # Handle child elements
        children = list(element)
        if children:
            child_dict = {}
            for child in children:
                child_data = self._xml_element_to_dict(child)
                if child.tag in child_dict:
                    # Multiple children with same tag - make it a list
                    if not isinstance(child_dict[child.tag], list):
                        child_dict[child.tag] = [child_dict[child.tag]]
                    child_dict[child.tag].append(child_data)
                else:
                    child_dict[child.tag] = child_data

            # For MediaContainer, put child elements in appropriate arrays for compatibility
            if element.tag == "MediaContainer":
                metadata_items = []
                directory_items = []

                for child in children:
                    child_data = self._xml_element_to_dict(child)
                    if child.tag in ["Playlist", "Track", "Artist", "Album", "Video"]:
                        metadata_items.append(child_data)
                    elif child.tag == "Directory":
                        directory_items.append(child_data)
                    else:
                        # Other child elements go directly into result
                        if child.tag in child_dict:
                            if not isinstance(result.get(child.tag), list):
                                result[child.tag] = [result.get(child.tag, child_dict[child.tag])]
                            result[child.tag].append(child_data)
                        else:
                            result[child.tag] = child_data

                if metadata_items:
                    result["Metadata"] = metadata_items
                if directory_items:
                    result["Directory"] = directory_items
                    # Also add directories as Metadata for compatibility with library sections
                    if not metadata_items:
                        result["Metadata"] = directory_items
            else:
                result.update(child_dict)

        # Add text content if present
        if element.text and element.text.strip():
            if children:
                result["text"] = element.text.strip()
            else:
                return element.text.strip()

        return result

    def get_music_libraries(self):
        """Get all music library sections"""
        try:
            results = self._get("/library/sections")
            media_container = results.get("MediaContainer", {})

            # Handle both XML and JSON response formats
            # In XML, library sections are Directory elements
            sections = media_container.get("Directory", [])
            if not sections:
                # Fallback to Metadata for JSON responses
                sections = media_container.get("Metadata", [])

            music_sections = []
            for section in sections:
                section_type = section.get("type", "")
                section_title = section.get("title", "")
                section_key = section.get("key", "")

                # Check for music/audio library types
                # 'artist' type indicates a music library in Plex
                if section_type in ("artist", "music", "audio"):
                    music_sections.append({
                        "key": section_key,
                        "title": section_title,
                        "type": section_type
                    })

            return music_sections

        except Exception as e:
            print(f"❌ Error getting music libraries: {e}")
            return []

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

        # Try different search strategies with more partial matches
        search_queries = [
            f"{artist_name} {track_name}",      # Artist + Track
            f"{track_name} {artist_name}",      # Track + Artist
            track_name,                         # Just track name
            artist_name,                        # Just artist name
            # Add partial searches for better matching
            " ".join(track_name.split()[:3]),   # First 3 words of track
            " ".join(track_name.split()[:2]),   # First 2 words of track
            " ".join(track_name.split()[-3:]),  # Last 3 words of track
            " ".join(track_name.split()[1:4]),  # Middle words of track
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

    # PLAYLIST METHODS - Core functionality for playlist management

    def find_playlist_by_name(self, playlist_name):
        """Find a playlist by name. Returns playlist metadata if found, None otherwise."""
        try:
            results = self._get("/playlists")
            media_container = results.get("MediaContainer", {})
            playlists = media_container.get("Metadata", [])

            for playlist in playlists:
                if playlist.get("title", "").lower() == playlist_name.lower():
                    return playlist

            return None
        except Exception as e:
            print(f"Error finding playlist '{playlist_name}': {e}")
            return None

    def create_playlist(self, title, track_rating_keys, summary=""):
        """
        Create a new playlist with the given tracks.
        Uses hybrid approach - create with 1 track, then add the rest.

        Args:
            title: Playlist title
            track_rating_keys: List of track ratingKeys to add
            summary: Optional playlist description

        Returns:
            True if successful, False otherwise
        """
        try:
            if not track_rating_keys:
                print("No tracks provided for playlist creation")
                return False

            print(f"🎵 Creating playlist '{title}' using hybrid method (1 track + add remaining)...")

            base_url = self.base_url
            token = self.token

            # Step 1: Create playlist with first track only
            first_track = track_rating_keys[0]
            uri = f"library://{base_url.split('://')[1]}/item/library%2Fmetadata%2F{first_track}"

            params = {
                "X-Plex-Token": token,
                "title": title,
                "type": "audio",
                "uri": uri
            }

            print(f"🔨 Creating playlist with first track...")
            headers = {"Accept": "application/json"}
            response = requests.post(f"{base_url}/playlists", params=params, headers=headers)
            response.raise_for_status()

            print(f"✅ Created playlist with 1 track")

            # Step 2: Add remaining tracks if there are any
            if len(track_rating_keys) > 1:
                remaining_tracks = track_rating_keys[1:]
                print(f"📝 Adding {len(remaining_tracks)} remaining tracks...")

                # Find the created playlist to get its ratingKey
                time.sleep(2)  # Give Plex time to create the playlist

                created_playlist = self.find_playlist_by_name(title)
                if created_playlist:
                    playlist_rating_key = created_playlist["ratingKey"]
                    add_success = self.add_tracks_to_playlist(playlist_rating_key, remaining_tracks)

                    if add_success:
                        print(f"✅ Successfully created playlist '{title}' with {len(track_rating_keys)} tracks total")
                        return True
                    else:
                        print(f"⚠️  Playlist created with 1 track, but failed to add {len(remaining_tracks)} remaining tracks")
                        return True  # Partial success is still success
                else:
                    print(f"❌ Could not find created playlist to add remaining tracks")
                    return False
            else:
                print(f"✅ Successfully created playlist '{title}' with 1 track")
                return True

        except Exception as e:
            print(f"❌ Error creating playlist '{title}': {e}")
            return False

    def add_tracks_to_playlist(self, playlist_rating_key, track_rating_keys):
        """
        Add tracks to an existing playlist.
        This Plex server requires adding tracks ONE AT A TIME.

        Args:
            playlist_rating_key: The ratingKey of the playlist
            track_rating_keys: List of track ratingKeys to add

        Returns:
            True if successful, False otherwise
        """
        try:
            if not track_rating_keys:
                print("No tracks provided to add to playlist")
                return False

            print(f"📝 Adding {len(track_rating_keys)} tracks one by one...")

            base_url = self.base_url
            token = self.token
            total_added = 0

            for i, key in enumerate(track_rating_keys, 1):
                try:
                    # Add each track individually
                    uri = f"library://{base_url.split('://')[1]}/item/library%2Fmetadata%2F{key}"
                    params = {
                        "X-Plex-Token": token,
                        "uri": uri
                    }

                    add_url = f"{base_url}/playlists/{playlist_rating_key}/items"
                    headers = {"Accept": "application/json"}
                    response = requests.put(add_url, params=params, headers=headers)
                    response.raise_for_status()

                    total_added += 1

                    # Progress indicator every 10 tracks
                    if i % 10 == 0 or i == len(track_rating_keys):
                        print(f"  ✅ Added {i}/{len(track_rating_keys)} tracks")

                    # Small delay to avoid overwhelming the server
                    time.sleep(0.2)

                except Exception as track_error:
                    print(f"  ❌ Failed to add track {i} (key: {key}): {track_error}")
                    continue

            if total_added > 0:
                print(f"✅ Successfully added {total_added}/{len(track_rating_keys)} tracks to playlist")
                return True
            else:
                print(f"❌ Failed to add any tracks to playlist")
                return False

        except Exception as e:
            print(f"❌ Error adding tracks to playlist: {e}")
            return False

    def delete_playlist(self, playlist_rating_key):
        """
        Delete a playlist.

        Args:
            playlist_rating_key: The ratingKey of the playlist to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self._delete(f"/playlists/{playlist_rating_key}")
            print(f"✅ Deleted playlist")
            return True
        except Exception as e:
            print(f"❌ Error deleting playlist: {e}")
            return False

    def create_or_update_playlist(self, title, track_rating_keys, summary=""):
        """
        Create a new playlist or update an existing one with the same name.

        Args:
            title: Playlist title
            track_rating_keys: List of track ratingKeys
            summary: Optional playlist description

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if playlist already exists
            existing_playlist = self.find_playlist_by_name(title)

            if existing_playlist:
                print(f"📝 Found existing playlist '{title}', deleting it first")
                if not self.delete_playlist(existing_playlist["ratingKey"]):
                    print(f"❌ Failed to delete existing playlist")
                    return False

                # Wait a moment for deletion to complete
                time.sleep(2)

            print(f"🆕 Creating new playlist '{title}'")
            return self.create_playlist(title, track_rating_keys, summary)

        except Exception as e:
            print(f"❌ Error creating or updating playlist '{title}': {e}")
            return False

    def get_playlist_tracks(self, playlist_rating_key):
        """
        Get all tracks in a playlist for verification purposes.

        Args:
            playlist_rating_key: The ratingKey of the playlist

        Returns:
            List of track metadata, or empty list if error
        """
        try:
            result = self._get(f"/playlists/{playlist_rating_key}/items")
            media_container = result.get("MediaContainer", {})
            tracks = media_container.get("Metadata", [])
            return tracks
        except Exception as e:
            print(f"❌ Error getting playlist tracks: {e}")
            return []

    def test_plex_connection(self):
        """
        Test basic Plex connectivity and permissions

        Returns:
            True if connection works, False otherwise
        """
        try:
            # Test basic server connection
            result = self._get("/")

            # Test library access
            libraries = self.get_music_libraries()

            # Test playlist access
            playlists_result = self._get("/playlists")
            media_container = playlists_result.get("MediaContainer", {})
            playlists = media_container.get("Metadata", [])

            # Only print summary, not detailed debug info
            print(f"✅ Plex connection test passed: {len(libraries)} music libraries, {len(playlists)} playlists")
            return True

        except Exception as e:
            print(f"❌ Plex connection test failed: {e}")
            return False
