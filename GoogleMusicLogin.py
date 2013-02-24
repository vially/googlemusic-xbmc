import os
import sys
import datetime

class GoogleMusicLogin():
    def __init__(self, gmusicapi):
        self.main = sys.modules["__main__"]
        self.xbmcgui = self.main.xbmcgui
        self.xbmc = self.main.xbmc
        self.settings = self.main.settings
        self.gmusicapi = gmusicapi

        self._cookie_file = os.path.join(self.xbmc.translatePath(self.settings.getAddonInfo('profile')), self.settings.getSetting('cookie_file'))

    def checkCookie(self):
        # Remove cookie file if it is older then 14 days
        # -> https://developers.google.com/gdata/faq#clientlogin_expire
        if os.path.isfile(self._cookie_file):
          if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.stat(self._cookie_file).st_mtime)).days >= 14:
            os.remove(self._cookie_file)
            self.settings.setSetting('logged_in', "")
        else:
            self.settings.setSetting('logged_in', "")

    def clearCookie(self):
        if os.path.isfile(self._cookie_file):
            os.remove(self._cookie_file)
        self.settings.setSetting('logged_in', "")

    def login(self):
        # Continue with normal procedure
        if not self.settings.getSetting('logged_in'):
            self.main.log('Logging in')
            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')

            self.gmusicapi.login(username, password, False)
            if not self.gmusicapi.is_authenticated():
                self.main.log("Login failed")
                self.settings.setSetting('logged_in', "")
                self.language = self.settings.getLocalizedString
                dialog = self.xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
            else:
                self.main.log("Login succeeded")
                self.gmusicapi.session.web_cookies.save(filename=self._cookie_file, ignore_discard=True)
                self.settings.setSetting('logged_in', "1")
        else:

            from cookielib import LWPCookieJar

            self.main.log("Loading cookie from file")
            self.gmusicapi.session.web_cookies = LWPCookieJar()
            self.gmusicapi.session.web_cookies.load(filename=self._cookie_file, ignore_discard=True)
            self.gmusicapi.session.logged_in = True
