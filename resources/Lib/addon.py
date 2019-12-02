import sys
import xbmc
import utils

if __name__ == "__main__":
    utils.log(" ARGV: " + repr(sys.argv))

    params = utils.paramsToDict(sys.argv[2])
    action = params.pop('action', '')

    if action == 'play_song':

        from playsong import PlaySong

        PlaySong().play(params)

    else:

        libgen = None
        pDialog = None
        count = 0

        if utils.get_system_version() < (18, 0):
            from xbmcgui import Dialog
            dialog = xbmcgui.Dialog()
            dialog.ok("Version Check", "This addon is compatible with Kodi 18 or earlier")
            raise Exception

        # if new version trigger init cache db
        if (not utils.addon.getSetting('version') or
                utils.addon.getSetting('version') != utils.addon.getAddonInfo('version')):
            utils.addon.setSetting('version', utils.addon.getAddonInfo('version'))
            from storage import storage
            storage.clearCache()
            storage.init_database()
            storage.init_indexes()

        # utils.log("#1# INIT STARTED :"+repr(utils.get_mem_cache('init_started'))+" - FETCHED TIME: "+str(utils.addon.getSettingInt('fetched_time')))

        if utils.addon.getSettingInt('fetched_time') == 0 and utils.get_mem_cache('init_started') != '1':
            # starts loading library
            utils.log("Initing addon data")
            utils.set_mem_cache('init_started', '1')

            from api import Api
            libgen = Api().getApi().get_all_songs(incremental=True)
            try:
                chunk = libgen.next()
                count = len(chunk)

                from xbmcgui import DialogProgressBG
                pDialog = DialogProgressBG()
                pDialog.create(utils.addon.getLocalizedString(30105), str(count)+" "+utils.addon.getLocalizedString(30213))

                from storage import storage
                storage.storeInAllSongs(chunk)
                utils.addon.setSettingInt("fetched_count", count)
            except StopIteration:
                utils.set_mem_cache('init_started', '0')
                utils.log("No data to load")
                pass

            if count == 0:
                xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (utils.plugin, utils.tryEncode("No tracks found"), utils.addon.getAddonInfo('icon')))

        if action:
            # execute action
            from actions import Actions

            Actions().executeAction(action, params)

        else:
            # show navigation menus
            from navigation import Navigation

            Navigation().listMenu(params)

        if pDialog:
            # finish loading library in background
            for chunk in libgen:
                storage.storeInAllSongs(chunk)
                count = count + len(chunk)
                pDialog.update(50, message=str(count)+" "+utils.addon.getLocalizedString(30213))

            pDialog.update(90, message=utils.addon.getLocalizedString(30202))
            storage.storePlaylistSongs(Api().getApi().get_all_user_playlist_contents())

            import time
            utils.addon.setSettingInt("fetched_time", int(time.time()))
            utils.addon.setSettingInt("fetched_count", count)
            utils.set_mem_cache('init_started', '0')
            utils.log("Finished loading data")

            # utils.log("#2# INIT STARTED :"+repr(utils.get_mem_cache('init_started'))+" - FETCHED TIME: "+str(utils.addon.getSettingInt('fetched_time')))

        import time
        if utils.addon.getSettingInt("fetched_time") > 0 and utils.addon.getSettingInt("fetched_time") + 600 < int(time.time()):
            # check for updates
            from api import Api
            from datetime import datetime
            after = datetime.fromtimestamp(utils.addon.getSettingInt("fetched_time"))
            utils.addon.setSettingInt("fetched_time", int(time.time()))
            updates = Api().getApi().get_all_songs(updated_after=after)
            if len(updates) > 0:
                utils.log("FOUND LIBRARY UPDATES: "+repr(after)+" - "+repr(len(updates)))
                from storage import storage
                storage.storeInAllSongs(updates)
            updates = Api().getApi().get_all_playlists(updated_after=after)
            if len(updates) > 0:
                utils.log("FOUND PLAYLISTS UPDATES: "+repr(after)+" - "+repr(len(updates)))
                from storage import storage
                storage.storePlaylistSongs(Api().getApi().get_all_user_playlist_contents())




