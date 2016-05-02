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
        xbmc.log("[%s] %s" % (plugin, message))

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
    xbmcplugin.addDirectoryItems(handle, list_items)
    if handle > 0:
        xbmcplugin.setContent(handle, content)

    for sorts in sort_methods:
        xbmcplugin.addSortMethod(int(sys.argv[1]), sorts)

    if content == "songs":
        view_mode_id = addon.getSetting('songs_viewid')
    elif content == "albums":
        view_mode_id = addon.getSetting('albums_viewid')

    if view_mode_id and addon.getSetting('overrideview') == "true":
        xbmc.executebuiltin('Container.SetViewMode(%s)' % view_mode_id)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


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

def playAll(songs, shuffle=False):
    player = xbmc.Player()
    if (player.isPlaying()):
        player.stop()

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    for song in songs:
        playlist.add(getUrl(song), createItem(song['display_name'], song['albumart'], song['artistart']))

    if shuffle:
        playlist.shuffle()

    xbmc.executebuiltin('playlist.playoffset(music , 0)')
