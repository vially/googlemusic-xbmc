import oauth2client.client
import os
import utils
import xbmc
import xbmcgui
from gmusicapi import Mobileclient


class Login:
    def __init__(self):
        import requests.packages.urllib3
        requests.packages.urllib3.disable_warnings()  # Silence unneeded warnings

        self.gmusicapi = Mobileclient(debug_logging=False, validate=False, verify_ssl=False)

        # self.gmusicapi._session_class.lang = xbmc.getLanguage(xbmc.ISO_639_1, True)
        # utils.log(repr(xbmc.getLanguage(xbmc.ISO_639_1, True)))


    def getApi(self):
        return self.gmusicapi


    def getStreamUrl(self, song_id, session_token, wentry_id):
        # retrieve stream quality from settings
        quality = {'0': 'hi', '1': 'med', '2': 'low'}[utils.addon.getSetting('quality')]

        if wentry_id:
            return self.gmusicapi.get_station_track_stream_url(song_id, wentry_id, session_token, quality)

        # retrieve registered device
        device_id = self.get_device_id()
        utils.log("getStreamUrl song id: %s device: %s quality: %s" % (song_id, device_id, quality))
        return self.gmusicapi.get_stream_url(song_id, device_id, quality)


    def get_device_id(self):
        device_id = utils.addon.getSetting('device_id')

        if not device_id:
            utils.log('Trying to fetch the device id')
            self.login()
            try:
                devices = self.gmusicapi.get_registered_devices()
                if len(devices) == 10:
                    utils.log("WARNING: 10 devices already registered!")
                utils.log('Devices: ' + repr(devices))
                for device in devices:
                    if device["type"] in ("ANDROID", "PHONE", "IOS"):
                        device_id = str(device["id"])
                        break
            except Exception as e:
                utils.log("ERROR: " + repr(e))

            if device_id:
                if device_id.lower().startswith('0x'): device_id = device_id[2:]
                utils.addon.setSetting('device_id', device_id)
                utils.log('Found device_id: ' + device_id)
            else:
                utils.log('No Android device found in account')
                xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (utils.plugin, utils.tryEncode(utils.addon.getLocalizedString(30111)), utils.addon.getAddonInfo('icon')))
        return device_id


    def login(self, nocache=False):
        if not utils.get_mem_cache('oauth'):
            path = os.path.join(xbmc.translatePath(utils.addon.getAddonInfo('profile')).decode('utf-8'), "gpmusic.oauth")
            credentials=None
            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    credentials = self.load_credentials(f.read())

            if credentials is None:
                # utils.log("1 "+repr(self.gmusicapi._session_class.oauth._asdict()))
                flow = oauth2client.client.OAuth2WebServerFlow(**self.gmusicapi._session_class.oauth._asdict())
                #auth_uri = flow.step1_get_authorize_url()
                auth_uri = flow.step1_get_device_and_user_codes()

                utils.log(repr(auth_uri))

                interval = int(auth_uri.interval) * 1000
                if interval > 60000:
                    interval = 5000
                user_code = auth_uri.user_code
                dp = xbmcgui.DialogProgress()
                dp.create("Sign In", "Access "+auth_uri.verification_url+" and enter code "+user_code)

                steps = ((10 * 60 * 1000) // interval)  # 10 Minutes
                count = 0
                for i in range(steps):
                    dp.update(int(count * 100 / steps))
                    count = count + 1
                    try:
                        credentials = flow.step2_exchange(device_flow_info=auth_uri)
                        with open(path, 'w') as f:
                            f.write(credentials.to_json())
                        break
                    except oauth2client.client.FlowExchangeError:
                        pass
                    if dp.iscanceled():
                        utils.log("Wait dialog canceled")
                        dp.close()

                    xbmc.sleep(interval)
                dp.close()

                #import urllib
                #auth_uri = urllib.unquote_plus(auth_uri)
                #utils.log("AUTH_URI "+auth_uri)
                #short = self.short_url(auth_uri)
                #utils.log("SHORT "+short)

                #keyboard = xbmc.Keyboard('',"Get authorization code in: "+ short)
                #keyboard.doModal()
                #if keyboard.isConfirmed() and keyboard.getText():
                #    credentials = flow.step2_exchange(keyboard.getText())
                #    with open(path, 'w') as f:
                #        f.write(credentials.to_json())

            self.gmusicapi.session.login(credentials)

            if not self.gmusicapi.is_authenticated():
                utils.log("Login failed")
                language = utils.addon.getLocalizedString
                dialog = xbmcgui.Dialog()
                dialog.ok(language(30101), language(30102))
                raise Exception
            else:
                utils.set_mem_cache('oauth', credentials.to_json())

        else:
            utils.log("Loading auth from cache")
            self.gmusicapi.session._oauth_creds = self.load_credentials(utils.get_mem_cache('oauth'))
            if self.gmusicapi.session._oauth_creds.access_token_expired:
                utils.log("Refresh Token")
                self.gmusicapi.session.login(self.gmusicapi.session._oauth_creds)
                utils.set_mem_cache('oauth', self.gmusicapi.session._oauth_creds.to_json())
            self.gmusicapi.session.is_authenticated = True

        self.gmusicapi._authtype = 'oauth'
        utils.addon.setSettingBool('subscriber', self.gmusicapi.is_subscribed)


    def clear_oauth_cache(self):
        utils.set_mem_cache('oauth', '')
        path = os.path.join(xbmc.translatePath(utils.addon.getAddonInfo('profile')).decode('utf-8'), "gpmusic.oauth")
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception as ex:
                utils.log("Error trying to delete oauth cache " + repr(ex))


    def load_credentials(self, json_credentials):
        import json, datetime, time
        data = json.loads(json_credentials)
        expiry = datetime.datetime(*(time.strptime(data['token_expiry'], oauth2client.client.EXPIRY_FORMAT)[0:6]))
        data['token_expiry'] = None
        credentials = oauth2client.client.Credentials.new_from_json(json.dumps(data))
        credentials.token_expiry = expiry
        return credentials


    def short_url(self, longurl):
        import requests
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
                   'Host': 'firebasedynamiclinks.googleapis.com',
                   'Content-Type': 'application/json',
                   }
        params = '''{
                  'dynamicLinkInfo': {
                    'domainUriPrefix': 'https://playmusicexp.page.link',
                    'link': '%s'},
                  'suffix': {'option': 'SHORT'},
                  }'''

        url = 'https://firebasedynamiclinks.googleapis.com/v1/shortLinks?key=AIzaSyCpYQnhH6BA_wGBB79agx_32kuoq7WwTZg'
        response = requests.post(url, data=params % longurl, headers=headers)

        utils.log(response.text)
        try:
            json_data = response.json()
            if 'error' in json_data:
                utils.log('Requesting failed: Code: |%s| JSON: |%s|' % (str(response.status_code), json_data))
        except ValueError:
            return None

        return json_data['shortLink']
