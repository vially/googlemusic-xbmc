import sys, xbmcplugin, xbmcaddon
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
        print "[%s] %s" % (plugin, message)

def paramsToDict(parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split('&')
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if len(paramSplits) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
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
    if handle < 0: return
    xbmcplugin.addDirectoryItems(handle, listItems)
    xbmcplugin.setContent(handle, content)

    for sorts in sortMethods:
        xbmcplugin.addSortMethod(int(sys.argv[1]), sorts)

    xbmcplugin.endOfDirectory(handle, succeeded=True)