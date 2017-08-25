import sys, xbmcplugin, xbmcaddon, xbmc
from xbmcgui import ListItem

# xbmc hooks
addon = xbmcaddon.Addon(id='plugin.audio.googlemusic.exp')

# plugin constants
plugin    = "GoogleMusicEXP-" + addon.getAddonInfo('version')
dbg       = addon.getSetting( "debug" ) == "true"
addon_url = sys.argv[0]
handle    = int(sys.argv[1])
song_url  = "%s?action=play_song&song_id=%s&title=%s&artist=%s&albumart=%s&tracknumber=%s&album=%s&year=%s&rating=%s&artistart=%s"

# utility functions
def log(message):
    if dbg:
        xbmc.log("[%s] %s" % (plugin, message), xbmc.LOGNOTICE)

def paramsToDict(parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split('&')
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            try:
                paramDict[paramSplits[0]] = paramSplits[1]
            except: pass
    return paramDict

def createItem(title, thumb, fanart):
    li = ListItem(title)
    li.setArt({'thumb':thumb, 'fanart':fanart})
    li.setProperty('IsPlayable', 'true')
    li.setProperty('Music', 'true')
    li.setProperty('mimetype', 'audio/mpeg')
    return li

def setResolvedUrl(list_item):
    xbmcplugin.setResolvedUrl(handle=handle, succeeded=True, listitem=list_item)

def setDirectory(list_items, content, sort_methods, view_mode_id):
    xbmcplugin.addDirectoryItems(handle, list_items, len(list_items))
    if handle > 0:
        xbmcplugin.setContent(handle, content)

    for sorts in sort_methods:
        xbmcplugin.addSortMethod(int(sys.argv[1]), sorts)

    if content == "songs":
        view_mode_id = addon.getSetting('songs_viewid')
    elif content == "albums":
        view_mode_id = addon.getSetting('albums_viewid')

    xbmcplugin.endOfDirectory(handle, succeeded=True)

    if view_mode_id and addon.getSetting('overrideview') == "true":
        xbmc.executebuiltin('Container.SetViewMode(%s)' % view_mode_id)

def tryEncode(text, encoding='utf-8'):
    try:
        if sys.platform.startswith('linux'):
           return text.decode(encoding).encode('latin1')
        return unicode(text.decode(encoding))
    except: pass
    try:
        return text.encode(encoding, errors='ignore')
    except:
        log(" ENCODING FAIL!!! "+encoding+" "+repr(text))
    return repr(text)

def getUrl(song):
    url = song_url % (addon_url, song['song_id'], song['title'], song['artist'], song['albumart'],
                      song['tracknumber'], song['album'], song['year'], song['rating'], song['artistart'])
    if 'sessiontoken' in song:
        url += "&sessiontoken=%s&wentryid=%s" % ( song['sessiontoken'], song['wentryid'] )
    return url

def playAll(songs, shuffle=False, fromhere=''):
    player = xbmc.Player()
    if (player.isPlaying()):
        player.stop()

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    fromhereSong = None
    for song in songs:
        if song['song_id'] != fromhere:
            item = createItem(song['display_name'], song['albumart'], song['artistart'])
            item.setInfo(type='music', infoLabels={'artist':song['artist'],'title':song['title']})
            playlist.add(getUrl(song), item )
        else:
            fromhereSong = song

    if shuffle or fromhere:
        playlist.shuffle()

    if fromhere:
        item = createItem(fromhereSong['display_name'], fromhereSong['albumart'], fromhereSong['artistart'])
        item.setInfo(type='music', infoLabels={'artist':fromhereSong['artist'],'title':fromhereSong['title']})
        playlist.add(getUrl(fromhereSong), item, 0)

    xbmc.executebuiltin('playlist.playoffset(music , 0)')

def checkInit():
    import GoogleMusicStorage
    storage = GoogleMusicStorage.storage
    import GoogleMusicLogin
    login = GoogleMusicLogin.GoogleMusicLogin()

    log("Checking init data")
    storage.checkDbInit()
    login.checkCredentials()
    login.checkCookie()
    login.initDevice()


def initAddon():
    import GoogleMusicStorage
    storage = GoogleMusicStorage.storage
    import GoogleMusicLogin
    login = GoogleMusicLogin.GoogleMusicLogin()

    if addon.getSetting('init-started') == '1':
        return

    log("Initing addon data")

    addon.setSetting('init-started','1')

    try:
        reload(sys)
        sys.setdefaultencoding("utf-8")

         # if version changed clear cache
        if not addon.getSetting('version') or addon.getSetting('version') != addon.getAddonInfo('version'):
           storage.clearCache()
           login.clearCookie()
           addon.setSetting('version', addon.getAddonInfo('version'))

        # check for initing cookies, db and library
        storage.checkDbInit()
        login.checkCredentials()
        login.checkCookie()
        login.initDevice()

        # check if library needs to be loaded
        if addon.getSetting('fetched_all_songs') == '0':

            xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (plugin, tryEncode(addon.getLocalizedString(30105)) ,addon.getAddonInfo('icon')))
            log('Loading library')
            import GoogleMusicApi
            GoogleMusicApi.GoogleMusicApi().loadLibrary()

            if addon.getSetting('auto_export')=='true' and addon.getSetting('export_path'):
                import GoogleMusicActions
                GoogleMusicActions.GoogleMusicActions().exportLibrary(addon.getSetting('export_path'))
    except Exception as e:
        log("ERROR: "+repr(e))

    addon.setSetting('init-started','0')
