import os
import sys
import urllib
import GoogleMusicApi

class GoogleMusicNavigation():
    def __init__(self):
        self.xbmc = sys.modules["__main__"].xbmc
        self.xbmcgui = sys.modules["__main__"].xbmcgui
        self.xbmcplugin = sys.modules["__main__"].xbmcplugin
        self.xbmcvfs = sys.modules["__main__"].xbmcvfs

        self.settings = sys.modules["__main__"].settings
        self.language = sys.modules["__main__"].language
        self.dbg = sys.modules["__main__"].dbg
        self.common = sys.modules["__main__"].common

        self.api = GoogleMusicApi.GoogleMusicApi()

        self.main_menu = (
            {'title':self.language(30201), 'params':{'path':"playlist", 'playlist_id':"all_songs"}},
            {'title':self.language(30202), 'params':{'path':"playlists", 'playlist_type':"user"}},
            {'title':self.language(30204), 'params':{'path':"playlists", 'playlist_type':"auto"}},
            {'title':self.language(30205), 'params':{'path':"filter", 'criteria':"artist"}},
            {'title':self.language(30206), 'params':{'path':"filter", 'criteria':"album"}},
            {'title':self.language(30207), 'params':{'path':"filter", 'criteria':"genre"}}        )

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
                else:
                    cm = self.getPlaylistsContextMenuItems(params['playlist_type'])
                self.addFolderListItem(menu_item['title'], params, cm)
        elif path == "playlist":
            self.listPlaylistSongs(get("playlist_id"))
        elif path == "playlists":
            playlist_type = get('playlist_type')
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
            self.playAll(params)
        elif (get("action") == "play_song"):
            self.playSong(params)
        elif (get("action") == "update_playlist"):
            self.api.getPlaylistSongs(params["playlist_id"], True)
        elif (get("action") == "update_playlists"):
            self.api.getPlaylistsByType(params["playlist_type"], True)
        elif (get("action") == "clear_cache"):
            self.clearCache()
        elif (get("action") == "clear_cookie"):
            self.clearCookie()
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
        li = self.xbmcgui.ListItem(song[23])
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setInfo(type='music', infoLabels=self.getInfoLabels(song))

        return li

    def addSongItem(self, song):
        song_id = song[0].encode('utf-8')

        li = self.createSongListItem(song)

        url = '%s?action=play_song&song_id=%s' % (sys.argv[0], song_id)
        return self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li)

    def listPlaylistSongs(self, playlist_id):
        self.common.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        self.addSongsFromLibrary(songs)

    def addSongsFromLibrary(self, library):
        for song in library:
            self.addSongItem(song)

    def getPlaylists(self, playlist_type):
        self.common.log("Getting playlists of type: " + playlist_type)
        playlists = self.api.getPlaylistsByType(playlist_type)
        self.common.log(str(playlists))
        self.addPlaylistsItems(playlists)
        
    def listFilterSongs(self, filter_type, filter_criteria):
        songs = self.api.getFilterSongs(filter_type, urllib.unquote_plus(filter_criteria))
        self.common.log(str(songs))
        self.addSongsFromLibrary(songs)

    def getCriteria(self, criteria):
        genres = self.api.getCriteria(criteria)
        for genre in genres:
            cm = []
            self.addFolderListItem(genre[0], {'path':criteria, 'name':genre[0].encode('utf8')}, cm)
        self.common.log(str(genres))

    def addPlaylistsItems(self, playlists):
        for playlist_id, playlist_name, playlist_type, fetched in playlists:
            cm = self.getPlayAllContextMenuItems(playlist_id)
            self.addFolderListItem(playlist_name, {'path':"playlist", 'playlist_id':playlist_id}, cm)

    def playAll(self, params={}):
        get = params.get

        playlist_id = get('playlist_id')
        self.common.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)

        player = self.xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = self.xbmc.PlayList(self.xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = "%s?action=play_song&song_id=%s&playlist_id=" + playlist_id
        for song in songs:
            song_id = song[0].encode('utf-8')

            li = self.createSongListItem(song)
            playlist.add(song_url % (sys.argv[0], song_id), li)

        if (get("shuffle")):
            playlist.shuffle()

        self.xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def playSong(self, params={}):
        get = params.get
        song = self.api.getSong(get("song_id"))
        url = self.api.getSongStreamUrl(get("song_id"))

        li = self.createSongListItem(song)
        li.setPath(url)

        self.xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

    def getPlayAllContextMenuItems(self, playlist):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (sys.argv[0], playlist)))
        cm.append((self.language(30303), "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" % (sys.argv[0], playlist)))
        return cm

    def getPlaylistsContextMenuItems(self, playlist_type):
        cm = []
        cm.append((self.language(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (sys.argv[0], playlist_type)))
        return cm

    def getInfoLabels(self, song):
        infoLabels = {
            'tracknumber': song[11],
            'duration': song[21] / 1000,
            'year': song[6],
            'genre': song[14].encode('utf-8'),
            'album': song[7].encode('utf-8'),
            'artist': song[18].encode('utf-8'),
            'title': song[8].encode('utf-8'),
            'playcount': song[15]
        }
        return infoLabels

    def clearCache(self):
        sqlite_db = os.path.join(self.xbmc.translatePath("special://database"), self.settings.getSetting('sqlite_db'))
        if self.xbmcvfs.exists(sqlite_db):
            self.xbmcvfs.delete(sqlite_db)

        self.settings.setSetting("fetched_all_songs", "")
        self.settings.setSetting('firstrun', "")

        self.clearCookie()

    def clearCookie(self):
        cookie_file = os.path.join(self.settings.getAddonInfo('path'), self.settings.getSetting('cookie_file'))
        if self.xbmcvfs.exists(cookie_file):
            self.xbmcvfs.delete(cookie_file)

        self.settings.setSetting('logged_in', "")
