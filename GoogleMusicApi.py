import sys

class GoogleMusicApi():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.storage   = self.main.storage
        self.api       = None
        self.device    = None
        self.login     = None

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

    def getPlaylistSongs(self, playlist_id, forceRenew=False):
        if playlist_id in ('thumbsup','lastadded','mostplayed','freepurchased','feellucky'):
            songs = self.storage.getAutoPlaylistSongs(playlist_id)
            if playlist_id == 'thumbsup':
                """ Try to fetch all access thumbs up songs """
                for track in self.getApi().get_thumbs_up_songs():
                    songs.append(self._convertAATrack(track))
        else:
            if forceRenew:
                self.updatePlaylistSongs()
            songs = self.storage.getPlaylistSongs(playlist_id)

        return songs

    def getPlaylistsByType(self, playlist_type, forceRenew=False):
        if playlist_type == 'auto':
            return [['thumbsup','Highly Rated'],['lastadded','Last Added'],
                    ['freepurchased','Free and Purchased'],['mostplayed','Most Played']]

        if forceRenew:
            self.updatePlaylistSongs()

        return self.storage.getPlaylists()

    def getSong(self, song_id):
        return self.storage.getSong(song_id)

    def loadLibrary(self):
        api_songs = self.getApi().get_all_songs()
        self.main.log("Library Size: "+repr(len(api_songs)))
        #self.main.log("First Song: "+repr(api_songs[0]))
        self.storage.storeApiSongs(api_songs, 'all_songs')

        self.updatePlaylistSongs()

    def updatePlaylistSongs(self):
        self.storage.storePlaylistSongs(self.getApi().get_all_user_playlist_contents())

    def getSongStreamUrl(self, song_id):
        stream_url = self.getLogin().getStreamUrl(song_id)
        self.storage.updateSongStreamUrl(song_id, stream_url)
        return stream_url

    def incrementSongPlayCount(self, song_id):
        try:
            self.getApi().increment_song_playcount(song_id)
        except Exception as ex:
            self.main.log("ERROR trying to increment playcount: "+repr(ex))
        self.storage.incrementSongPlayCount(song_id)

    def getFilterSongs(self, filter_type, filter_criteria, albums):
        return self.storage.getFilterSongs(filter_type, filter_criteria, albums)

    def getCriteria(self, criteria, artist=''):
        return self.storage.getCriteria(criteria,artist)

    def getSearch(self, query):
        self.main.log("API getsearch: "+query)
        result = self.storage.getSearch(query)
        tracks = result['tracks']
        albums = result['albums']
        artists = result['artists']
        #if True:
        try:
            aaresult = self.getApi().search_all_access(query)
            self.main.log("API getsearch aa: "+repr(aaresult))
            for song in aaresult['song_hits']:
                track = song['track']
                #self.main.log("RESULT SONGS: "+repr(track['artist'])+" - "+repr(track['title'])+" "+track['nid'])
                tracks.append(self._convertAATrack(track))
            for album in aaresult['album_hits']:
                #self.main.log("RESULT ALBUMS: "+repr(album['album']['name'])+" - "+repr(album['album']['artist'])+" "+album['album']['albumId'])
                albums.append([album['album']['name'],album['album']['artist'],album['album'].get('albumArtRef',''),album['album']['albumId']])
            #albums.append(['Toto IV (Alben für die Ewigkeit)','Toto',''])
            for artist in aaresult['artist_hits']:
                artists.append([artist['artist']['name'],artist['artist'].get('artistArtRef',''),artist['artist']['artistId']])
            self.main.log("API search results: tracks "+repr(len(tracks))+" albums "+repr(len(albums))+" artists "+repr(len(artists)))
        except Exception as e:
            self.main.log("*** NO ALL ACCESS RESULT IN SEARCH *** "+repr(e))
            #tracksAA = self.storage.getAutoPlaylistSongs('thumbsup')
        return result

    def getAlbum(self, albumid):
        result = []
        try:
            for track in self.getApi().get_album_info(albumid, include_tracks=True)['tracks']:
                result.append(self._convertAATrack(track))
        except Exception as e:
            self.main.log("*** NO ALL ACCESS ALBUM *** "+albumid+' '+repr(e))
        return result

    def getArtist(self, artistid):
        result = []
        try:
            for track in self.getApi().get_artist_info(artistid, include_albums=False, max_top_tracks=50, max_rel_artist=0)['topTracks']:
                result.append(self._convertAATrack(track))
        except Exception as e:
            self.main.log("*** NO ALL ACCESS ARTIST *** "+artistid+' '+repr(e))
        return result

    def getTrack(self, trackid):
        return self._convertAATrack(self.getApi().get_track_info(trackid))

    def getSharedPlaylist(self, sharetoken):
        result = []
        try:
            for track in self.getApi().get_shared_playlist_contents(sharetoken):
                result.append(self._convertAATrack(track['track']))
        except Exception as e:
            self.main.log("*** NO ALL ACCESS SHARED PLAYLIST *** "+sharetoken+' '+repr(e))
        return result

    def clearCache(self):
        self.storage.clearCache()
        self.clearCookie()

    def clearCookie(self):
        self.getLogin().clearCookie()

    def getStations(self):
        stations = {}
        try:
            stations = self.getApi().get_all_stations()
            #self.main.log("STATIONS: "+repr(stations))
        except Exception as e:
            self.main.log("*** NO STATIONS *** "+repr(e))
        return stations

    def getStationTracks(self, station_id):
        songs = []
        try:
            for track in self.getApi().get_station_tracks(station_id):
                songs.append(self._convertAATrack(track))
        except Exception as e:
            self.main.log("*** NO TRACKS *** "+repr(e))
        return songs

    def addAAtrack(self, song_id):
        self.getApi().add_aa_track(song_id)

    def addToPlaylist(self, playlist_id, song_id):
        entry_id = self.getApi().add_songs_to_playlist(playlist_id, song_id)
        self.storage.addToPlaylist(playlist_id, song_id, entry_id[0])

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = self.storage.delFromPlaylist(playlist_id, song_id)
        self.getApi().remove_entries_from_playlist(entry_id)

    def _convertAATrack(self, aaTrack):
        return [aaTrack.get('id') or aaTrack['storeId'],'',0,0,0,'',0,aaTrack.get('album'),
                aaTrack['artist']+" - "+aaTrack['title'],aaTrack['albumArtist'],0,
                aaTrack['trackNumber'],0,0,'',aaTrack.get('playCount', 0),0,aaTrack['title'],
                aaTrack['artist'],'',0,int(aaTrack['durationMillis'])/1000,
                aaTrack['albumArtRef'][0]['url'] if aaTrack.get('albumArtRef') else '',
                aaTrack['artist']+" - "+aaTrack['title'],'',
                aaTrack.get('artistArtRef') if aaTrack.get('artistArtRef') else '']