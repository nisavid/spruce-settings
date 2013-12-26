###############
Spruce-settings
###############

Spruce-settings is a Python library for application settings.

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
