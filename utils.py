import sys, xbmcplugin, xbmcaddon, xbmc
from xbmcgui import ListItem

# xbmc hooks
addon = xbmcaddon.Addon(id='plugin.audio.googlemusic.exp')

# plugin constants
plugin    = "GoogleMusicEXP-" + addon.getAddonInfo('version')
dbg       = addon.getSetting( "debug" ) == "true"
addon_url = sys.argv[0]
handle    = int(sys.argv[1])

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

def createItem(title, thumb):
    li = ListItem(title)
    try:
        li.setThumbnailImage(thumb)
    except: pass
    li.setProperty('IsPlayable', 'true')
    li.setProperty('Music', 'true')
    li.setProperty('mimetype', 'audio/mpeg')
    return li

def setResolvedUrl(listItem):
    xbmcplugin.setResolvedUrl(handle=handle, succeeded=True, listitem=listItem)

def setDirectory(listItems, content, sortMethods):
    xbmcplugin.addDirectoryItems(handle, listItems)
    if handle > 0:
        xbmcplugin.setContent(handle, content)

    for sorts in sortMethods:
        xbmcplugin.addSortMethod(int(sys.argv[1]), sorts)

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