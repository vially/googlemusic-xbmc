import os, sys, urllib, xbmc
import GoogleMusicApi

class GoogleMusicNavigation():
    def __init__(self):
        self.main = sys.modules["__main__"]
        self.xbmcgui = self.main.xbmcgui
        self.xbmcplugin = self.main.xbmcplugin

        self.language = self.main.settings.getLocalizedString
        self.icon = self.main.settings.getAddonInfo('icon')
        self.api = GoogleMusicApi.GoogleMusicApi()

        self.main_menu = (
            {'title':"I'm feeling lucky mix", 'params':{'path':"ifl"}},
            {'title':self.language(30209), 'params':{'path':"library"}},
            {'title':self.language(30204), 'params':{'path':"playlists", 'playlist_type':"auto"}},
            {'title':self.language(30202), 'params':{'path':"playlists", 'playlist_type':"user"}},
            {'title':self.language(30208), 'params':{'path':"search"}}
        )
        self.lib_menu = (
            {'title':self.language(30210), 'params':{'path':"playlist", 'playlist_id':"feellucky"}},
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
            if self.api.getDevice():
                listItems.insert(1,self.addFolderListItem(self.language(30203),{'path':"playlists",'playlist_type':"radio"}))
        elif self.path == "ifl":
            listItems = self.getStationTracks("IFL")
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
            listItems = self.listFilterSongs(self.path,get('name'),get('artist'))
        elif self.path == "search":
            import CommonFunctions as common
            query = common.getUserInput(self.language(30208), '')
            if query:
                listItems = self.getSearch(query)
            else:
                self.main.log("No query specified. Showing main menu")
                listItems = self.getMenuItems(self.main_menu)
                updateListing = True
        elif self.path == "search_result":
            listItems = self.getSearch(get('query'),True)
        else:
            self.main.log("Invalid path: " + get("path"))

        self.xbmcplugin.addDirectoryItems(int(sys.argv[1]), listItems)
        self.xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True, updateListing=updateListing)

    def getMenuItems(self, items):
        ''' Build the plugin root menu. '''
        menuItems = []
        for menu_item in items:
            params = menu_item['params']
            cm = []
            if 'playlist_id' in params:
                cm = self.getPlayAllContextMenuItems(menu_item['title'], params['playlist_id'])
            elif 'playlist_type' in params:
                cm = self.getPlaylistsContextMenuItems(menu_item['title'], params['playlist_type'])
            elif params['path'] == 'library':
                cm.append(('Update Library', "XBMC.RunPlugin(%s?action=update_library)" % sys.argv[0]))
                cm.append(('Add to favourites', "XBMC.RunPlugin(%s?action=add_favourite&path=library&title=%s)" % (sys.argv[0],menu_item['title'])))
            elif 'criteria' in params:
                cm.append(('Add to favourites', "XBMC.RunPlugin(%s?action=add_favourite&path=filter&criteria=%s&title=%s)" % (sys.argv[0],params['criteria'],menu_item['title'])))
            menuItems.append(self.addFolderListItem(menu_item['title'], params, cm))
        return menuItems

    def executeAction(self, params):
        action = params.pop("action")
        if (action == "play_all"):
            self.playAll(params)
        elif (action == "update_playlist"):
            self.api.getPlaylistSongs(params["playlist_id"], True)
        elif (action == "update_playlists"):
            self.api.getPlaylistsByType(params["playlist_type"], True)
        elif (action == "clear_cache"):
            self.api.clearCache()
        elif (action == "clear_cookie"):
            self.api.clearCookie()
        elif (action == "add_favourite"):
            self.addFavourite(params.pop("title"),params)
        elif (action == "update_library"):
            self.api.clearCache()
            xbmc.executebuiltin("XBMC.RunPlugin(%s)" % sys.argv[0])
        else:
            self.main.log("Invalid action: " + action)

    def addFolderListItem(self, name, params, contextMenu=[], album_art_url=''):
        li = self.xbmcgui.ListItem(label=name, iconImage=album_art_url, thumbnailImage=album_art_url)
        li.addContextMenuItems(contextMenu, replaceItems=True)
        url = "?".join([sys.argv[0],urllib.urlencode(params)])
        return url, li, "true"

    def listPlaylistSongs(self, playlist_id):
        self.main.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        return self.addSongsFromLibrary(songs)

    def addSongsFromLibrary(self, library):
        listItems = []
        append = listItems.append
        createItem = self.createItem
        url = sys.argv[0]+'?action=play_song&song_id=%s&title=%s&artist=%s'
        # add album name when showing all artist songs
        if self.path == 'artist_allsongs':
            for song in library:
                songItem = createItem(song)
                songItem.setLabel("".join(['[',song[7],'] ',song[8]]))
                append([url % (song[0], song[8], song[18]), songItem])
        else:
            for song in library:
                append([url % (song[0], song[8], song[18]), createItem(song)])
        return listItems

    def getPlaylists(self, playlist_type):
        self.main.log("Getting playlists of type: " + playlist_type)
        if playlist_type == 'radio':
            return self.getStations()
        playlists = self.api.getPlaylistsByType(playlist_type)
        return self.addPlaylistsItems(playlists)

    def listFilterSongs(self, filter_type, filter_criteria, artist=''):
        if filter_criteria:
            filter_criteria = urllib.unquote_plus(filter_criteria)
        if artist:
            artist = urllib.unquote_plus(artist)
        songs = self.api.getFilterSongs(filter_type, filter_criteria, artist)
        return self.addSongsFromLibrary(songs)

    def getCriteria(self, criteria, artist=''):
        listItems = []
        append = listItems.append
        addFolder = self.addFolderListItem
        getCm = self.getFilterContextMenuItems
        #self.main.log("CRITERIA: "+criteria+" "+artist)
        items = self.api.getCriteria(criteria,artist)
        if criteria == 'album':
            for item in items:
                folder = addFolder('[%s] %s'%(item[0],item[1]),{'path':criteria,'name':item[1],'artist':artist},getCm(criteria,item[1]),item[-1])
                folder[1].setInfo(type='music', infoLabels={'year':item[2],'artist':artist})
                append(folder)
        else:
            for item in items:
                append( addFolder(item[0], {'path':criteria,'name':item[0],'artist':artist}, getCm(criteria,item[0]), self.icon))
        return listItems

    def addPlaylistsItems(self, playlists):
        listItems = []
        for playlist_id, playlist_name in playlists:
            cm = self.getPlayAllContextMenuItems(playlist_name, playlist_id)
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

        player = xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = sys.argv[0]+"?action=play_song&song_id=%s&title=%s&artist=%s"
        for song in songs:
            playlist.add(song_url % (song[0], song[8], song[18]), self.createItem(song))

        if (get("shuffle")):
            playlist.shuffle()

        xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def createItem(self, song):
        infoLabels = {
            'tracknumber': song[11], 'duration': song[21],
            'year': song[6],         'genre': song[14],
            'album': song[7],        'artist': song[18],
            'title': song[8],        'playcount': song[15]
        }

        li = self.xbmcgui.ListItem(song[23])

        try:
            li.setThumbnailImage(song[22])
            li.setIconImage(song[22])
        except: pass
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setProperty('mimetype', 'audio/mpeg')
        li.setInfo(type='music', infoLabels=infoLabels)

        return li

    def getPlayAllContextMenuItems(self, name, playlist):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (sys.argv[0], playlist)))
        cm.append((self.language(30303), "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append(('Add to favourites', "XBMC.RunPlugin(%s?action=add_favourite&path=playlist&playlist_id=%s&title=%s)" % (sys.argv[0], playlist, name)))
        return cm

    def getFilterContextMenuItems(self, filter_type, filter_criteria):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s)" % (sys.argv[0], filter_type, filter_criteria)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s&shuffle=true)" % (sys.argv[0], filter_type, filter_criteria)))
        cm.append(('Add to favourites', "XBMC.RunPlugin(%s?action=add_favourite&path=%s&name=%s&title=%s)" % (sys.argv[0], filter_type, filter_criteria, filter_criteria)))
        return cm

    def getPlaylistsContextMenuItems(self, name, playlist_type):
        cm = []
        cm.append((self.language(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (sys.argv[0], playlist_type)))
        cm.append(('Add to favourites', "XBMC.RunPlugin(%s?action=add_favourite&path=playlists&playlist_type=%s&title=%s)" % (sys.argv[0], playlist_type, name)))
        return cm

    def getSearch(self, query, onlytracks=False):
        result = self.api.getSearch(query)
        listItems = self.addSongsFromLibrary(result['tracksLib'], 'library')
        listItems.extend(self.addSongsFromLibrary(result['tracksAA'], 'library'))

        if not onlytracks:
            for album in result['albums']:
                listItems.append(self.addFolderListItem(album[0],{'path':"search_result",'query':album[0]+' '+album[1]}))
            for artist in result['artists']:
                listItems.append(self.addFolderListItem(artist,{'path':"search_result",'query':artist}))

        return listItems

    def getStations(self):
        listItems = []
        stations = self.api.getStations()
        for rs in stations:
           listItems.append(self.addFolderListItem(rs['name'], {'path':"station",'id':rs['id']}, album_art_url=rs.get('imageUrl',self.icon)))
        return listItems

    def getStationTracks(self,station_id):
        import gmusicapi.utils.utils as utils
        listItems = []
        tracks = self.api.getStationTracks(station_id)
        for track in tracks:
            li = self.xbmcgui.ListItem(track['title'])
            li.setProperty('IsPlayable', 'true')
            li.setProperty('Music', 'true')
            url = '%s?action=play_song&song_id=%s' % (sys.argv[0],utils.id_or_nid(track).encode('utf8'))
            infos = {}
            for k,v in track.iteritems():
                if k in ('title','album','artist'):
                    url = url+'&'+unicode(k)+'='+unicode(v)
                    infos[k] = v
            li.setInfo(type='music', infoLabels=infos)
            li.setPath(url)
            listItems.append([url,li])
        return listItems

    def addFavourite(self, name, params):
        import fileinput
        path = os.path.join(xbmc.translatePath("special://masterprofile"), "favourites.xml")

        url = ''
        for k,v in params.iteritems():
            url = url+'&'+unicode(k)+'='+unicode(v)

        fav = '\t<favourite name="%s" thumb="%s">ActivateWindow(10501,&quot;%s?%s&quot;,return)</favourite>'
        fav = fav % (name, xbmc.translatePath(self.icon), sys.argv[0], url[1:])

        for line in fileinput.input(path, inplace=1):
            if line.startswith('</favourites>'):
                print fav
            print line,
