import unittest
import mock
import addon
import constants


class TestSequenceFunctions(unittest.TestCase):
    def test_login_dialog(self):
        addon.settings.setSetting(constants.LOGGED_IN_KEY, None)
        with mock.patch('addon.plugin.addon.openSettings') as s:
            addon.index()
            s.assert_called_with()
