# -*- coding: utf-8 -*-

"""
Single interface for code that varies across Python environments.
"""

import sys

_ver = sys.version_info
is_py26 = (_ver[:2] == (2, 6))

if is_py26:
    try:
       import simplejson as json
    except:
       import json
else:  # 2.7
    import json  # noqa

try:
    from appdirs import AppDirs
    my_appdirs = AppDirs('gmusicapi', 'Simon Weber')
except ImportError:

    class FakeAppDirs(object):
        to_spoof = set([base + '_dir' for base in
                        ('user_data', 'site_data', 'user_config',
                         'site_config', 'user_cache', 'user_log')])

        def __getattr__(self, name):
            if name in self.to_spoof:
                return '.'  # current dir
            else:
                raise AttributeError

    my_appdirs = FakeAppDirs()
