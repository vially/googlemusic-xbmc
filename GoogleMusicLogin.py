import utils, xbmc, xbmcgui
from datetime import datetime
from gmusicapi import Mobileclient

class GoogleMusicLogin():
    def __init__(self):
        self.gmusicapi = Mobileclient(debug_logging=False, validate=False, verify_ssl=True)

    def checkCookie(self):
        # Remove cookie data if it is older then 7 days
        if utils.addon.getSetting('cookie-date') != None and len(utils.addon.getSetting('cookie-date')) > 0:
            import time
            if (datetime.now() - datetime(*time.strptime(utils.addon.getSetting('cookie-date'), '%Y-%m-%d %H:%M:%S.%f')[0:6])).days >= 7:
                self.clearCookie()

    def checkCredentials(self):
        if not utils.addon.getSetting('username'):
            utils.addon.openSettings()
        if utils.addon.getSetting('password') and utils.addon.getSetting('password') != '**encoded**':
            import base64
            utils.addon.setSetting('encpassword',base64.b64encode(utils.addon.getSetting('password')))
            utils.addon.setSetting('password','**encoded**')

    def getApi(self):
        return self.gmusicapi

    def getStreamUrl(self,song_id):
        # retrieve registered device
        device_id = self.getDevice()
        # retrieve stream quality from settings
        quality = { '0':'hi','1':'med','2':'low' } [utils.addon.getSetting('quality')]
        utils.log("getStreamUrl songid: %s device: %s quality: %s"%(song_id, device_id, quality))

        return self.gmusicapi.get_stream_url(song_id, device_id, quality)

    def getDevice(self):
        return utils.addon.getSetting('device_id')

    def initDevice(self):
        device_id = self.getDevice()

        if not device_id:
            utils.log('Trying to fetch the device_id')
            self.login()
            try:
                devices = self.gmusicapi.get_registered_devices()
                if len(devices) == 10:
                    utils.log("WARNING: 10 devices already registered!")
                utils.log('Devices: '+repr(devices))
                for device in devices:
                    if device["type"] in ("ANDROID","PHONE","IOS"):
                        device_id = str(device["id"])
                        break
            except:
                pass

            if device_id:
                if device_id.lower().startswith('0x'): device_id = device_id[2:]
                utils.addon.setSetting('device_id', device_id)
                utils.log('Found device_id: '+device_id)

    def clearCookie(self):
        utils.addon.setSetting('logged_in-mobile', "")
        utils.addon.setSetting('authtoken-mobile', "")
        utils.addon.setSetting('device_id', "")

    def logout(self):
        self.gmusicapi.logout()

    def login(self, nocache=False):
        if not utils.addon.getSetting('logged_in-mobile') or nocache:
            import base64

            utils.log('Logging in')
            self.checkCredentials()
            username = utils.addon.getSetting('username')
            password = base64.b64decode(utils.addon.getSetting('encpassword'))

            try:
                self.gmusicapi.login(username, password, utils.addon.getSetting('device_id'))
                if not self.gmusicapi.is_authenticated():
                    self.gmusicapi.login(username, password, Mobileclient.FROM_MAC_ADDRESS)
            except Exception as e:
                utils.log(repr(e))

            if not self.gmusicapi.is_authenticated():
                utils.log("Login failed")
                utils.addon.setSetting('logged_in-mobile', "")
                self.language = utils.addon.getLocalizedString
                dialog = xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
                #utils.addon.openSettings()
                raise
            else:
                utils.log("Login succeeded")
                utils.addon.setSetting('logged_in-mobile', "1")
                utils.addon.setSetting('authtoken-mobile', self.gmusicapi.session._authtoken)
                utils.addon.setSetting('cookie-date', str(datetime.now()))
                try:
                    self.gmusicapi.get_listen_now()
                    utils.addon.setSetting('all-access', "1")
                except:
                    utils.addon.setSetting('all-access', "0")


        else:

            utils.log("Loading auth from cache")
            self.gmusicapi.session._authtoken = utils.addon.getSetting('authtoken-mobile')
            self.gmusicapi.session.is_authenticated = True