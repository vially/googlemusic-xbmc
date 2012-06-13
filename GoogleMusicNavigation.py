import sys
import urllib
import GoogleMusicLogin

class GoogleMusicNavigation():
    def __init__(self):
        self.xbmc = sys.modules["__main__"].xbmc
        self.xbmcgui = sys.modules["__main__"].xbmcgui
        self.xbmcplugin = sys.modules["__main__"].xbmcplugin

        self.settings = sys.modules["__main__"].settings
        self.language = sys.modules["__main__"].language
        self.dbg = sys.modules["__main__"].dbg
        self.cache = sys.modules["__main__"].cache
        self.common = sys.modules["__main__"].common
        self.api = sys.modules["__main__"].api

        self.main_menu = (
            {'title':self.language(30201), 'params':{'path':"playlist", 'playlist_id':"all_songs"}},
            {'title':self.language(30202), 'params':{'path':"playlists", 'type':"user"}},
            {'title':self.language(30203), 'params':{'path':"playlists", 'type':"instant"}},
            #{'title':self.language(30204), 'params':{'path':"playlists", 'type':"auto"}}
        )

        self.login = GoogleMusicLogin.GoogleMusicLogin()

    def listMenu(self, params={}):
        get = params.get
        path = get("path", "root")

        if path == "root":
            ''' Show the plugin root menu. '''
            for menu_item in self.main_menu:
                params = menu_item['params']
                cm = []
                if 'playlist_id' in params:
                    cm = self.getPlayAllContextMenuItems(params['playlist_id'])
                self.addFolderListItem(menu_item['title'], params, cm)
        elif path == "playlist":
            self.login.login()
            self.listPlaylistSongs(get("playlist_id"))
        elif path == "playlists":
            self.login.login()
            playlist_type = get('type')
            if playlist_type in ('auto', 'instant', 'user'):
                self.getPlaylists(playlist_type)
            else:
                self.common.log("Invalid playlist type: " + playlist_type)
        else:
            self.common.log("Invalid path: " + get("path"))

        self.xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

    def executeAction(self, params={}):
        get = params.get
        if (get("action") == "play_all"):
            self.login.login()
            self.playAll(params)
        elif (get("action") == "play_song"):
            self.login.login()
            self.playSong(params)
        elif (get("action") == "clear_cache"):
            self.clearCache()
        else:
            self.common.log("Invalid action: " + get("action"))

    def addFolderListItem(self, name, params={}, contextMenu=[]):
        li = self.xbmcgui.ListItem(name)
        li.setProperty("Folder", "true")

        url = sys.argv[0] + '?' + urllib.urlencode(params)

        if len(contextMenu) > 0:
            li.addContextMenuItems(contextMenu, replaceItems=True)

        return self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)

    def createSongListItem(self, song):
        name = self.getSongDisplayName(song)
        li = self.xbmcgui.ListItem(name)
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setInfo(type='music', infoLabels=self.getInfoLabels(song))

        return li

    def addSongItem(self, song, playlist_id):
        song_id = song["id"].encode('utf-8')

        self.cache.set("songInfo-" + song_id, repr(song))

        li = self.createSongListItem(song)
        li.addContextMenuItems(self.getPlayAllContextMenuItems(playlist_id))

        url = '%s?action=play_song&song_id=%s' % (sys.argv[0], song_id)
        return self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li)

    def listPlaylistSongs(self, playlist_id):
        self.common.log("Loading playlist: " + playlist_id)
        if (playlist_id == "all_songs"):
            library = self.api.get_all_songs()
        else:
            library = self.api.get_playlist_songs(playlist_id)

        self.addSongsFromLibrary(library, playlist_id)
        self.common.log("%d tracks found" % len(library))

    def addSongsFromLibrary(self, library, playlist_id):
        for song in library:
            self.addSongItem(song, playlist_id)

    def getPlaylists(self, playlist_type):
        self.common.log("Getting playlists of type: " + playlist_type)
        playlists = self.api.get_all_playlist_ids(playlist_type=="auto", playlist_type=="instant", playlist_type=="user", always_id_lists=True)
        self.common.log(str(playlists[playlist_type]))
        self.addPlaylistsItems(playlists[playlist_type])

    def addPlaylistsItems(self, playlists):
        for playlist_name, playlist in playlists.iteritems():
            for playlist_id in playlist:
                cm = self.getPlayAllContextMenuItems(playlist_id)
                self.addFolderListItem(playlist_name, {'path':"playlist", 'playlist_id':playlist_id}, cm)

    def getPlayAllContextMenuItems(self, playlist):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?playlist=%s&action=play_all)" % (sys.argv[0], playlist)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?playlist=%s&action=play_all&shuffle=true)" % (sys.argv[0], playlist)))
        return cm

    def playAll(self, params={}):
        get = params.get

        playlist = get('playlist')
        self.common.log("Loading playlist: " + playlist)
        if (get("playlist") == "all_songs"):
            library = self.api.get_all_songs()
        else:
            library = self.api.get_playlist_songs(playlist)

        player = self.xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = self.xbmc.PlayList(self.xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = "%s?action=play_song&song_id=%s&playlist=" + get('playlist')
        for song in library:
            song_id = song["id"].encode('utf-8')
            self.cache.set("songInfo-" + song_id, repr(song))

            li = self.createSongListItem(song)
            playlist.add(song_url % (sys.argv[0], song_id), li)

        if (get("shuffle")):
            playlist.shuffle()

        self.xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def playSong(self, params={}):
        get = params.get
        song = eval(self.cache.get("songInfo-" + get("song_id")))
        url = self.api.get_stream_url(get("song_id"))

        li = self.createSongListItem(song)
        li.setPath(url)

        self.xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

    def getSongDisplayName(self, entry):
        displayName = ""
        song = entry.get
        song_name = song("name").encode('utf-8').strip()
        song_artist = song("artist").encode('utf-8').strip()

        if ( (len(song_artist) == 0) and (len(song_name) == 0)):
            displayName = "UNKNOWN"
        elif (len(song_artist) > 0):
            displayName += song_artist
            if (len(song_name) > 0):
                displayName += " - " + song_name
        else:
            displayName += song_name

        return displayName

    def getInfoLabels(self, entry):
        song = entry.get
        infoLabels = {
            'tracknumber': song("track"),
            'duration': song("durationMillis") / 1000,
            'year': song("year"),
            'genre': song("genre").encode('utf-8'),
            'album': song("album").encode('utf-8'),
            'artist': song("artist").encode('utf-8'),
            'title': song("title").encode('utf-8'),
            'playcount': song("playCount")
        }
        return infoLabels

    def clearCache(self):
        self.settings.setSetting('logged_in', "")
        self.cache.delete("%")
