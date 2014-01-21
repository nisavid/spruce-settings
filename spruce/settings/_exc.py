"""Exceptions"""

__copyright__ = "Copyright (C) 2014 Ivan D Vasin"
__docformat__ = "restructuredtext"

import exceptions as _py_exc


class Exception(_py_exc.Exception):
    pass


class Error(RuntimeError, Exception):
    pass


class InvalidSettingsValue(Error):

    """A settings value is invalid

    This represents an invalid *value* for a given *key*.

    :param str key:
        A settings key.

    :param str value:
        The value of the given *key*.

    :param type:
        A settings value type.  The name of one of the types handled by a
        corresponding :samp:`Settings.{type}value()` method.  Null implies
        the generic type, a string.
    :type type: :obj:`str` or null

    :param message:
        A description of how *value* is invalid.
    :type message: :obj:`str` or null

    """

    def __init__(self, key, value, type=None, message=None, *args):
        super(InvalidSettingsValue, self).__init__(key, value, type, message,
                                                   *args)
        self._key = key
        self._message = message
        self._type = type
        self._value = value

    def __str__(self):
        value_str = u'value {!r} for {!r}'.format(self.value, self.key)
        if self.type:
            value_str = u'{} {}'.format(self.type, value_str)
        message = u'invalid {} in persistent settings'.format(value_str)
        if self.message:
            message += u': {}'.format(self.message)
        return message

    @property
    def key(self):
        return self._key

    @property
    def message(self):
        return self._message

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value


class MalformedSettingsLocation(Error):

    """A settings location is malformed

    :param location:
        A settings location.
    :type location: :obj:`str` or null

    :param message:
        A description of how *location* is malformed.
    :type message: :obj:`str` or null

    """

    def __init__(self, location=None, message=None, *args):
        super(MalformedSettingsLocation, self).__init__(location, message,
                                                        *args)
        self._location = location
        self._message = message

    def __str__(self):
        message = 'malformed persistent settings'
        if self.location:
            message += u' at {!r}'.format(self.location)
        if self.message:
            message += u': {}'.format(self.message)
        return message

    @property
    def location(self):
        return self._location

    @property
    def message(self):
        return self._message


class MissingRequiredSettingsValue(Error):

    """A required value is missing

    This represents a missing value for a given *key*, optionally
    specifying the expected *type* and inspected *locations*.

    .. note::
        A setting is considered missing only if it is absent.  An empty
        value is a value nonetheless.

    :param str key:
        A settings key.

    :param type:
        A settings value type.  The name of one of the types handled by a
        corresponding :samp:`Settings.{type}value()` method.  :obj:`None`
        implies the generic type, a string.
    :type type: :obj:`str` or null

    :param locations:
        Settings locations.
    :type locations: ~[:obj:`str`] or null

    """

    def __init__(self, key, type=None, locations=None, *args):
        super(MissingRequiredSettingsValue, self).__init__(key, type,
                                                           locations, *args)
        self._key = key
        self._locations = locations
        self._type = type

    def __str__(self):
        required_value_str = u'value for {!r}'.format(self.key)
        if self.type:
            required_value_str = u'{} {}'.format(self.type, required_value_str)
        message = u'missing required {} in persistent settings'\
                   .format(required_value_str)
        if self.locations:
            message += u' at {}'.format(self.locations)
        return message

    @property
    def key(self):
        return self._key

    @property
    def locations(self):
        return self._locations

    @property
    def type(self):
        return self._type
