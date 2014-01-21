"""Conf format

The conf format is registered by default.  It reads and writes settings
using :mod:`ConfigParser` at locations that are similar to typical Unix
configuration files---that is, in :file:`.conf` files specific to each
component scope under :file:`/etc/{organization}` for system-wide
settings and under :file:`~/.{organization}` for user-specific settings.

"""

__copyright__ = "Copyright (C) 2014 Ivan D Vasin"
__docformat__ = "restructuredtext"

import ConfigParser as _configparser
# TODO: (Python 3)
#import configparser as _configparser
import os as _os

from . import _core
from . import _exc


def _read_settings(file_, keys):

    settings = {}

    parser = _configparser.RawConfigParser(allow_no_value=True)
    parser.read(file_)

    if keys == ['']:
        for section in parser.sections():
            for subkey, value in parser.items(section):
                settings[section + '/' + subkey] = value
    else:
        for key in keys:
            section, _, subkey = key.rpartition('/')
            if not section:
                section = _configparser.DEFAULTSECT

            if parser.has_section(section) \
                   and parser.has_option(section, subkey):
                try:
                    settings[key] = parser.get(section, subkey)
                except _configparser.Error as exc:
                    raise _exc.MalformedSettingsLocation(message=str(exc))
            else:
                settings[key] = None

    return settings


def _write_settings(file_, settings):
    if settings:
        # FIXME
        raise NotImplementedError('writing \'conf\' settings is not yet'
                                  ' implemented')


_core.Settings.register_format('conf', extension='.conf',
                               read_func=_read_settings,
                               write_func=_write_settings)

_homedir = _os.path.expanduser('~')
_paths = {('system', 'organization'):
              _os.path.join(_os.path.sep, 'etc', '{organization}',
                            '{organization}{extension}'),
          ('system', 'application'):
              _os.path.join(_os.path.sep, 'etc', '{organization}',
                            '{application}{extension}'),
          ('system', 'subsystem'):
              _os.path.join(_os.path.sep, 'etc', '{organization}',
                            '{application}', '{subsystem}{extension}'),
          ('user', 'organization'):
              _os.path.join(_homedir, '.{organization}',
                            '{organization}{extension}'),
          ('user', 'application'):
              _os.path.join(_homedir, '.{organization}',
                            '{application}{extension}'),
          ('user', 'subsystem'):
              _os.path.join(_homedir, '.{organization}', '{application}',
                            '{subsystem}{extension}'),
          }
for (_base_scope, _component_scope), _path in _paths.iteritems():
    _core.Settings.set_path('conf', _base_scope, _component_scope, _path)
