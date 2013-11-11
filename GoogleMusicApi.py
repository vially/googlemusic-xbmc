import sys
import GoogleMusicLogin

class GoogleMusicApi():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.storage   = self.main.storage
        self.login     = GoogleMusicLogin.GoogleMusicLogin()
        self.gmusicapi = self.login.getApi()

    def getPlaylistSongs(self, playlist_id, forceRenew=False):

        if playlist_id == 'thumbsup':
            return self.storage.getThumbsup()
        if playlist_id == 'lastadded':
            return self.storage.getLastadded()
        if playlist_id == 'mostplayed':
            return self.storage.getMostplayed()
        if playlist_id == 'freepurchased':
            return self.storage.getFreepurchased()

        if not self.storage.isPlaylistFetched(playlist_id) or forceRenew:
            self.updatePlaylistSongs(playlist_id)

        songs = self.storage.getPlaylistSongs(playlist_id)

        return songs

    def getPlaylistsByType(self, playlist_type, forceRenew=False):
        if playlist_type == 'auto':
            return [['thumbsup','Highly Rated'],['lastadded','Last Added'],['freepurchased','Free and Purchased'],['mostplayed','Most Played']]

        if forceRenew:
            self.updatePlaylists(playlist_type)

        playlists = self.storage.getPlaylistsByType(playlist_type)
        if len(playlists) == 0 and not forceRenew:
            self.updatePlaylists(playlist_type)
            playlists = self.storage.getPlaylistsByType(playlist_type)

        return playlists

    def getSong(self, song_id):
        return self.storage.getSong(song_id)

    def updatePlaylistSongs(self, playlist_id):
        api_songs = []

        self.login.login()
        if playlist_id == 'all_songs':
            #gen = self.gmusicapi.get_all_songs(incremental=True)
            #for chunk in gen:
            #    for song in chunk:
                    #print song
            #        api_songs.append(song)
            #    break
            #api_songs = [song for chunk in api_songs for song in chunk]
            api_songs = self.gmusicapi.get_all_songs()
            self.main.log("Library Size: "+repr(len(api_songs)))
            self.main.log("First Song: "+repr(api_songs[0]))
        else:
            if self.login.getDevice():
                 self.storage.storePlaylistSongs(self.gmusicapi.get_all_user_playlist_contents())
            else:
                 api_songs = self.gmusicapi.get_playlist_songs(playlist_id)

        if api_songs:
            self.storage.storeApiSongs(api_songs, playlist_id)

    def updatePlaylists(self, playlist_type):
        self.login.login()
        if self.login.getDevice():
            self.storage.storePlaylistSongs(self.gmusicapi.get_all_user_playlist_contents())
        else:
            playlists = self.gmusicapi.get_all_playlist_ids(playlist_type)
            self.storage.storePlaylists(playlists[playlist_type], playlist_type)

    def getSongStreamUrl(self, song_id):

        self.login.login()

        device_id = self.login.getDevice()
        self.main.log("getSongStreamUrl device: "+device_id)

        if device_id:
            stream_url = self.gmusicapi.get_stream_url(song_id, device_id)
        else:
            streams = self.gmusicapi.get_stream_urls(song_id)
            if len(streams) > 1:
                xbmc.executebuiltin("XBMC.Notification("+plugin+",'All Access track not playable')")
                raise Exception('All Access track not playable, no mobile device found in account!')
            stream_url = streams[0]

        self.storage.updateSongStreamUrl(song_id, stream_url)
        self.main.log("getSongStreamUrl: "+stream_url)
        return stream_url

    def getFilterSongs(self, filter_type, filter_criteria):
        songs = self.storage.getFilterSongs(filter_type, filter_criteria)

        return songs

    def getCriteria(self, criteria, artist=''):
        return self.storage.getCriteria(criteria,artist)

    def getSearch(self, query):
        return self.storage.getSearch(query)

    def clearCache(self):
        self.storage.clearCache()
        self.login.clearCookie()

    def clearCookie(self):
        self.login.clearCookie()

    def getStations(self):
        self.login.login()
        stations = {}
        try:
            stations = self.gmusicapi.get_all_stations()
        except Exception as e:
            self.main.log("*** NO STATIONS *** "+repr(e))
        self.main.log("STATIONS: "+repr(stations))
        return stations

    def getStationTracks(self, station_id):
        self.login.login()
        tracks = {}
        try:
            tracks = self.gmusicapi.get_station_tracks(station_id)
            self.main.log("TRACKS *** "+repr(tracks))
        except Exception as e:
            self.main.log("*** NO TRACKS *** "+repr(e))
        return tracks