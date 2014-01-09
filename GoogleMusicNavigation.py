import os
import sys
import urllib
import CommonFunctions as common
import GoogleMusicApi
from gmusicapi.utils.utils import id_or_nid

class GoogleMusicNavigation():
    def __init__(self):
        self.main = sys.modules["__main__"]
        self.xbmc = self.main.xbmc
        self.xbmcgui = self.main.xbmcgui
        self.xbmcplugin = self.main.xbmcplugin

        self.language = self.main.settings.getLocalizedString

        self.api = GoogleMusicApi.GoogleMusicApi()
        self.song = self.main.song

        self.main_menu = (
            {'title':self.language(30209), 'params':{'path':"library"}},
            {'title':self.language(30204), 'params':{'path':"playlists", 'playlist_type':"auto"}},
            {'title':self.language(30202), 'params':{'path':"playlists", 'playlist_type':"user"}},
            {'title':self.language(30208), 'params':{'path':"search"}}
        )
        self.lib_menu = (
            {'title':self.language(30201), 'params':{'path':"playlist", 'playlist_id':"all_songs"}},
            {'title':self.language(30205), 'params':{'path':"filter", 'criteria':"artist"}},
            {'title':self.language(30206), 'params':{'path':"filter", 'criteria':"album"}},
            {'title':self.language(30207), 'params':{'path':"filter", 'criteria':"genre"}},
        )
        
    def listMenu(self, params={}):
        get = params.get
        self.path = get("path", "root")

        listItems = []
        updateListing = False

        if self.path == "root":
            listItems = self.getMenuItems(self.main_menu)
            if self.api.login.getDevice():
                listItems.insert(1,self.addFolderListItem(self.language(30203),{'path':"playlists",'playlist_type':"radio"}))
        elif self.path == "library":
            listItems = self.getMenuItems(self.lib_menu)
        elif self.path == "playlist":
            listItems = self.listPlaylistSongs(get("playlist_id"))
        elif self.path == "station":
            listItems = self.getStationTracks(get('id'))
        elif self.path == "playlists":
            listItems = self.getPlaylists(get('playlist_type'))
        elif self.path == "filter":
            listItems = self.getCriteria(get('criteria'))
        elif self.path == "artist":
            albumName = urllib.unquote_plus(get('name'))
            listItems = self.getCriteria("album",albumName)
            listItems.insert(0,self.addFolderListItem(self.language(30201),{'path':"artist_allsongs", 'name':albumName}))
        elif self.path == "artist_allsongs":
            listItems = self.listFilterSongs("artist",get('name'))
        elif self.path in ["genre","artist","album"]:
            listItems = self.listFilterSongs(self.path,get('name'))
        elif self.path == "search":
            query = common.getUserInput(self.language(30208), '')
            if query:
                listItems = self.getSearch(query)
            else:
                self.main.log("No query specified. Showing main menu")
                listItems = self.getMenuItems(self.main_menu)
                updateListing = True
        else:
            self.main.log("Invalid path: " + get("path"))

        self.xbmcplugin.addDirectoryItems(int(sys.argv[1]), listItems)
        self.xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True, updateListing=updateListing)

    def getMenuItems(self,items):
        ''' Build the plugin root menu. '''
        menuItems = []
        for menu_item in items:
            params = menu_item['params']
            cm = []
            if 'playlist_id' in params:
                cm = self.getPlayAllContextMenuItems(params['playlist_id'])
            elif 'playlist_type' in params:
                cm = self.getPlaylistsContextMenuItems(params['playlist_type'])
            menuItems.append(self.addFolderListItem(menu_item['title'], params, cm))
        return menuItems

    def executeAction(self, params={}):
        get = params.get
        if (get("action") == "play_all"):
            self.playAll(params)
        elif (get("action") == "play_song"):
            self.song.play(get("song_id"))
        elif (get("action") == "update_playlist"):
            self.api.getPlaylistSongs(params["playlist_id"], True)
        elif (get("action") == "update_playlists"):
            self.api.getPlaylistsByType(params["playlist_type"], True)
        elif (get("action") == "clear_cache"):
            self.api.clearCache()
        elif (get("action") == "clear_cookie"):
            self.api.clearCookie()
        else:
            self.main.log("Invalid action: " + get("action"))

    def addFolderListItem(self, name, params={}, contextMenu=[], album_art_url=""):
        if not name:
            name = 'Unknown'
        li = self.xbmcgui.ListItem(label=name, iconImage=album_art_url, thumbnailImage=album_art_url)
        li.setProperty("Folder", "true")

        url = sys.argv[0] + '?' + urllib.urlencode(params)

        if len(contextMenu) > 0:
            li.addContextMenuItems(contextMenu, replaceItems=True)

        return url, li, "true"

    def addSongItem(self, song):
        if self.path == 'artist_allsongs' and song[7]:
            # add album name when showing all artist songs
            li = self.song.createItem(song, ('['+song[7]+'] '+song[8]))
        else:
            li = self.song.createItem(song)

        url = '%s?action=play_song&song_id=%s' % (sys.argv[0], song[0])
        return url,li

    def listPlaylistSongs(self, playlist_id):
        self.main.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        return self.addSongsFromLibrary(songs)

    def addSongsFromLibrary(self, library):
        listItems = []
        for song in library:
            listItems.append(self.addSongItem(song))
        return listItems

    def getPlaylists(self, playlist_type):
        self.main.log("Getting playlists of type: " + playlist_type)
        if playlist_type == 'radio':
            return self.getStations()
        playlists = self.api.getPlaylistsByType(playlist_type)
        return self.addPlaylistsItems(playlists)

    def listFilterSongs(self, filter_type, filter_criteria):
        if filter_criteria:
            filter_criteria = urllib.unquote_plus(filter_criteria)
        songs = self.api.getFilterSongs(filter_type, filter_criteria)
        return self.addSongsFromLibrary(songs)

    def getCriteria(self, criteria, artist=''):
        listItems = []
        genres = self.api.getCriteria(criteria,artist)
        for genre in genres:
            if len(genre)>1:
                art = genre[1]
            else:
                art = self.main.__icon__
            cm = self.getFilterContextMenuItems(criteria,genre[0])
            listItems.append(self.addFolderListItem(genre[0], {'path':criteria, 'name':genre[0]}, cm, art))
        return listItems

    def addPlaylistsItems(self, playlists):
        listItems = []
        for playlist_id, playlist_name in playlists:
            cm = self.getPlayAllContextMenuItems(playlist_id)
            listItems.append(self.addFolderListItem(playlist_name, {'path':"playlist", 'playlist_id':playlist_id}, cm))
        return listItems

    def playAll(self, params={}):
        get = params.get

        playlist_id = get('playlist_id')
        if playlist_id:
            self.main.log("Loading playlist: " + playlist_id)
            songs = self.api.getPlaylistSongs(playlist_id)
        else:
            songs = self.api.getFilterSongs(get('filter_type'), get('filter_criteria'))

        player = self.xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = self.xbmc.PlayList(self.xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = "%s?action=play_song&song_id=%s"
        for song in songs:
            playlist.add(song_url % (sys.argv[0], song[0]), self.song.createItem(song))

        if (get("shuffle")):
            playlist.shuffle()

        self.xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def getPlayAllContextMenuItems(self, playlist):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (sys.argv[0], playlist)))
        cm.append((self.language(30303), "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" % (sys.argv[0], playlist)))
        return cm

    def getFilterContextMenuItems(self, filter_type, filter_criteria):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s)" % (sys.argv[0], filter_type, filter_criteria)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s&shuffle=true)" % (sys.argv[0], filter_type, filter_criteria)))
        return cm

    def getPlaylistsContextMenuItems(self, playlist_type):
        cm = []
        cm.append((self.language(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (sys.argv[0], playlist_type)))
        return cm

    def getSearch(self, query):
        return self.addSongsFromLibrary(self.api.getSearch(query))

    def getStations(self):
        listItems = []
        stations = self.api.getStations()
        #stations = [{'name':'Teste','id':'1287yed82d'}]
        for rs in stations:
           listItems.append(self.addFolderListItem(rs['name'], {'path':"station",'id':rs['id']}))
        return listItems

    def getStationTracks(self,station_id):
        listItems = []
        tracks = self.api.getStationTracks(station_id)
        #tracks = [{'title':'Teste1','id':'f5d1db5a-77d6-3b89-993b-b6ee45b3abce'},{'title':'Teste2','id':'kf7fi765'}]
        for track in tracks:
            li = self.xbmcgui.ListItem(track['title'])
            li.setProperty('IsPlayable', 'true')
            li.setProperty('Music', 'true')
            url = '%s?action=play_song&song_id=%s&title=%s' % (sys.argv[0],id_or_nid(track).encode('utf8'),track['title'].encode('utf8'))
            li.setPath(url)
            listItems.append([url,li])
        return listItems
