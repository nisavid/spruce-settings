"""Exceptions."""

__copyright__ = "Copyright (C) 2014 Ivan D Vasin"
__docformat__ = "restructuredtext"


class SettingsError(RuntimeError):
    """There is an error in some persistent settings."""
    pass


class InvalidSettingsValue(SettingsError):
    """A settings value is invalid.

    This represents an invalid *value* for a given *key*.

    :param str key:
        A settings key.

    :param str value:
        The value of the given *key*.

    :param type:
        A settings value type.  The name of one of the types handled by a
        corresponding :samp:`Settings.{type}value()` method.  :obj:`None`
        implies the generic type, a string.
    :type type: :obj:`str` or null

    :param message:
        A description of how *value* is invalid.
    :type message: :obj:`str` or null

    """
    def __init__(self, key, value, type=None, message=None):

        self.key = key
        self.value = value
        self.type = type
        self.message_ = message

        value_string = 'value {!r} for {!r}'.format(value, key)
        if type:
            value_string = '{} {}'.format(type, value_string)
        message_ = 'invalid {} in persistent settings'.format(value_string)
        if message:
            message_ += ': {}'.format(message)

        super(InvalidSettingsValue, self).__init__(message_)


class MalformedSettingsLocation(SettingsError):
    """A settings location is malformed.

    :param location:
        A settings location.
    :type location: :obj:`str` or null

    :param message:
        A description of how *location* is malformed.
    :type message: :obj:`str` or null

    """
    def __init__(self, location=None, message=None):

        self.location = location
        self.message_ = message

        message_ = 'malformed persistent settings'
        if location:
            message_ += ' at {!r}'.format(location)
        if message:
            message_ += ': {}'.format(message)

        super(MalformedSettingsLocation, self).__init__(message_)


class MissingRequiredSettingsValue(SettingsError):
    """A required value is missing.

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
    def __init__(self, key, type=None, locations=None):

        self.key = key
        self.type = type
        self.locations = locations

        required_value_string = 'value for {!r}'.format(key)
        if type:
            required_value_string = '{} {}'.format(type, required_value_string)
        message = 'missing required {} in persistent settings'\
                      .format(required_value_string)
        if locations:
            message += ' at {}'.format(locations)

        super(MissingRequiredSettingsValue, self).__init__(message)
