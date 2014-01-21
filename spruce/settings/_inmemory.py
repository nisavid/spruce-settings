"""In-memory format

This is a volatile (not persistent) settings representation format.

"""

__copyright__ = "Copyright (C) 2014 Ivan D Vasin"
__docformat__ = "restructuredtext"

from . import _core


_STORED_SETTINGS = {}


def _read_settings(_, keys):
    if keys == ['']:
        return _STORED_SETTINGS.copy()
    else:
        return {key: _STORED_SETTINGS[key] if key in _STORED_SETTINGS else None
                for key in keys}


def _write_settings(_, settings):
    global _STORED_SETTINGS
    for key, value in settings.iteritems():
        _STORED_SETTINGS[key] = value


_core.Settings.register_format('inmemory', extension='',
                               read_func=_read_settings,
                               write_func=_write_settings)
_paths = {('system', 'organization'): '/'.join(('system', '{organization}')),
          ('system', 'application'):
              '/'.join(('system', '{organization}', '{application}')),
          ('system', 'subsystem'):
              '/'.join(('system', '{organization}', '{application}',
                        '{subsystem}')),
          ('user', 'organization'): '/'.join(('user', '{organization}')),
          ('user', 'application'):
              '/'.join(('system', '{organization}', '{application}')),
          ('user', 'subsystem'):
              '/'.join(('system', '{organization}', '{application}',
                        '{subsystem}')),
          }
for (_base_scope, _component_scope), _path in _paths.iteritems():
    _core.Settings.set_path('inmemory', _base_scope, _component_scope, _path)
