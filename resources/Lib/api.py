import utils
from storage import storage


class Api:
    def __init__(self):
        self.api = None
        self.login = None
        self.artistInfo = {}
        self.miss = 0

    def getApi(self, nocache=False):
        if self.api is None:
            import login
            self.login = login.Login()
            self.login.login(nocache)
            self.api = self.login.getApi()
        return self.api

    def getLogin(self):
        if self.login is None:
            self.getApi()
        return self.login

    def clearCache(self):
        storage.clearCache()
        storage.init_database()
        storage.init_indexes()

    def clear_auth_cache(self):
        self.getLogin().clear_oauth_cache()

    def getPlaylistSongs(self, playlist_id):
        if playlist_id in ('videos', 'thumbsup', 'lastadded', 'mostplayed', 'freepurchased', 'feellucky'):
            if playlist_id == 'thumbsup':
                """ Try to fetch store thumbs up songs """
                songs = self._loadStoreTracks(self.getApi().get_top_songs())
            else:
                songs = storage.getAutoPlaylistSongs(playlist_id)
        else:
            songs = storage.getPlaylistSongs(playlist_id)

        return songs

    def getPlaylistsByType(self, playlist_type):
        if playlist_type == 'recent':
            return storage.getRecentPlaylists()
        return storage.getPlaylists()

    def getSong(self, song_id):
        return storage.getSong(song_id)

    def getSongStreamUrl(self, song_id, session_token=None, wentry_id=None):
        stream_url = self.getLogin().getStreamUrl(song_id, session_token=session_token, wentry_id=wentry_id)
        return stream_url

    def incrementSongPlayCount(self, song_id):
        self.getApi().increment_song_playcount(song_id)
        storage.incrementSongPlayCount(song_id)

    def createPlaylist(self, name):
        playlist_id = self.getApi().create_playlist(name)
        storage.createPlaylist(name, playlist_id)

    def deletePlaylist(self, playlist_id):
        self.getApi().delete_playlist(playlist_id)
        storage.deletePlaylist(playlist_id)

    def setThumbs(self, song_id, thumbs):
        if song_id[0] == 'T':
            song = self.getApi().get_track_info(song_id)
            self.getApi().rate_songs([song], thumbs)
        else:
            self.getApi().rate_songs([{'id': song_id}], thumbs)
        storage.setThumbs(song_id, thumbs)

    def getFilterSongs(self, filter_type, filter_criteria, albums):
        return storage.getFilterSongs(filter_type, filter_criteria, albums)

    def getCriteria(self, criteria, artist=''):
        return storage.getCriteria(criteria, artist)

    def getSearch(self, query, max_results=10):
        import urllib
        query = urllib.unquote(query).decode('utf8')
        utils.log("API get search: " + query)
        result = storage.getSearch(query, max_results)
        # result = {'tracks':[],'albums':[],'artists':[]}
        tracks = result['tracks']
        albums = result['albums']
        artists = result['artists']
        stations = []
        videos = []
        result['stations'] = stations
        result['videos'] = videos
        try:
            store_result = self.getApi().search(query, max_results)
            # utils.log("API get search aa: "+repr(store_result))
            tracks.extend(self._loadStoreTracks(store_result['song_hits']))
            albums.extend(self._loadStoreAlbums(store_result['album_hits']))
            artists.extend([artist['artist'] for artist in store_result['artist_hits']])
            stations.extend([station['station'] for station in store_result['station_hits']])
            videos.extend([video['youtube_video'] for video in store_result['video_hits']])
            utils.log("API search results: tracks " + repr(len(tracks)) + " albums " + repr(len(albums))
                      + " artists " + repr(len(artists)) + " stations " + repr(len(stations)) + " videos " + repr(len(videos)))
        except Exception as e:
            utils.log("*** NO ALL ACCESS RESULT IN SEARCH *** " + repr(e))
        return result

    def getAlbum(self, albumid):
        return self._loadStoreTracks(self.getApi().get_album_info(albumid, include_tracks=True)['tracks'])

    def getArtistInfo(self, artistid, albums=False, tracks=20, relartists=0):
        info = self.getApi().get_artist_info(artistid, include_albums=albums, max_top_tracks=tracks, max_rel_artist=relartists)
        result = {'tracks': self._loadStoreTracks(info['topTracks']) if 'topTracks' in info else None,
                  'relartists': info['related_artists'] if 'related_artists' in info else None,
                  'albums': self._loadStoreAlbums(info['albums']) if 'albums' in info else None}
        return result

    def getTrack(self, trackid):
        # return self._convertStoreTrack(self.getApi().get_track_info(trackid))
        return self._loadStoreTracks([self.getApi().get_track_info(trackid)])[0]

    def getSharedPlaylist(self, sharetoken):
        return self._loadStoreTracks(self.getApi().get_shared_playlist_contents(sharetoken))

    def getStationsCategories(self):
        categories = utils.get_mem_cache('station_categories')
        if not categories:
            categories = self.getApi().get_station_categories()
            utils.set_mem_cache('station_categories', categories)
        return categories

    def getStations(self):
        stations = utils.get_mem_cache('all_stations')
        if not stations:
            stations = self.getApi().get_all_stations()
            utils.set_mem_cache('all_stations', stations)
        return stations

    def get_situations(self):
        situations = utils.get_mem_cache('situations')
        if not situations:
            situations = self.getApi().get_listen_now_situations()
            utils.set_mem_cache('situations', situations)
        return situations

    def getStationTracks(self, station_id):
        return self._loadStoreTracks(self.getApi().get_station_tracks(station_id, num_tracks=200))

    def startRadio(self, name,
                   track_id=None, artist_id=None, album_id=None,
                   genre_id=None, playlist_token=None, curated_station_id=None):
        station = self.getApi().create_station(name, track_id, artist_id, album_id, genre_id, playlist_token, curated_station_id)
        if 'sessionToken' in station:
            import random
            station_arts = ''
            if 'compositeArtRefs' in station and len(station['compositeArtRefs']) > 0:
                station_arts = station['compositeArtRefs']
            utils.log("Free Radio token: " + station['sessionToken'])
            # utils.log(repr(station))
            result = []
            for track in station['tracks']:
                track_conv = self._convertStoreTrack(track)
                track_conv['sessiontoken'] = station['sessionToken']
                if station_arts:
                    track_conv['artistart'] = station_arts[random.randint(0, len(station_arts) - 1)]['url']
                result.append(track_conv)
            return result
        return self._loadStoreTracks(self.getApi().get_station_tracks(station, 100))

    def addStoreTrack(self, song_id):
        self.getApi().add_store_track(song_id)

    def addToPlaylist(self, playlist_id, song_id):
        entry_id = self.getApi().add_songs_to_playlist(playlist_id, song_id)
        storage.addToPlaylist(playlist_id, song_id, entry_id[0])

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = storage.delFromPlaylist(playlist_id, song_id)
        self.getApi().remove_entries_from_playlist(entry_id)

    def getTopcharts(self, content_type='tracks'):
        content = utils.get_mem_cache('top_chart')
        if not content:
            content = self.getApi().get_top_chart()
            utils.set_mem_cache('top_chart', content)

        if content_type == 'tracks':
            return self._loadStoreTracks(content['tracks'])
        if content_type == 'albums':
            return self._loadStoreAlbums(content['albums'])

    def getNewreleases(self):
        releases = utils.get_mem_cache('new_releases')
        if not releases:
            releases = self.getApi().get_new_releases()
            utils.set_mem_cache('new_releases', releases)
        return self._loadStoreAlbums(releases)

    def _loadArtistArt(self, artistid):
        if artistid not in self.artistInfo:
            artistart = storage.getArtist(artistid)
            if artistart:
                self.artistInfo[artistid] = {'artistArtRefs': [{'url': artistart}]}
            else:
                self.miss += 1
                try:
                    self.artistInfo[artistid] = self.getApi().get_artist_info(artistid, include_albums=False, max_top_tracks=0,
                                                                              max_rel_artist=0)
                except:
                    self.artistInfo[artistid] = {}
                if 'artistArtRefs' in self.artistInfo[artistid]:
                    storage.setArtist(artistid, self.artistInfo[artistid]['artistArtRefs'][0]['url'])
                else:
                    utils.log("NO ART FOR ARTIST: " + repr(artistid))
                    self.artistInfo[artistid] = {'artistArtRefs': [{'url': ''}]}
        return self.artistInfo[artistid]['artistArtRefs']

    def _loadStoreAlbums(self, albums):
        self.miss = 0

        for item in albums:
            if 'album' in item:
                item = item['album']
            if 'artistArtRef' not in item and 'artistId' in item and item['artistId'][0]:
                item['artistArtRef'] = self._loadArtistArt(item['artistId'][0])[0]['url']
            else:
                item['artistArtRef'] = utils.addon.getAddonInfo('fanart')
            yield item

        utils.log("Loaded %d albums (%d art miss)" % (len(albums), self.miss))

    def _loadStoreTracks(self, tracks):
        self.miss = 0

        for item in tracks:
            if 'track' in item:
                item = item['track']
            if not 'artistArtRef' in item and 'artistId' in item and item['artistId'][0]:
                item['artistArtRef'] = self._loadArtistArt(item['artistId'][0])
            yield self._convertStoreTrack(item)

        utils.log("Loaded %d tracks (%d art miss)" % (len(tracks), self.miss))

    def _convertStoreTrack(self, track):
        track['song_id'] = track.get('id') or track['storeId']
        track['title'] = utils.tryEncode(track['title'])
        track['artist'] = utils.tryEncode(track['artist'])
        track['album'] = utils.tryEncode(track['album'])
        track['tracknumber'] = track.get('trackNumber', 0)
        track['playcount'] = track.get('playCount', 0)
        track['discnumber'] = track.get('discNumber', 0)
        track['rating'] = track.get('rating', 0)
        track['year'] = track.get('year', 0)
        track['genre'] = track.get('genre', "")
        track['duration'] = int(track.get('durationMillis', 0)) / 1000
        track['albumart'] = track['albumArtRef'][0]['url'] if track.get('albumArtRef') else utils.addon.getAddonInfo('icon')
        track['display_name'] = track.get('artist') + " - " + track['title']
        track['artistart'] = track['artistArtRef'][0]['url'] if track.get('artistArtRef') else utils.addon.getAddonInfo('fanart')
        track['videoid'] = track.get('primaryVideo', {'id': ""})['id']
        return track
