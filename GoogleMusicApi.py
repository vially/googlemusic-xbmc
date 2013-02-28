import sys
import GoogleMusicLogin
from gmusicapi.api import Api

class GoogleMusicApi():
    def __init__(self):
        self.storage = sys.modules["__main__"].storage

        self.gmusicapi = Api(debug_logging=False)
        self.login = GoogleMusicLogin.GoogleMusicLogin(self.gmusicapi)

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
            api_songs = self.gmusicapi.get_all_songs()
        else:
            api_songs = self.gmusicapi.get_playlist_songs(playlist_id)
 
        if api_songs:
            self.storage.storeApiSongs(api_songs, playlist_id)

    def updatePlaylists(self, playlist_type):
        self.login.login()
        playlists = self.gmusicapi.get_all_playlist_ids(playlist_type)
        self.storage.storePlaylists(playlists[playlist_type], playlist_type)

    def getSongStreamUrl(self, song_id):
        self.login.login()
        stream_url = self.gmusicapi.get_stream_url(song_id)
        #self.storage.updateSongStreamUrl(song_id, stream_url)

        return stream_url

    def getFilterSongs(self, filter_type, filter_criteria):
        songs = self.storage.getFilterSongs(filter_type, filter_criteria)

        return songs

    def getCriteria(self, criteria):
        return self.storage.getCriteria(criteria)
        
    def getSearch(self, query):
        return self.storage.getSearch(query)

    def clearCache(self):
        self.storage.clearCache()
        self.login.clearCookie()

    def clearCookie(self):
        self.login.clearCookie()
