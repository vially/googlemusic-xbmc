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
            {'title':'Composers', 'params':{'path':"filter", 'criteria':"composer"}},
        )

    def listMenu(self, params={}):
        get = params.get
        self.path = get("path", "root")

        listItems = []
        updateListing = False
        view_mode_id = 0
        content = ''
        handle1 = int(sys.argv[1])

        if self.path == "root":
            listItems = self.getMenuItems(self.main_menu)
            if self.api.getDevice():
                listItems.insert(1,self.addFolderListItem(self.language(30203),{'path':"playlists",'playlist_type':"radio"}))
        elif self.path == "ifl":
            listItems = self.getStationTracks("IFL")
            content = "songs"
        elif self.path == "library":
            listItems = self.getMenuItems(self.lib_menu)
        elif self.path == "playlist":
            listItems = self.listPlaylistSongs(get("playlist_id"))
            content = "songs"
        elif self.path == "station":
            listItems = self.getStationTracks(get('id'))
            content = "songs"
        elif self.path == "playlists":
            listItems = self.getPlaylists(get('playlist_type'))
        elif self.path == "filter":
            listItems = self.getCriteria(get('criteria'))
            view_mode_id = 500
        elif self.path in ["artist", "genre"] and get('albums'):
            albums = urllib.unquote_plus(get('albums'))
            listItems = self.getCriteria(self.path, albums)
            listItems.insert(0,self.addFolderListItem('* '+self.language(30201),{'path':"allsongs",'criteria':self.path,'albums':albums}))
            content = "albums"
            view_mode_id = 500
        elif self.path == "allsongs":
            listItems = self.listFilterSongs(get('criteria'), get('albums'))
            self.xbmcplugin.addSortMethod(handle1, self.xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE, "%A")
            content = "songs"
        elif self.path in ["genre", "artist", "album", "composer"]:
            listItems = self.listFilterSongs(self.path, get('album'), get('artist'))
            content = "songs"
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
            self.main.log("SEARCH_RESULT: "+get('query'))
            listItems = self.getSearch(params, True)
            content = "songs"
        else:
            self.main.log("Invalid path: " + get("path"))
            return

        self.xbmcplugin.addDirectoryItems(handle1, listItems)

        self.xbmcplugin.addSortMethod(handle1, self.xbmcplugin.SORT_METHOD_UNSORTED)
        if content in ["songs","albums"]:
            self.xbmcplugin.setContent(handle1, content)
            self.xbmcplugin.addSortMethod(handle1, self.xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
            self.xbmcplugin.addSortMethod(handle1, self.xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE, "%A")
            self.xbmcplugin.addSortMethod(handle1, self.xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE)
            self.xbmcplugin.addSortMethod(handle1, self.xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            if content == "songs":
                self.xbmcplugin.addSortMethod(handle1, self.xbmcplugin.SORT_METHOD_TRACKNUM)

        if view_mode_id > 0 and self.main.settings.getSetting('overrideview') == "true":
            xbmc.executebuiltin('Container.SetViewMode(%d)' % view_mode_id)

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
                cm.append((self.language(30305), "XBMC.RunPlugin(%s?action=update_library)" % sys.argv[0]))
                cm.append((self.language(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=library&title=%s)" % (sys.argv[0],menu_item['title'])))
            elif 'criteria' in params:
                cm.append((self.language(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=filter&criteria=%s&title=%s)" % (sys.argv[0],params['criteria'],menu_item['title'])))
            menuItems.append(self.addFolderListItem(menu_item['title'], params, cm))
        return menuItems

    def executeAction(self, action, params):
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
        elif (action == "add_library"):
            self.api.addAAtrack(params["song_id"])
            xbmc.executebuiltin("XBMC.Notification("+self.main.plugin+",'Library update needed',5000,"+self.icon+")")
        elif (action == "add_playlist"):
            self.addToPlaylist(params["song_id"])
        elif (action == "del_from_playlist"):
            self.api.delFromPlaylist(params["playlist_id"], params["song_id"])
        elif (action == "update_library"):
            self.api.clearCache()
            xbmc.executebuiltin("XBMC.RunPlugin(%s)" % sys.argv[0])
        else:
            self.main.log("Invalid action: " + action)

    def addFolderListItem(self, name, params, contextMenu=[], album_art_url='', name2='*'):
        li = self.xbmcgui.ListItem(label=name, label2=name2, iconImage=album_art_url, thumbnailImage=album_art_url)
        li.addContextMenuItems(contextMenu, replaceItems=True)
        url = "?".join([sys.argv[0],urllib.urlencode(params)])
        return url, li, "true"

    def listPlaylistSongs(self, playlist_id):
        self.main.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        if playlist_id in ('thumbsup','lastadded','mostplayed','freepurchased','feellucky','all_songs'):
            return self.addSongsFromLibrary(songs, 'library')
        return self.addSongsFromLibrary(songs, 'playlist'+playlist_id)

    def addSongsFromLibrary(self, library, song_type):
        listItems = []
        append = listItems.append
        createItem = self.createItem
        url = sys.argv[0]+'?action=play_song&song_id=%s&title=%s&artist=%s&albumart=%s'
        # add album name when showing all artist songs
        if self.path == 'allsongs':
            for song in library:
                songItem = createItem(song, song_type)
                songItem.setLabel("".join(['[',song[7],'] ',song[8]]))
                songItem.setLabel2(song[7])
                append([url % (song[0], song[8], song[18], song[22]), songItem])
        else:
            for song in library:
                #self.main.log("ITEM URL: "+url % (song[0], song[8], song[18], song[22]))
                append([url % (song[0], song[8], song[18], song[22]), createItem(song, song_type)])
        return listItems

    def getPlaylists(self, playlist_type):
        self.main.log("Getting playlists of type: " + playlist_type)
        if playlist_type == 'radio':
            return self.getStations()
        playlists = self.api.getPlaylistsByType(playlist_type)
        return self.addPlaylistsItems(playlists)

    def listFilterSongs(self, filter_type, filter_criteria, albums=''):
        #self.main.log("FILTER: "+repr(filter_type)+" "+repr(filter_criteria)+" "+repr(albums))
        if albums: albums = urllib.unquote_plus(albums)
        if filter_criteria: filter_criteria = urllib.unquote_plus(filter_criteria)
        songs = self.api.getFilterSongs(filter_type, filter_criteria, albums )
        return self.addSongsFromLibrary(songs, 'library')

    def getCriteria(self, criteria, albums=''):
        self.main.log("CRITERIA: "+repr(criteria)+" "+repr(albums))
        listItems = []
        append = listItems.append
        addFolder = self.addFolderListItem
        getCm = self.getFilterContextMenuItems
        items = self.api.getCriteria(criteria, albums)
        #print repr(items)
        if criteria == 'album' or (albums and criteria in ('genre','artist','composer')):
            for item in items:
                folder = addFolder('[%s] %s'%(item[0],item[1]),{'path':criteria,'album':item[1],'artist':item[0]},getCm(criteria,item[1]),item[-1])
                #folder = addFolder(item[1],{'path':criteria,'album':item[1],'artist':item[0]},getCm(criteria,item[1]),item[-1],item[0])
                folder[1].setInfo(type='music', infoLabels={'year':item[2],'artist':item[0],'album':item[1]})
                append(folder)
        elif criteria == 'artist':
            for item in items:
                append( addFolder(item[0], {'path':criteria,'albums':item[0]}, getCm(criteria,item[0]), item[1]))
        else:
            for item in items:
                append( addFolder(item[0], {'path':criteria,'album':item[0]}, getCm(criteria,item[0])))
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
        elif get('album_id'):
            self.main.log("Loading album: " + get('album_id'))
            songs = self.api.getAlbum(get('album_id'))
        elif get('share_token'):
            self.main.log("Loading shared playlist: " + get('share_token'))
            songs = self.api.getSharedPlaylist(urllib.unquote_plus(get('share_token')))
        elif get('artist_id'):
            self.main.log("Loading artist top tracks: " + get('artist_id'))
            songs = self.api.getArtist(get('artist_id'))
        else:
            songs = self.api.getFilterSongs(get('filter_type'), get('filter_criteria'), albums='')

        player = xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = sys.argv[0]+"?action=play_song&song_id=%s&title=%s&artist=%s&albumart=%s"
        for song in songs:
            playlist.add(song_url % (song[0], song[8], song[18], song[22]), self.createItem(song, ''))

        if (get("shuffle")):
            playlist.shuffle()

        xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def createItem(self, song, song_type):
        infoLabels = {
            'tracknumber': song[11], 'duration': song[21],
            'year': song[6],         'genre': song[14],
            'album': song[7],        'artist': song[18],
            'title': song[8],        'playcount': song[15],
            'rating': song[2]
        }

        li = self.xbmcgui.ListItem(song[23])
        li.addContextMenuItems(self.getSongContextMenu(song[0], song_type))

        try:
            li.setThumbnailImage(song[22])
            li.setIconImage(song[22])
        except: pass
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setProperty('mimetype', 'audio/mpeg')
        li.setInfo(type='music', infoLabels=infoLabels)

        return li

    def getSongContextMenu(self, song_id, song_type):
        cm = []
        if song_type == 'library':
            cm.append(("Add to playlist","XBMC.RunPlugin(%s?action=add_playlist&song_id=%s)" % (sys.argv[0],song_id)))
        elif song_type.startswith('playlist'):
            cm.append(("Remove from playlist", "XBMC.RunPlugin(%s?action=del_from_playlist&song_id=%s&playlist_id=%s)" % (sys.argv[0], song_id, song_type[8:])))
        if song_id.startswith('T'):
            cm.append(("Add to library", "XBMC.RunPlugin(%s?action=add_library&song_id=%s)" % (sys.argv[0],song_id)))
        return cm

    def getPlayAllContextMenuItems(self, name, playlist):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (sys.argv[0], playlist)))
        cm.append((self.language(30303), "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append((self.language(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlist&playlist_id=%s&title=%s)" % (sys.argv[0], playlist, name)))
        return cm

    def getFilterContextMenuItems(self, filter_type, filter_criteria):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s)" % (sys.argv[0], filter_type, filter_criteria)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s&shuffle=true)" % (sys.argv[0], filter_type, filter_criteria)))
        cm.append((self.language(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=%s&name=%s&title=%s)" % (sys.argv[0], filter_type, filter_criteria, filter_criteria)))
        return cm

    def getPlaylistsContextMenuItems(self, name, playlist_type):
        cm = []
        cm.append((self.language(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (sys.argv[0], playlist_type)))
        cm.append((self.language(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlists&playlist_type=%s&title=%s)" % (sys.argv[0], playlist_type, name)))
        return cm

    def getSearch(self, query, onlytracks=False):
        listItems = []

        if not onlytracks:
            result = self.api.getSearch(query)
            if result['albums']:
                listItems.append(self.addFolderListItem('[COLOR orange]*** '+self.language(30206)+' ***[/COLOR]',{'path':'none'}))
                cm = []
                for album in result['albums']:
                    params = {'path':"search_result",'query':self.tryEncode(album[0])}
                    if len(album) > 3:
                        cm = [(self.language(30301), "XBMC.RunPlugin(%s?action=play_all&album_id=%s)" % (sys.argv[0], album[3]))]
                        params['albumid'] = album[3]
                    listItems.append(self.addFolderListItem("[%s] %s"%(album[1],album[0]),params,cm,album_art_url=album[2]))
            if result['artists']:
                listItems.append(self.addFolderListItem('[COLOR orange]*** '+self.language(30205)+' ***[/COLOR]',{'path':'none'}))
                cm = []
                for artist in result['artists']:
                    params = {'path':"search_result",'query':self.tryEncode(artist[0])}
                    if len(artist) > 2:
                        cm = [(self.language(30301), "XBMC.RunPlugin(%s?action=play_all&artist_id=%s)" % (sys.argv[0], artist[2]))]
                        params['artistid'] = artist[2]
                    listItems.append(self.addFolderListItem(artist[0],params,cm,album_art_url=artist[1]))
            if result['tracks']:
                listItems.append(self.addFolderListItem('[COLOR orange]*** Songs ***[/COLOR]',{'path':'none'}))
                listItems.extend(self.addSongsFromLibrary(result['tracks'], 'library'))
        elif 'albumid' in query:
            listItems.extend(self.addSongsFromLibrary(self.api.getAlbum(query['albumid']), 'library'))
        elif 'artistid' in query:
            listItems.extend(self.addSongsFromLibrary(self.api.getArtist(query['artistid']), 'library'))
        else:
            result = self.api.getSearch(urllib.unquote_plus(query['query']))
            url = sys.argv[0]+'?action=play_song&song_id=%s&title=%s&artist=%s&albumart=%s'
            for item in result['tracks']:
                listItems.append([url % (item[0], item[8], item[18], item[22]), self.createItem(item, 'library')])

        return listItems

    def getStations(self):
        listItems = []
        stations = self.api.getStations()
        for rs in stations:
            listItems.append(self.addFolderListItem(rs['name'], {'path':"station",'id':rs['id']}, album_art_url=rs.get('imageUrl',self.icon)))
        return listItems

    def getStationTracks(self,station_id):
        return self.addSongsFromLibrary(self.api.getStationTracks(station_id), 'library')

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

    def addToPlaylist (self, song_id):
        list = []
        playlists = self.api.getPlaylistsByType('user')
        for playlist_id, playlist_name in playlists:
            list.append(playlist_name)
        dialog = self.xbmcgui.Dialog()
        selected = dialog.select('Add to Playlist..', list)
        if selected > 0:
            playlist_id = playlists[selected][0]
            self.main.log(repr(playlist_id))
            self.api.addToPlaylist(playlist_id, song_id)

    def tryEncode(self, text, encoding='utf8'):
        #for encoding in ('utf8','windows-1252','iso-8859-15','iso-8859-1'):
        try:
            #print encoding
            return text.encode(encoding)
        except:
            self.main.log(" ENCODING FAIL!!!@ "+encoding)
        return repr(text)
