import sys, utils, xbmc


if (__name__ == "__main__" ):
    utils.log(" ARGV: " + repr(sys.argv))

    params = utils.paramsToDict(sys.argv[2])
    action = params.pop('action','')

    if action == 'play_song':

        import GoogleMusicPlaySong
        GoogleMusicPlaySong.GoogleMusicPlaySong().play(params)

    else:

        # check hourly if addon needs initing any data
        import time
        if (not utils.addon.getSetting('last-checked') or
            time.time() - float(utils.addon.getSetting('last-checked')) > 3600):
            utils.checkInit()
            utils.addon.setSetting('last-checked',str(time.time()))

        # if any vital setting is missing, trigger init
        if (not utils.addon.getSetting('authtoken-mobile') or
            not utils.addon.getSetting('version') or
            utils.addon.getSetting('version') != utils.addon.getAddonInfo('version') or
            utils.addon.getSetting('fetched_all_songs') == '0'):

            utils.initAddon()

        if action:

            import GoogleMusicActions
            GoogleMusicActions.GoogleMusicActions().executeAction(action, params)

        else:

            import GoogleMusicNavigation
            GoogleMusicNavigation.GoogleMusicNavigation().listMenu(params)

