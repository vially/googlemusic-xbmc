import sys, utils, xbmc


if (__name__ == "__main__" ):
    utils.log(" ARGV: " + repr(sys.argv))

    params = utils.paramsToDict(sys.argv[2])
    action = params.pop('action','')

    if action == 'play_song':

        import GoogleMusicPlaySong
        GoogleMusicPlaySong.GoogleMusicPlaySong().play(params)

    elif action:

        import GoogleMusicActions
        GoogleMusicActions.GoogleMusicActions().executeAction(action, params)

    elif params.get('path'):

        import GoogleMusicNavigation
        GoogleMusicNavigation.GoogleMusicNavigation().listMenu(params)

    elif not params:

        reload(sys)
        sys.setdefaultencoding("utf-8")

        import GoogleMusicStorage
        storage = GoogleMusicStorage.storage

        import GoogleMusicNavigation
        navigation = GoogleMusicNavigation.GoogleMusicNavigation()

        import GoogleMusicLogin
        login = GoogleMusicLogin.GoogleMusicLogin()

        addon = utils.addon

        # if version changed clear cache
        if not addon.getSetting('version') or addon.getSetting('version') != addon.getAddonInfo('version'):
           storage.clearCache()
           login.clearCookie()
           addon.setSetting('version', addon.getAddonInfo('version'))

        # check for initing cookies, db and library only on main menu
        storage.checkDbInit()
        login.checkCredentials()
        login.checkCookie()
        login.initDevice()

        # check if library needs to be loaded
        if addon.getSetting('fetched_all_songs') == '0':

            xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (utils.plugin, utils.tryEncode(addon.getLocalizedString(30105)) ,addon.getAddonInfo('icon')))
            utils.log('Loading library')
            navigation.api.loadLibrary()

            if addon.getSetting('auto_export')=='true' and addon.getSetting('export_path'):
                import GoogleMusicActions
                GoogleMusicActions.GoogleMusicActions().exportLibrary(addon.getSetting('export_path'))

        navigation.listMenu()

    else:
        utils.log(" ARGV Nothing done.. verify params " + repr(params))