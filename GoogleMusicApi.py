import utils
from GoogleMusicStorage import storage

class GoogleMusicApi():
    def __init__(self):
        self.api      = None
        self.device   = None
        self.login    = None

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
        self.clearCookie()

    def clearCookie(self):
        self.getLogin().clearCookie()

    def getPlaylistSongs(self, playlist_id, forceRenew=False):
        if playlist_id in ('thumbsup','lastadded','mostplayed','freepurchased','feellucky'):
            songs = storage.getAutoPlaylistSongs(playlist_id)
            if playlist_id == 'thumbsup':
                """ Try to fetch all access thumbs up songs """
                for track in self.getApi().get_promoted_songs():
                    songs.append(self._convertAATrack(track))
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

        for chunk in gen:
            utils.log("Chunk Size: "+repr(len(chunk)))
            api_songs = []
            for song in chunk:
                api_songs.append(song)
            storage.storeApiSongs(api_songs)

        self.updatePlaylistSongs()

        if utils.addon.getSetting('load_kodi_library')=='true':
            try:
                storage.loadKodiLib()
            except Exception as ex:
                utils.log("ERROR trying to load local library: "+repr(ex))

    def updatePlaylistSongs(self):
        storage.storePlaylistSongs(self.getApi().get_all_user_playlist_contents())

    def getSongStreamUrl(self, song_id):
        stream_url = self.getLogin().getStreamUrl(song_id)
        return stream_url

    def incrementSongPlayCount(self, song_id):
        try:
            self.getApi().increment_song_playcount(song_id)
        except Exception as ex:
            utils.log("ERROR trying to increment playcount: "+repr(ex))
        storage.incrementSongPlayCount(song_id)

    def getFilterSongs(self, filter_type, filter_criteria, albums):
        return storage.getFilterSongs(filter_type, filter_criteria, albums)

    def getCriteria(self, criteria, artist=''):
        return storage.getCriteria(criteria,artist)

    def getSearch(self, query):
        utils.log("API getsearch: "+query)
        result = storage.getSearch(query)
        tracks = result['tracks']
        albums = result['albums']
        artists = result['artists']
        try:
            aaresult = self.getApi().search_all_access(query)
            #utils.log("API getsearch aa: "+repr(aaresult))
            for song in aaresult['song_hits']:
                track = song['track']
                #utils.log("RESULT SONGS: "+repr(track['artist'])+" - "+repr(track['title'])+" "+track['nid'])
                tracks.append(self._convertAATrack(track))
            for album in aaresult['album_hits']:
                #utils.log("RESULT ALBUMS: "+repr(album['album']['name'])+" - "+repr(album['album']['artist'])+" "+album['album']['albumId'])
                albumDict = album['album']
                albums.append([albumDict['name'],albumDict['artist'],albumDict.get('albumArtRef',''),albumDict['albumId']])
            for artist in aaresult['artist_hits']:
                artistDict = artist['artist']
                artists.append([artistDict['name'],artistDict.get('artistArtRef',''),artistDict['artistId']])
            utils.log("API search results: tracks "+repr(len(tracks))+" albums "+repr(len(albums))+" artists "+repr(len(artists)))
        except Exception as e:
            utils.log("*** NO ALL ACCESS RESULT IN SEARCH *** "+repr(e))
            #tracksAA = storage.getAutoPlaylistSongs('thumbsup')
        return result

    def getAlbum(self, albumid):
        return self._loadAATracks(self.getApi().get_album_info(albumid, include_tracks=True)['tracks'])

    def getArtist(self, artistid):
        return self._loadAATracks(self.getApi().get_artist_info(artistid, include_albums=False, max_top_tracks=50, max_rel_artist=0)['topTracks'])

    def getTrack(self, trackid):
        return self._convertAATrack(self.getApi().get_track_info(trackid))

    def getSharedPlaylist(self, sharetoken):
        return self._loadAATracks(self.getApi().get_shared_playlist_contents(sharetoken))

    def getStations(self):
        stations = {}
        try:
            stations = self.getApi().get_all_stations()
            utils.log("STATIONS: "+repr(stations))
        except Exception as e:
            utils.log("*** NO STATIONS *** "+repr(e))
        return stations

    def getStationTracks(self, station_id):
        return self._loadAATracks(self.getApi().get_station_tracks(station_id, num_tracks=200))

    def startRadio(self, name, song_id):
        return self.getApi().create_station(name, track_id=song_id)

    def addAAtrack(self, song_id):
        self.getApi().add_aa_track(song_id)

    def addToPlaylist(self, playlist_id, song_id):
        entry_id = self.getApi().add_songs_to_playlist(playlist_id, song_id)
        storage.addToPlaylist(playlist_id, song_id, entry_id[0])

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = storage.delFromPlaylist(playlist_id, song_id)
        self.getApi().remove_entries_from_playlist(entry_id)

    def getTopcharts(self, content_type='tracks'):
        content = self.getApi().get_top_chart()
        if content_type == 'tracks':
            return self._loadAATracks(content['tracks'])
        if content_type == 'albums':
            albums = []
            for item in content['albums']:
                albums.append([item['name'],item['artist'],item.get('albumArtRef',''),item['albumId']])
            return albums

    def getNewreleases(self):
        albums = []
        content = self.getApi().get_new_releases()
        for item in content:
            print repr(item)
            album = item['album']
            albums.append([album['name'],album['artist'],album.get('albumArtRef',''),album['albumId']])
        return albums

    def _loadAATracks(self, tracks):
        result = []
        artistInfo = {}
        try:
            for track in tracks:
                if 'track' in track:
                    track = track['track']
                if not 'artistArtRef' in track:
                    artistId = track['artistId'][0]
                    if not artistId in artistInfo:
                        artistInfo[artistId] = self.getApi().get_artist_info(artistId, include_albums=False, max_top_tracks=0, max_rel_artist=0)
                    if 'artistArtRefs' in artistInfo[artistId]:
                        track['artistArtRef'] = artistInfo[artistId]['artistArtRefs']
                result.append(self._convertAATrack(track))
        except Exception as e:
            utils.log("*** NO ALL ACCESS TRACKS *** "+repr(e))
        return result


    def _convertAATrack(self, aaTrack):
        return [aaTrack.get('id') or aaTrack['storeId'],'',0,0,0,'',0,aaTrack.get('album'),
                aaTrack['title'],aaTrack['albumArtist'],0,
                aaTrack['trackNumber'],0,0,'',aaTrack.get('playCount', 0),0,aaTrack['title'],
                aaTrack['artist'],'',0,int(aaTrack['durationMillis'])/1000,
                aaTrack['albumArtRef'][0]['url'] if aaTrack.get('albumArtRef') else utils.addon.getAddonInfo('icon'),
                aaTrack['artist']+" - "+aaTrack['title'],'',
                aaTrack['artistArtRef'][0]['url'] if aaTrack.get('artistArtRef') else utils.addon.getAddonInfo('fanart')]
