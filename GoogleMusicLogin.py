import os
import sys
import xbmcgui
import datetime

class GoogleMusicLogin():
    def __init__(self, gmusicapi):
        self.xbmcgui = sys.modules["__main__"].xbmcgui
        self.settings = sys.modules["__main__"].settings
        self.language = sys.modules["__main__"].language
        self.common = sys.modules["__main__"].common
        self.dbg = sys.modules["__main__"].dbg
        self.gmusicapi = gmusicapi

        self._cookie_file = os.path.join(self.settings.getAddonInfo('path'), self.settings.getSetting('cookie_file'))

    def login(self):
    	
        # Remove cookie file if it is older then 14 days
        # -> https://developers.google.com/gdata/faq#clientlogin_expire
        if ((os.path.isfile(self._cookie_file)) and
            ((datetime.datetime.now() - datetime.datetime.fromtimestamp(os.stat(self._cookie_file).st_mtime)).days >= 14)):
            os.remove(self._cookie_file)
            self.settings.setSetting('logged_in', "")
    	
    	# Continue with normal procedure
        if not self.settings.getSetting('logged_in'):
            self.common.log('Logging in')

            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')

            self.gmusicapi.login(username, password)

            if not self.gmusicapi.is_authenticated():
                self.common.log("Login failed")
                self.settings.setSetting('logged_in', "")
                dialog = self.xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
            else:
                self.common.log("Login succeeded")
                self.gmusicapi.session.cookies.save(filename=self._cookie_file, ignore_discard=True)
                self.settings.setSetting('logged_in', "1")
        else:
            from cookielib import LWPCookieJar

            self.common.log("Loading cookie from file")
            self.gmusicapi.session.cookies = LWPCookieJar()
            self.gmusicapi.session.cookies.load(filename=self._cookie_file, ignore_discard=True)
            self.gmusicapi.session.logged_in = True
