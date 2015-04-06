import xbmc, xbmcplugin, utils
import GoogleMusicApi
import time
from urllib import unquote_plus, urlencode
from xbmcgui import ListItem

class GoogleMusicNavigation():
    def __init__(self):
        self.lang    = utils.addon.getLocalizedString
        self.fanart  = utils.addon.getAddonInfo('fanart')
        self.api     = GoogleMusicApi.GoogleMusicApi()

        self.song_url  = utils.addon_url+"?action=play_song&song_id=%s&title=%s&artist=%s&albumart=%s"

        self.main_menu = (
            {'title':self.lang(30211), 'params':{'path':"ifl"}},
            {'title':self.lang(30209), 'params':{'path':"library"}},
            {'title':self.lang(30204), 'params':{'path':"playlists", 'playlist_type':"auto"}},
            {'title':self.lang(30202), 'params':{'path':"playlists", 'playlist_type':"user"}},
            {'title':self.lang(30208), 'params':{'path':"search"}}
        )
        self.lib_menu = (
            {'title':self.lang(30210), 'params':{'path':"playlist", 'playlist_id':"feellucky"}},
            {'title':self.lang(30201), 'params':{'path':"playlist", 'playlist_id':"all_songs"}},
            {'title':self.lang(30205), 'params':{'path':"filter", 'criteria':"artist"}},
            {'title':self.lang(30206), 'params':{'path':"filter", 'criteria':"album"}},
            {'title':self.lang(30207), 'params':{'path':"filter", 'criteria':"genre"}},
            {'title':self.lang(30212), 'params':{'path':"filter", 'criteria':"composer"}},
        )

    def listMenu(self, params={}):
        get = params.get
        self.path = get("path", "root")

        listItems = []
        view_mode_id = 0
        content = ''
        sortMethods = [xbmcplugin.SORT_METHOD_UNSORTED]

        if self.path == "root":
            listItems = self.getMenuItems(self.main_menu)
            if self.api.getDevice():
                listItems.insert(1,self.createFolder(self.lang(30203),{'path':"playlists",'playlist_type':"radio"}))
        elif self.path == "ifl":
            listItems = self.addSongsFromLibrary(self.api.getStationTracks("IFL"), 'library')
            content = "songs"
        elif self.path == "library":
            listItems = self.getMenuItems(self.lib_menu)
        elif self.path == "playlist":
            listItems = self.listPlaylistSongs(get("playlist_id"))
            if get("playlist_id")=='all_songs':
                sortMethods = [xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]
            content = "songs"
        elif self.path == "station":
            listItems = self.addSongsFromLibrary(self.api.getStationTracks(get('id')), 'library')
            content = "songs"
        elif self.path == "playlists":
            listItems = self.getPlaylists(get('playlist_type'))
        elif self.path == "filter":
            listItems = self.getCriteria(get('criteria'))
            sortMethods = [xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]
            if ('album' == get('criteria')):
                sortMethods = [xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE, xbmcplugin.SORT_METHOD_VIDEO_YEAR, 
                               xbmcplugin.SORT_METHOD_ARTIST, xbmcplugin.SORT_METHOD_ALBUM,
                               xbmcplugin.SORT_METHOD_DATE]
            view_mode_id = 500
        elif self.path in ["artist", "genre"] and get('albums'):
            albums = unquote_plus(get('albums'))
            listItems = self.getCriteria(self.path, albums)
            listItems.insert(0,self.createFolder('* '+self.lang(30201),{'path':"allsongs",'criteria':self.path,'albums':albums}))
            sortMethods = [xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE, xbmcplugin.SORT_METHOD_VIDEO_YEAR, 
                           xbmcplugin.SORT_METHOD_ARTIST, xbmcplugin.SORT_METHOD_ALBUM,
                           xbmcplugin.SORT_METHOD_DATE]
            content = "albums"
            view_mode_id = 500
        elif self.path == "allsongs":
            listItems = self.listFilterSongs(get('criteria'), get('albums'))
            sortMethods = [xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]
            content = "songs"
        elif self.path in ["genre", "artist", "album", "composer"]:
            listItems = self.listFilterSongs(self.path, get('album'), get('artist'))
            sortMethods = [xbmcplugin.SORT_METHOD_TRACKNUM,  xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,
                           xbmcplugin.SORT_METHOD_PLAYCOUNT, xbmcplugin.SORT_METHOD_SONG_RATING]
            content = "songs"
        elif self.path == "search":
            keyboard = xbmc.Keyboard('', self.lang(30208))
            keyboard.doModal()
            if keyboard.isConfirmed() and keyboard.getText():
                listItems = self.getSearch(keyboard.getText())
            else: return
            content = "songs"
        elif self.path == "search_result":
            utils.log("SEARCH_RESULT: "+get('query'))
            listItems = self.getSearch(params)
            content = "songs"
        else:
            utils.log("Invalid path: " + get("path"))
            return

        utils.setDirectory(listItems, content, sortMethods)

        if view_mode_id > 0 and utils.addon.getSetting('overrideview') == "true":
            xbmc.executebuiltin('Container.SetViewMode(%d)' % view_mode_id)

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
                cm.append((self.lang(30314), "XBMC.RunPlugin(%s?action=export_library)" % utils.addon_url))
                cm.append((self.lang(30305), "XBMC.RunPlugin(%s?action=update_library)" % utils.addon_url))
                cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=library&title=%s)" % (utils.addon_url,menu_item['title'])))
            elif 'criteria' in params:
                cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=filter&criteria=%s&title=%s)" % (utils.addon_url,params['criteria'],menu_item['title'])))
            menuItems.append(self.createFolder(menu_item['title'], params, cm))
        return menuItems

    def listPlaylistSongs(self, playlist_id):
        utils.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        if playlist_id in ('thumbsup','lastadded','mostplayed','freepurchased','feellucky','all_songs'):
            return self.addSongsFromLibrary(songs, 'library')
        return self.addSongsFromLibrary(songs, 'playlist'+playlist_id)

    def addSongsFromLibrary(self, library, song_type):
        listItems = []
        append = listItems.append
        createItem = self.createItem
        # add album name when showing all artist songs
        if self.path == 'allsongs':
            for song in library:
                songItem = createItem(song, song_type)
                songItem.setLabel("".join(['[',song[7],'] ',song[8]]))
                songItem.setLabel2(song[7])
                append([self.song_url % (song[0], song[8], song[18], song[22]), songItem])
        else:
            for song in library:
                append([self.song_url % (song[0], song[8], song[18], song[22]), createItem(song, song_type)])
        return listItems

    def getPlaylists(self, playlist_type):
        utils.log("Getting playlists of type: " + playlist_type)
        listItems = []
        append = listItems.append
        addFolder = self.createFolder
        if playlist_type == 'radio':
            icon = utils.addon.getAddonInfo('icon')
            for rs in self.api.getStations():
                cm = self.getRadioContextMenuItems(rs['name'], rs['id'])
                append(addFolder(rs['name'], {'path':"station",'id':rs['id']}, cm, album_art_url=rs.get('imageUrl', icon)))
        else:
            for pl_id, pl_name in self.api.getPlaylistsByType(playlist_type):
                cm = self.getPlayAllContextMenuItems(pl_name, pl_id)
                append(addFolder(pl_name, {'path':"playlist", 'playlist_id':pl_id}, cm))
        return listItems

    def listFilterSongs(self, filter_type, filter_criteria, albums=''):
        #utils.log("FILTER: "+repr(filter_type)+" "+repr(filter_criteria)+" "+repr(albums))
        if albums: albums = unquote_plus(albums)
        if filter_criteria: filter_criteria = unquote_plus(filter_criteria)
        songs = self.api.getFilterSongs(filter_type, filter_criteria, albums )
        return self.addSongsFromLibrary(songs, 'library')

    def getCriteria(self, criteria, albums=''):
        #utils.log("CRITERIA: "+repr(criteria)+" "+repr(albums))
        listItems = []
        append = listItems.append
        addFolder = self.createFolder
        getCm = self.getFilterContextMenuItems
        items = self.api.getCriteria(criteria, albums)
        if criteria == 'album' or (albums and criteria in ('genre','artist','composer')):
            for item in items:
                #folder = addFolder('[%s] %s'%(item[0],item[1]),{'path':criteria,'album':item[1],'artist':item[0]},getCm(criteria,item[1]),item[-1])
                folder = addFolder(item[1],{'path':criteria,'album':item[1],'artist':item[0]},getCm(criteria,item[1]),item[-1],item[0])
                folder[1].setInfo(type='music', infoLabels={'year':item[2],'artist':item[0],'album':item[1],
                    'date':time.strftime('%d.%m.%Y', time.gmtime(item[4]/1000000))})
                #utils.log("folder[1].setInfo('year':" + str(item[2]) +
                #    ",'artist':" + item[0] +
                #    ",'album':" + item[1] +
                #    ", date: " + time.strftime('%d.%m.%Y', time.gmtime(item[4]/1000000))+")")
                append(folder)
        elif criteria == 'artist':
            for item in items:
                append( addFolder(item[0], {'path':criteria,'albums':item[0]}, getCm(criteria,item[0]), item[1]))
        else:
            for item in items:
                append( addFolder(item[0], {'path':criteria,'album':item[0]}, getCm(criteria,item[0])))
        return listItems

    def createFolder(self, name, params, contextMenu=[], album_art_url='', name2='*'):
        li = ListItem(label=name, label2=name2, thumbnailImage=album_art_url)
        li.addContextMenuItems(contextMenu, replaceItems=True)
        li.setProperty('fanart_image', self.fanart)
        url = "?".join([utils.addon_url, urlencode(params)])
        return url, li, "true"

    def createItem(self, song, song_type):
        infoLabels = {
            'tracknumber': song[11], 'duration': song[21],
            'year': song[6],         'genre': song[14],
            'album': song[7],        'artist': song[18],
            'title': song[8],        'playcount': song[15],
            'rating': song[2],       'discnumber': song[4]
        }

        li = utils.createItem(song[23], song[22])
        li.setProperty('fanart_image', song[25])
        li.setInfo(type='music', infoLabels=infoLabels)
        li.addContextMenuItems(self.getSongContextMenu(song[0], song[23], song_type))
        return li

    def getSongContextMenu(self, song_id, title, song_type):
        cm = []
        if song_id.startswith('T'):
            cm.append((self.lang(30309), "XBMC.RunPlugin(%s?action=add_library&song_id=%s)" % (utils.addon_url,song_id)))
        if song_type == 'library':
            cm.append((self.lang(30307),"XBMC.RunPlugin(%s?action=add_playlist&song_id=%s)" % (utils.addon_url,song_id)))
        elif song_type.startswith('playlist'):
            cm.append((self.lang(30308), "XBMC.RunPlugin(%s?action=del_from_playlist&song_id=%s&playlist_id=%s)" % (utils.addon_url, song_id, song_type[8:])))
        cm.append((self.lang(30313), "XBMC.RunPlugin(%s?action=play_yt&title=%s)" % (utils.addon_url,title)))
        cm.append((self.lang(30311), "XBMC.RunPlugin(%s?action=search_yt&title=%s)" % (utils.addon_url,title)))
        cm.append((self.lang(30310), "XBMC.RunPlugin(%s?action=start_radio&song_id=%s)" % (utils.addon_url,song_id)))
        return cm

    def getRadioContextMenuItems(self, name, radio_id):
        cm = []
        cm.append((self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&radio_id=%s)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30302), "XBMC.RunPlugin(%s?action=play_all&radio_id=%s&shuffle=true)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30312), "XBMC.RunPlugin(%s?action=play_all_yt&radio_id=%s)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlist&radio_id=%s&title=%s)" % (utils.addon_url, radio_id, name)))
        return cm

    def getPlayAllContextMenuItems(self, name, playlist):
        cm = []
        cm.append((self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30312), "XBMC.RunPlugin(%s?action=play_all_yt&playlist_id=%s)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30303), "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlist&playlist_id=%s&title=%s)" % (utils.addon_url, playlist, name)))
        return cm

    def getFilterContextMenuItems(self, filter_type, filter_criteria):
        cm = []
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=%s&name=%s&title=%s)" % (utils.addon_url, filter_type, filter_criteria, filter_criteria)))
        cm.append((self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s)" % (utils.addon_url, filter_type, filter_criteria)))
        cm.append((self.lang(30302), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s&shuffle=true)" % (utils.addon_url, filter_type, filter_criteria)))
        cm.append((self.lang(30312), "XBMC.RunPlugin(%s?action=play_all_yt&filter_type=%s&filter_criteria=%s)" % (utils.addon_url, filter_type, filter_criteria)))
        cm.append((self.lang(30208), "XBMC.RunPlugin(%s?action=search&filter_type=%s&filter_criteria=%s)" % (utils.addon_url, filter_type, filter_criteria)))
        return cm

    def getPlaylistsContextMenuItems(self, name, playlist_type):
        cm = []
        cm.append((self.lang(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (utils.addon_url, playlist_type)))
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlists&playlist_type=%s&title=%s)" % (utils.addon_url, playlist_type, name)))
        return cm

    def getSearch(self, query):
        listItems = []

        def listAlbumsResults():
            listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30206)+' ***[/COLOR]',{'path':'none'}))
            cm = []
            for album in result['albums']:
                params = {'path':"search_result",'query':utils.tryEncode(album[0])}
                if len(album) > 3:
                    cm = [(self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&album_id=%s)" % (utils.addon_url, album[3]))]
                    params['albumid'] = album[3]
                listItems.append(self.createFolder("[%s] %s"%(album[1], album[0]), params, cm, album[2]))

        if isinstance(query,basestring):
            result = self.api.getSearch(query)
            if result['albums']: listAlbumsResults()
            if result['artists']:
                listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30205)+' ***[/COLOR]',{'path':'none'}))
                cm = []
                for artist in result['artists']:
                    params = {'path':"search_result",'query':utils.tryEncode(artist[0])}
                    if len(artist) > 2:
                        cm = [(self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&artist_id=%s)" % (utils.addon_url, artist[2]))]
                        params['artistid'] = artist[2]
                    listItems.append(self.createFolder(artist[0], params, cm, artist[1]))
            if result['tracks']:
                listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30213)+' ***[/COLOR]',{'path':'none'}))
                listItems.extend(self.addSongsFromLibrary(result['tracks'], 'library'))
        elif 'artistid' in query:
            result = self.api.getSearch(unquote_plus(query['query']))
            if result['albums']: listAlbumsResults()
            listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30213)+' ***[/COLOR]',{'path':'none'}))
            listItems.extend(self.addSongsFromLibrary(self.api.getArtist(query['artistid']), 'library'))
        elif 'albumid' in query:
            listItems.extend(self.addSongsFromLibrary(self.api.getAlbum(query['albumid']), 'library'))
        else:
            #listItems.extend(self.addSongsFromLibrary(self.api.getSearch(unquote_plus(query['query']))['tracks'], 'library'))
            listItems.extend(self.getSearch(unquote_plus(query['query'])))
        return listItems



