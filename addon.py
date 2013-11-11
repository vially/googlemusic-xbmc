from xbmcswift2 import Plugin
from gmusicapi import Mobileclient
import constants


plugin = Plugin()
settings = plugin.addon


@plugin.route('/')
def index():
    if not settings.getSetting(constants.LOGGED_IN_KEY):
        settings.openSettings()
        return

    item = {
        'label': 'All songs',
        'path': plugin.url_for('all_songs')
    }

    return [item]


@plugin.route('/all_songs')
def all_songs():
    api = Mobileclient()
    api.login(settings.getSetting(constants.USERNAME_KEY), settings.getSetting(constants.PASSWORD_KEY))

    library = api.get_all_songs()
    items = [{
        'label': track['artist'],
        'path': plugin.url_for('devnull', song_id=track['id'])
    } for track in library]

    return items

@plugin.route('/dev/null')
def devnull():
    return []


if __name__ == '__main__':
    plugin.run()
