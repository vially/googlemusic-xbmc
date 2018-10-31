import utils
from GoogleMusicStorage import storage

class GoogleMusicApi():
    def __init__(self):
        self.api        = None
        self.device     = None
        self.login      = None
        self.artistInfo = {}
        self.miss       = 0

    def getApi(self,nocache=False):
        if self.api == None :
            import GoogleMusicLogin
            self.login = GoogleMusicLogin.GoogleMusicLogin()
            self.login.login(nocache)
            self.api = self.login.getApi()
            self.device = self.login.getDevice()
        return self.api

    def getDevice(self):
        if self.device == None:
            self.getApi()
        return self.device

    def getLogin(self):
        if self.login == None:
            self.getApi()
        return self.login

    def clearCache(self):
        storage.clearCache()

    def clearCookie(self):
        self.getLogin().clearCookie()

    def getPlaylistSongs(self, playlist_id, forceRenew=False):
        if playlist_id in ('videos','thumbsup','lastadded','mostplayed','freepurchased','feellucky'):
            if playlist_id == 'thumbsup':
                """ Try to fetch store thumbs up songs """
                songs = self._loadStoreTracks(self.getApi().get_promoted_songs())
            else:
                songs = storage.getAutoPlaylistSongs(playlist_id)
        else:
            if forceRenew:
                self.updatePlaylistSongs()
            songs = storage.getPlaylistSongs(playlist_id)

        return songs

    def getPlaylistsByType(self, playlist_type, forceRenew=False):
        if forceRenew:
            self.updatePlaylistSongs()

        return storage.getPlaylists()

    def getSong(self, song_id):
        return storage.getSong(song_id)

    def loadLibrary(self):
        gen = self.getApi().get_all_songs(incremental=True)

        uploaded_songs=0
        for chunk in gen:
            utils.log("Chunk Size: "+repr(len(chunk)))
            uploaded_songs += len(chunk)
            storage.storeInAllSongs(chunk)

        self.updatePlaylistSongs()

        if utils.addon.getSetting('load_kodi_library')=='true':
            try:
                storage.loadKodiLib()
            except Exception as ex:
                utils.log("ERROR trying to load local library: "+repr(ex))

        import time
        utils.addon.setSetting("fetched_all_songs", str(time.time()))
        utils.addon.setSetting("library_songs", str(uploaded_songs))


    def updatePlaylistSongs(self):
        storage.storePlaylistSongs(self.getApi().get_all_user_playlist_contents())

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
            song['rating'] = thumbs
            self.getApi().change_song_metadata(song)
        else:
            self.getApi().change_song_metadata({'id':song_id,'rating':thumbs})
        storage.setThumbs(song_id, thumbs)

    def getFilterSongs(self, filter_type, filter_criteria, albums):
        return storage.getFilterSongs(filter_type, filter_criteria, albums)

    def getCriteria(self, criteria, artist=''):
        return storage.getCriteria(criteria,artist)

    def getSearch(self, query, max_results=10):
        import urllib	
        query = urllib.unquote(query).decode('utf8')
        utils.log("API getsearch: "+query)
        result = storage.getSearch(query, max_results)
        #result = {'tracks':[],'albums':[],'artists':[]}
        tracks = result['tracks']
        albums = result['albums']
        artists = result['artists']
        stations = []
        videos = []
        result['stations'] = stations
        result['videos'] = videos
        try:
            store_result = self.getApi().search(query, max_results)
            #utils.log("API getsearch aa: "+repr(store_result))
            tracks.extend(self._loadStoreTracks(store_result['song_hits']))
            albums.extend(self._loadStoreAlbums(store_result['album_hits']))
            artists.extend([artist['artist'] for artist in store_result['artist_hits']])
            stations.extend([station['station'] for station in store_result['station_hits']])
            videos.extend([video['youtube_video'] for video in store_result['video_hits']])
            utils.log("API search results: tracks "+repr(len(tracks))+" albums "+repr(len(albums))
                     +" artists "+repr(len(artists))+" stations "+repr(len(stations))+" videos "+repr(len(videos)))
        except Exception as e:
            utils.log("*** NO ALL ACCESS RESULT IN SEARCH *** "+repr(e))
        return result

    def getAlbum(self, albumid):
        return self._loadStoreTracks(self.getApi().get_album_info(albumid, include_tracks=True)['tracks'])

    def getArtistInfo(self, artistid, albums=False, tracks=20, relartists=0):
        info = self.getApi().get_artist_info(artistid, include_albums=albums, max_top_tracks=tracks, max_rel_artist=relartists)
        result = {}
        result['tracks']     = self._loadStoreTracks(info['topTracks']) if 'topTracks' in info else None
        result['relartists'] = info['related_artists'] if 'related_artists' in info else None
        result['albums']     = self._loadStoreAlbums(info['albums']) if 'albums' in info else None
        return result

    def getTrack(self, trackid):
        #return self._convertStoreTrack(self.getApi().get_track_info(trackid))
        return self._loadStoreTracks([self.getApi().get_track_info(trackid)])[0]

    def getSharedPlaylist(self, sharetoken):
        return self._loadStoreTracks(self.getApi().get_shared_playlist_contents(sharetoken))

    def getStations(self):
        stations = {}
        try:
            stations = self.getApi().get_all_stations()
            #utils.log("STATIONS: "+repr(stations))
        except Exception as e:
            utils.log("*** NO STATIONS *** "+repr(e))
        return stations

    def getStationTracks(self, station_id):
        return self._loadStoreTracks(self.getApi().get_station_tracks(station_id, num_tracks=200))

    def startRadio(self, name,
                   track_id=None, artist_id=None, album_id=None,
                   genre_id=None, playlist_token=None, curated_station_id=None):
        station=self.getApi().create_station(name, track_id, artist_id, album_id, genre_id, playlist_token, curated_station_id)
        #tracks = self._loadStoreTracks(station['tracks'])
        if 'sessionToken' in station:
            import random
            station_arts = ''
            if 'compositeArtRefs' in station and len(station['compositeArtRefs']) > 0:
                station_arts = station['compositeArtRefs']
            utils.log("Free Radio token: "+station['sessionToken'])
            #utils.log(repr(station))
            result = []
            for track in station['tracks']:
                track_conv = self._convertStoreTrack(track)
                track_conv['sessiontoken'] = station['sessionToken']
                if station_arts:
                    track_conv['artistart'] = station_arts[random.randint(0,len(station_arts)-1)]['url']
                result.append(track_conv)
            return result
        return self._loadStoreTracks(station['tracks'])
        #return self.getApi().create_station(name, track_id=song_id)

    def addStoreTrack(self, song_id):
        self.getApi().add_store_track(song_id)

    def addToPlaylist(self, playlist_id, song_id):
        entry_id = self.getApi().add_songs_to_playlist(playlist_id, song_id)
        storage.addToPlaylist(playlist_id, song_id, entry_id[0])

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = storage.delFromPlaylist(playlist_id, song_id)
        self.getApi().remove_entries_from_playlist(entry_id)

    def getTopcharts(self, content_type='tracks'):
        content = self.getApi().get_top_chart()
        if content_type == 'tracks':
            return self._loadStoreTracks(content['tracks'])
        if content_type == 'albums':
            return self._loadStoreAlbums(content['albums'])

    def getNewreleases(self):
        return self._loadStoreAlbums(self.getApi().get_new_releases())

    def _loadArtistArt(self, artistid):
        if not artistid in self.artistInfo:
            artistart = storage.getArtist(artistid)
            if artistart:
                self.artistInfo[artistid] = {'artistArtRefs':[{'url':artistart}]}
            else:
                self.miss += 1
                self.artistInfo[artistid] = self.getApi().get_artist_info(artistid, include_albums=False, max_top_tracks=0, max_rel_artist=0)
                if 'artistArtRefs' in self.artistInfo[artistid]:
                    storage.setArtist(artistid, self.artistInfo[artistid]['artistArtRefs'][0]['url'])
                else:
                    utils.log("NO ART FOR ARTIST: "+repr(self.artistInfo[artistid]))
                    self.artistInfo[artistid] = {'artistArtRefs':[{'url':''}]}
        return self.artistInfo[artistid]['artistArtRefs']

    def _loadStoreAlbums(self, albums):
        result    = []
        self.miss = 0

        for item in albums:
            if 'album' in item:
                item = item['album']
            if not 'artistArtRef' in item and 'artistId' in item and item['artistId'][0] :
                item['artistArtRef'] = self._loadArtistArt(item['artistId'][0])[0]['url']
            else:
                item['artistArtRef'] = utils.addon.getAddonInfo('fanart')
            result.append(item)

        utils.log("Loaded %d albums (%d art miss)" % (len(albums), self.miss) )
        return result

    def _loadStoreTracks(self, tracks):
        result    = []
        self.miss = 0

        for item in tracks:
            if 'track' in item:
                item = item['track']
            if not 'artistArtRef' in item and 'artistId' in item and item['artistId'][0]:
                item['artistArtRef'] = self._loadArtistArt(item['artistId'][0])
            result.append(self._convertStoreTrack(item))

        utils.log("Loaded %d tracks (%d art miss)" % (len(tracks), self.miss) )
        return result


    def _convertStoreTrack(self, track):
        return { 'song_id':       track.get('id') or track['storeId'],
                 'album':         track.get('album'),
                 'title':         track['title'],
                 'year':          track.get('year', 0),
                 'rating':        track.get('rating', 0),
                 'album_artist':  track.get('albumArtist'),
                 'tracknumber':   track.get('trackNumber',0),
                 'playcount':     track.get('playCount', 0),
                 'artist':        track.get('artist'),
                 'genre':         track.get('genre'),
                 'discnumber':    track.get('discNumber',0),
                 'duration':      int(track.get('durationMillis',0))/1000,
                 'albumart':      track['albumArtRef'][0]['url'] if track.get('albumArtRef') else utils.addon.getAddonInfo('icon'),
                 'display_name':  track.get('artist')+" - "+track['title'],
                 'artistart':     track['artistArtRef'][0]['url'] if track.get('artistArtRef') else utils.addon.getAddonInfo('fanart'),
                 'videoid':       track.get('primaryVideo',{'id':""})['id'],
                 'wentryid':      track.get('wentryid'),
                }

