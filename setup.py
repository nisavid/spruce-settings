#!/usr/bin/env python

__copyright__ = "Copyright (C) 2013 Ivan D Vasin and Cogo Labs"
__credits__ = ["Ivan D Vasin"]
__maintainer__ = "Ivan D Vasin"
__email__ = "nisavid@gmail.com"
__docformat__ = "restructuredtext"

from setuptools import find_packages as _find_packages, setup as _setup


# basics ----------------------------------------------------------------------

NAME_NOPREFIX = 'settings'

NAME = 'nisavid-' + NAME_NOPREFIX

VERSION = '0'

SITE_URI = ''

DESCRIPTION = 'Application settings.'

LONG_DESCRIPTION = DESCRIPTION + '''

Some applications require certain settings to exist before they are
launched.  Some applications require the ability to save certain
settings so that they persist after termination.  It is desirable to
access both persistent and runtime settings via a uniform interface.
This package provides objects that satisfy these requirements.

Settings may be stored in a variety of ways.  Windows uses a system
registry.  OS X uses XML preferences files.  Many Unix applications use
INI-style configuration (conf) files.  It is desirable to store some
settings in a database.  For now, this module implements only the conf
file method, but it provides enough abstraction to allow for other
methods to be implemented as needed.
'''

LICENSE = 'LGPLv3'

TROVE_CLASSIFIERS = \
    ('Development Status :: 5 - Production/Stable',
     'Intended Audience :: Developers',
     'License :: OSI Approved :: GNU Lesser General Public License v3'
      ' (LGPLv3)',
     'Operating System :: POSIX',
     'Programming Language :: Python :: 2.7',
     'Topic :: Software Development :: Libraries :: Python Modules',
     )


# dependencies ----------------------------------------------------------------

SETUP_DEPS = ()

INSTALL_DEPS = ('nisavid-collections',)

EXTRAS_DEPS = {}

TESTS_DEPS = ()

DEPS_SEARCH_URIS = ()


# packages --------------------------------------------------------------------

PARENT_NAMESPACE_PKG = 'nisavid'

ROOT_PKG = '.'.join((PARENT_NAMESPACE_PKG, NAME_NOPREFIX))

NAMESPACE_PKGS = (PARENT_NAMESPACE_PKG,)

SCRIPTS_PKG = '.'.join((ROOT_PKG, 'scripts'))

TESTS_PKG = '.'.join((ROOT_PKG, 'tests'))


# entry points ----------------------------------------------------------------

STD_SCRIPTS_PKG_COMMANDS = {}

COMMANDS = {cmd: '{}.{}:{}'.format(SCRIPTS_PKG,
                                   script if isinstance(script, basestring)
                                          else script[0],
                                   'main' if isinstance(script, basestring)
                                          else script[1])
            for cmd, script in STD_SCRIPTS_PKG_COMMANDS.items()}

ENTRY_POINTS = {'console_scripts': ['{} = {}'.format(name, funcpath)
                                    for name, funcpath in COMMANDS.items()]}


if __name__ == '__main__':
    _setup(name=NAME,
           version=VERSION,
           url=SITE_URI,
           description=DESCRIPTION,
           long_description=LONG_DESCRIPTION,
           author=', '.join(__credits__),
           maintainer=__maintainer__,
           maintainer_email=__email__,
           license=LICENSE,
           classifiers=TROVE_CLASSIFIERS,
           setup_requires=SETUP_DEPS,
           install_requires=INSTALL_DEPS,
           extras_require=EXTRAS_DEPS,
           tests_require=TESTS_DEPS,
           dependency_links=DEPS_SEARCH_URIS,
           namespace_packages=NAMESPACE_PKGS,
           packages=_find_packages(),
           test_suite=TESTS_PKG,
           include_package_data=True,
           entry_points=ENTRY_POINTS)
