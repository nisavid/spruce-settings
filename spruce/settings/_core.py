"""Application settings core"""

__copyright__ = "Copyright (C) 2014 Ivan D Vasin"
__docformat__ = "restructuredtext"

from collections import Mapping as _Mapping, namedtuple as _namedtuple
from contextlib import closing as _closing, contextmanager as _contextmanager
from datetime import datetime as _datetime, timedelta as _timedelta

from spruce.collections import odict as _odict

from . import _exc


class Settings(object):

    """Application settings

    Objects of this class maintain a current group.  By default, there is no
    current group, but one may be specified by one or more :meth:`ingroup`
    contexts.  For example, specifying a key :code:`'Book/Color'` is
    equivalent to specifying a key :code:`'Color'` in a :keyword:`with`
    block having the context :code:`ingroup('Book')`.  To resolve a relative
    name to an absolute name using the current group as the basis, use
    :meth:`absname`.

    The primary settings location is determined from the format, base scope,
    organization, application, and subsystem according to the mapping
    defined by successive calls to :meth:`set_path`.  The location fallback
    behavior can be configured via :attr:`base_scope_fallback` and
    :meth:`set_component_scope_fallback`.

    All settings, including fallback settings, are read in a single pass
    just before the first time any settings are accessed.  The settings are
    stored in an internal cache in memory.  All settings are read from and
    written to this cache.

    The cache is synchronized to persistent storage via :meth:`sync`.  The
    cache is synchronized automatically just before the first time any
    settings are accessed and just before the :class:`Settings` object is
    destroyed.  Also, if a cache lifespan is set, the cache expires when its
    age exceeds its lifespan; it is synchronized automatically just before
    the next access thereafter.

    This class is inspired by the `QSettings API`_.

    .. _`QSettings API`: http://qt-project.org/doc/qt-5/QSettings.html

    .. warning::
        The mutator methods (:meth:`clear`, :meth:`remove`, and
        :meth:`set_value`) are untested.

    :param str organization:
        The organization name used for storing and retrieving settings.

    :param application:
        The application name used for storing and retrieving settings.  If
        :obj:`None`, this object will only access organization-wide
        locations.
    :type application: :obj:`str` or null

    :param subsystem:
        The subsystem name used for storing and retrieving settings.  If
        :obj:`None`, this object will only access application- or
        organization-wide locations.
    :type subsystem: :obj:`str` or null

    :param str format:
        The name of the settings format.  This must be one of the formats
        previously registered with :meth:`register_format`.

    :param str base_scope:
        The base scope.  Either :code:`'user'` or :code:`'system'`.  If
        :code:`'user'`, then user-specific settings are searched first,
        followed by system-wide settings if :attr:`base_scope_fallback` is
        true.  If :code:`'system'`, then user-specific settings are ignored,
        and only system-wide settings are accessed.

    :raise ValueError:
        Raised if:

          * *application* is :obj:`None` and *subsystem* is not :obj:`None`,

          * *organization*, *application*, or *subsystem* is an empty
            string.

          * *format* has not been registered with :meth:`register_format`,
            or

          * *base_scope* is neither :code:`'user'` nor :code:`'system'`.

    """

    def __init__(self, organization, application=None, subsystem=None,
                 format='conf', base_scope='user'):

        if format not in self._formats:
            raise ValueError('unregistered format {!r}'.format(format))
        elif not organization:
            raise ValueError('invalid organization {!r}'.format(organization))
        if application is None:
            if subsystem is not None:
                raise ValueError('application is required if subsystem is'
                                  ' given')
        elif not application:
            raise ValueError('invalid application {!r}'.format(application))
        if subsystem is not None and not subsystem:
            raise ValueError('invalid subsystem {!r}'.format(subsystem))
        if base_scope not in ['user', 'system']:
            raise ValueError('invalid base_scope {!r}'.format(base_scope))

        self._application = application
        self._base_scope_fallback = True
        self._base_scope = base_scope
        self._cache_ = {}
        self._cache_creationtime = None
        self._cache_lifespan = _timedelta(seconds=6)
        self._component_fallback_enabled = \
            {('subsystem', 'application'): True,
             ('subsystem', 'organization'): True,
             ('application', 'organization'): True}
        self._defaults = self.__class__._Defaults(self)
        self._deleting = False
        self._format = format
        self._group = None
        self._isopen = False
        self._keys_in_primarylocation = set()
        self._keystowrite = set()
        self._locations = []
        self._organization = organization
        self._previous_groups = []
        self._subsystem = subsystem

        if subsystem is not None:
            self._component_scope = 'subsystem'
        elif application is not None:
            self._component_scope = 'application'
        else:
            self._component_scope = 'organization'

    def __del__(self):
        self._deleting = True
        self.close()

    def absname(self, name):
        """The absolute name of a group or key

        :param str name:
            The name of a group or key.

        :return:
            The absolute name created by resolving the given *name* relative to
            the current :attr:`group`.
        :rtype: :obj:`str`

        """
        if not self.group:
            return name
        else:
            return self.group + '/' + name

    @property
    def all_groups(self):
        """
        An iterable over all groups, including subgroups, that can be read by
        this settings object in the current :attr:`group`

        .. note::
            This includes the groups provided by :attr:`defaults`.

        .. seealso::
            :attr:`all_keys`, :attr:`child_groups`, and :attr:`child_keys`

        :type: ~[:obj:`str`]

        """
        groups_seen = set()
        for key in self.all_keys:
            group, _, _ = key.rpartition('/')
            if group and group not in groups_seen:
                groups_seen.add(group)
                yield group

    @property
    def all_keys(self):
        """
        An iterable over all keys, including subkeys, that can be read by this
        settings object in the current :attr:`group`

        .. note::
            This includes the keys provided by :attr:`defaults`.

        .. seealso::
            :attr:`all_groups`, :attr:`child_groups`, and :attr:`child_keys`

        :type: ~[:obj:`str`]

        """
        return (self._descendant_key_name(key)
                for key in filter(self._is_descendant_key, self._cache.keys()))

    @property
    def application(self):
        """The application name used for storing and retrieving settings

        .. seealso::
            :attr:`base_scope`, :attr:`component_scope`, :attr:`format`,
            :attr:`organization`, and :attr:`subsystem`

        :type: :obj:`str`

        """
        return self._application

    @property
    def base_scope(self):
        """The base scope

        This is either :code:`'user'` or :code:`'system'`.

        :type: :obj:`str`

        """
        return self._base_scope

    @property
    def base_scope_fallback(self):
        """Whether fallback is enabled between the base scopes

        If :obj:`True`, any key not found in the current user's settings will
        be searched for in the system-wide settings.

        By default, fallback is enabled.

        .. seealso::
            :meth:`component_scope_fallback` and
            :meth:`set_component_scope_fallback`

        :type: :obj:`bool`

        """
        return self._base_scope_fallback

    @base_scope_fallback.setter
    def base_scope_fallback(self, enabled):
        self._base_scope_fallback = enabled

    def boolvalue(self, key, default=None, required=False):

        """
        The value of the setting identified by some key, converted to
        a :obj:`bool`

        If the setting is not found, then

          * if *required* is false, *default* is returned.

          * if *required* is true, a
            :exc:`~spruce.settings._exc.MissingRequiredSettingsValue` is
            raised.

        The acceptable case-insensitive representations of boolean values are

            true values
                ``true``, ``1``, ``yes``, ``on``

            false values
                ``false``, ``0``, ``no``, ``off``

        .. note::
            This is a convenience method that calls :meth:`value`.

        .. seealso::
            :meth:`contains`, :meth:`remove`, :meth:`set_value`, and
            :meth:`value`

        :param str key:
            A settings key.

        :param default:
            A default value.
        :type default: :obj:`bool` or null

        :param bool required:
            Whether the setting is required.

        :rtype: :obj:`bool` or null

        :raise spruce.settings.InvalidSettingsValue:
            Raised if the value is not one of the acceptable boolean
            representations.

        :raise spruce.settings.MissingRequiredSettingsValue:
            Raised if *required* is true and the setting is not found.

        """

        TYPE = 'boolean'

        value = self.value(key, default=None, required=False)

        if value is None:
            if required:
                raise _exc.MissingRequiredSettingsValue\
                       (self.absname(key), type=TYPE, locations=self.locations)
            else:
                return default

        if value.lower() in ['true', '1', 'yes', 'on']:
            return True
        if value.lower() in ['false', '0', 'no', 'off']:
            return False

        raise _exc.InvalidSettingsValue(self.absname(key), value, type=TYPE)

    @property
    def cache_lifespan(self):
        """The maximum age of the internal cache

        This is the amount of time after the cache's creation after which a
        subsequent access will automatically be preceded by a synchronization.

        If this is :obj:`None`, automatic synchronization is turned off.

        The default cache lifespan is 6 seconds.

        :type: :class:`datetime.timedelta` or null

        """
        return self._cache_lifespan

    @cache_lifespan.setter
    def cache_lifespan(self, lifespan):
        if lifespan is not None \
               and not isinstance(lifespan, _timedelta):
            raise TypeError('invalid cache lifespan type {}'
                             .format(lifespan.__class__))
        self._cache_lifespan = lifespan

    @property
    def child_groups(self):
        """
        An iterable over the non-empty top-level groups in the current group

        It is possible to navigate the entire setting hierarchy using
        :attr:`child_keys` and :attr:`child_groups` recursively.

        .. note::
            This includes the groups provided by :attr:`defaults`.

        .. seealso:: :attr:`all_groups` and :attr:`child_keys`

        :type: ~[:obj:`str`]

        """
        return {self._child_group_name(key) for key in self._cache.keys()
                if self._in_child_group(key)}

    @property
    def child_keys(self):
        """An iterable over the top-level keys in the current group

        It is possible to navigate the entire setting hierarchy using
        :attr:`child_keys` and :attr:`child_groups` recursively.

        .. note::
            This includes the groups provided by :attr:`defaults`.

        .. seealso:: :attr:`all_keys` and :attr:`child_groups`

        :type: ~[:obj:`str`]

        """
        return (self._child_key_name(key)
                for key in filter(self._is_child_key, self._cache.keys()))

    def clear(self):
        """Remove all entries in the primary location

        Entries in fallback locations are not removed.

        To remove only the entries in the current group, use :code:`remove('')`
        instead.

        .. warning:: **Bug:**
            Writing settings in the conf format is not yet implemented, so any
            synchronization after calling this will raise a
            :exc:`~exceptions.NotImplementedError`.

        .. note::
            This removes entries that were added after the last
            synchronization.

        .. seealso:: :meth:`remove`

        """
        self._keystowrite.clear()
        self._keystowrite.add('')
        self._cache = {'': None}

    def close(self):
        """Close this settings object

        This triggers a call to :meth:`sync`.

        """
        if self._isopen:
            self.sync()

    @property
    def component_scope(self):
        """The component scope

        This is one of :code:`'organization'`, :code:`'application'`, or
        :code:`'subsystem'`.

        :type: :obj:`str`

        """
        return self._component_scope

    def component_scope_fallback(self, lesser_component, greater_component):

        """Whether fallback is enabled between two component scopes

        If :obj:`True`, any key not found in *lesser_component* will be
        searched for in *greater_component*.

        By default, fallback is enabled for all valid combinations of component
        scopes.

        .. seealso:: :meth:`set_component_scope_fallback`

        :param str lesser_component:
            The lesser component scope.  Either :code:`'application'` or
            :code:`'subsystem'`.

        :param str greater_component:
            The greater component scope.  Either :code:`'organization'` or
            :code:`'application'`.

        :rtype: :obj:`bool`

        :raise ValueError:
            Raised if:

              * *lesser_component* is neither :code:`'application'` nor
                :code:`'subsystem'`.

              * *greater_component* is neither :code:`'organization'` nor
                :code:`'application'`.

              * *lesser_component* refers to a component scope that is
                greater than or equal to that of *greater_component*.

        """

        if lesser_component not in ('application', 'subsystem'):
            raise ValueError('invalid lesser component scope {!r}'
                              .format(lesser_component))
        if greater_component not in ('organization', 'application'):
            raise ValueError('invalid greater component scope {!r}'
                              .format(greater_component))
        if lesser_component == greater_component \
               or greater_component == 'subsystem' \
               or lesser_component == 'organization':
            raise ValueError('the lesser component scope must be less than the'
                              ' greater component scope (lesser: {}; greater:'
                              ' {})'
                              .format(lesser_component, greater_component))

        return self._component_fallback_enabled[(lesser_component,
                                                 greater_component)]

    def contains(self, key):
        """
        Whether there exists a setting identified by some key in the current
        group

        .. seealso:: :meth:`set_value` and :meth:`value`

        :param str key:
            A settings key.

        :rtype: :obj:`bool`

        """
        return key in self._cache

    def copy(self):

        """A copy of these settings

        :rtype: :class:`Settings`

        """

        settings = Settings(organization=self.organization,
                            application=self.application,
                            subsystem=self.subsystem,
                            format=self.format,
                            base_scope=self.base_scope)
        settings.defaults = self.defaults
        settings.cache_lifespan = self.cache_lifespan

        settings.base_scope_fallback = self.base_scope_fallback
        for pair in (('subsystem', 'application'),
                     ('subsystem', 'organization'),
                     ('application', 'organization')):
            settings.set_component_scope_fallback\
             (pair[0], pair[1], self.component_scope_fallback(*pair))

        settings._group = self.group
        settings._previous_groups = self._previous_groups

        settings._keystowrite = self._keystowrite
        settings._keys_in_primarylocation = self._keys_in_primarylocation

        return settings

    @property
    def defaults(self):
        """A mapping of default settings

        This may be a mapping of keys to values, or it may be a mapping of
        groups to subgroups to keys to values, or any combination thereof.  A
        consequence of this flexibility is that it is impossible to specify a
        default value inside this mapping that is itself a mapping object.

        The keys in this mapping are absolute names.  To create new items using
        only relative key names, pass them through :meth:`absname`.

        When reading settings with :meth:`value` or one of its convenience
        methods, if a setting key is not found in any of the applicable
        locations, its value is retrieved from this mapping if it exists.

        :type: {:obj:`str`: :obj:`object`}

        """
        return self._defaults

    @defaults.setter
    def defaults(self, defaults):

        if not isinstance(defaults, _Mapping):
            raise TypeError('invalid defaults mapping type {}'
                             .format(defaults.__class__.__name__))

        def flatten_defaults(parent_group, defaults):
            defaults_new = self.__class__._Defaults(self)
            for key, value in defaults.iteritems():
                if isinstance(value, _Mapping):
                    group = None
                    if parent_group is None:
                        group = key
                    else:
                        group = parent_group + '/' + key

                    defaults_new.update(flatten_defaults(group, value))
                else:
                    if parent_group is None:
                        defaults_new[key] = value
                    else:
                        defaults_new[parent_group + '/' + key] = value
            return defaults_new

        self._defaults = \
            flatten_defaults(None, defaults if defaults is not None else {})

    def floatvalue(self, key, default=None, required=False):

        """
        The value of the setting identified by some key, converted to a
        :obj:`float`

        If the setting is not found, then

          * if *required* is false, *default* is returned.

          * if *required* is true, a
            :exc:`~spruce.settings._exc.MissingRequiredSettingsValue` is
            raised.

        .. note::
            This is a convenience method that calls :meth:`value`.

        .. seealso::
            :meth:`contains`, :meth:`remove`, :meth:`set_value`, and
            :meth:`value`

        :param str key:
            A settings key.

        :param default:
            A default value.
        :type default: :obj:`float` or null

        :param bool required:
            Whether the setting is required.

        :rtype: :obj:`float` or null

        :raise spruce.settings.InvalidSettingsValue:
            Raised if the value cannot be converted to a :obj:`float`.

        :raise spruce.settings.MissingRequiredSettingsValue:
            Raised if *required* is true and the setting is not found.

        """

        TYPE = 'floating point'

        value = self.value(key, default=None, required=False)

        if value is None:
            if required:
                raise _exc.MissingRequiredSettingsValue\
                       (self.absname(key), type=TYPE, locations=self.locations)
            else:
                return default

        try:
            return float(value)
        except ValueError as exc:
            raise _exc.InvalidSettingsValue(self.absname(key), value,
                                            type=TYPE, message=str(exc))

    @property
    def format(self):
        """The format used for storing and retrieving settings

        .. seealso::
            :attr:`application`, :attr:`base_scope`, :attr:`component_scope`,
            :attr:`organization`, and :attr:`subsystem`

        :type: :obj:`str`

        """
        return self._format

    @property
    def group(self):
        """The current group

        This is an empty string if there is no current group.

        The current group is set by a :keyword:`with` context created by
        :meth:`ingroup`.  Within such a context, the current group is prepended
        to all keys specified to this settings object.  Also, the query methods
        :attr:`child_groups`, :attr:`child_keys`, and :attr:`all_groups` are
        based on the current group.

        By default, there is no current group.

        .. seealso:: :meth:`ingroup`

        :type: :obj:`str`

        """
        return self._group if self._group is not None else ''

    @_contextmanager
    def ingroup(self, group):

        """A context with a new current group

        Upon entering this context, the :attr:`current group <group>` is set to
        the given *group*.  Upon exiting this context, the current group of the
        calling context is restored.

        .. seealso:: :attr:`group`

        :param group:
            The new current group.  This can be nested.  If null, the current
            group is unchanged.
        :type group: :obj:`str` or null

        :return:
            A context in which the current group is the given *group*,
            evaluated relative to the current group in the calling context.
        :rtype: context

        """

        if group:
            if not self.group:
                self._group = group
            else:
                self._previous_groups.append(self.group)
                self._group += '/' + group

        yield

        if group:
            if self._previous_groups:
                self._group = self._previous_groups.pop()
            else:
                self._group = None

    def intvalue(self, key, default=None, required=False):

        """
        The value of the setting identified by some key, converted to an
        :obj:`int`

        If the setting is not found, then

          * if *required* is false, *default* is returned.

          * if *required* is true, a
            :exc:`~spruce.settings._exc.MissingRequiredSettingsValue` is
            raised.

        .. note::
            This is a convenience method that calls :meth:`value`.

        .. seealso::
            :meth:`contains`, :meth:`remove`, :meth:`set_value`, and
            :meth:`value`

        :param str key:
            A settings key.

        :param default:
            A default value.
        :type default: :obj:`int` or null

        :param bool required:
            Whether the setting is required.

        :rtype: :obj:`int` or null

        :raise spruce.settings.InvalidSettingsValue:
            Raised if the value cannot be converted to an :obj:`int`.

        :raise spruce.settings.MissingRequiredSettingsValue:
            Raised if *required* is true and the setting is not found.

        """

        TYPE = 'integer'

        value = self.value(key, default=None, required=False)

        if value is None:
            if required:
                raise _exc.MissingRequiredSettingsValue\
                       (self.absname(key), type=TYPE, locations=self.locations)
            else:
                return default

        try:
            return int(value)
        except ValueError as exc:
            raise _exc.InvalidSettingsValue(self.absname(key), value,
                                            type=TYPE, message=str(exc))

    def listvalue(self, key, default=None, required=False, sep=','):

        """
        The value of the setting identified by some key, converted to a
        :obj:`list`

        If the setting is not found, then

          * if *required* is false, *default* is returned.

          * if *required* is true, a
            :exc:`~spruce.settings._exc.MissingRequiredSettingsValue` is
            raised.

        The given separator *sep* is used to identify the items of the list.
        The list may optionally be surrounded by square, round, or curly
        brackets.

        .. warning::
            An empty list value (an empty value or one of {``[]``, ``()``,
            ``{}``}) is treated as an empty list.  There is no way to specify a
            value that is a singleton list that contains an empty string.

        .. note::
            This is a convenience method that calls :meth:`value`.

        .. seealso::
            :meth:`contains`, :meth:`remove`, :meth:`set_value`, and
            :meth:`value`

        :param str key:
            A settings key.

        :param default:
            A default value.
        :type default: [:obj:`str`] or null

        :param bool required:
            Whether the setting is required.

        :param str sep:
            The separator between list items in the underlying string value.

        :rtype: [:obj:`str`] or null

        :raise spruce.settings.MissingRequiredSettingsValue:
            Raised if *required* is true and the setting is not found.

        """

        TYPE = 'list'

        value = self.value(key, default=None, required=False)

        if value is None:
            if required:
                raise _exc.MissingRequiredSettingsValue\
                       (self.absname(key), type=TYPE, locations=self.locations)
            else:
                return default

        value = value.strip()

        if len(value) == 0:
            return []

        if len(value) >= 2:
            if value[0] == '[' and value[-1] == ']' \
                   or value[0] == '(' and value[-1] == ')' \
                   or value[0] == '{' and value[-1] == '}':
                value = value[1:-1]

        if sep not in value:
            if value:
                return [value]
            else:
                return []

        list_ = value.split(sep)

        for index, item in enumerate(list_):
            list_[index] = item.strip()

        return list_

    @property
    def locations(self):
        """The locations that were used in the last :meth:`sync`

        These are determined by :attr:`base_scope`, :attr:`component_scope`,
        :attr:`organization`, :attr:`application`, and :attr:`subsystem`
        according to the paths configured with :meth:`set_path` for the current
        :attr:`format`.

        The locations are returned in the order in which they are inspected for
        settings, highest precedence first.

        .. seealso:: :meth:`set_path`

        :type: ~[:obj:`str`]

        """
        return self._locations

    def open(self):
        """A context in which this settings object is open for access

        Upon entering this context, :meth:`sync` is called.  Upon exiting this
        context, :meth:`close` is called.

        :rtype: context

        """
        self._isopen = True
        self.sync()
        return _closing(self)

    @property
    def organization(self):
        """The organization name used for storing and retrieving settings

        .. seealso::
            :attr:`application`, :attr:`base_scope`, :attr:`component_scope`,
            :attr:`format`, and :attr:`subsystem`

        :type: :obj:`str`

        """
        return self._organization

    @property
    def primary_path(self):
        """A path to the primary location

        .. seealso:: :attr:`format` and :attr:`writable`

        :type: :obj:`str`

        """
        return self._paths[self.format][self.base_scope][self.component_scope]

    def remove(self, key):
        """
        Remove the setting identified by some key and all of its subkeys

        Entries in fallback locations are not removed.

        If *key* is an empty string, all keys in the current group are removed.

        .. warning:: **Bug:**
            Writing settings in the conf format is not yet implemented, so any
            synchronization after calling this will raise a
            :exc:`~exceptions.NotImplementedError`.

        .. seealso:: :meth:`contains`, :meth:`set_value`, and :meth:`value`

        :param str key:
            A settings key or an empty string.

        """
        self._cache[key] = None
        self._keystowrite.add(key)

    def set_component_scope_fallback(self, lesser_component, greater_component,
                                     enabled):

        """Set whether fallback is enabled between two component scopes

        If *enabled* is true, any key not found in *lesser_component* will
        be searched for in *greater_component*.

        By default, fallback is enabled for all combinations of component
        scopes.

        .. seealso:: :meth:`component_scope_fallback`

        :param str lesser_component:
            The lesser component scope.  Either :code:`'application'` or
            :code:`'subsystem'`.

        :param str greater_component:
            The greater component scope.  Either :code:`'organization'` or
            :code:`'application'`.

        :param bool enabled:
            Whether fallback should be enabled from *lesser_component* to
            *greater_component*.

        :raise ValueError:
            Raised if:

              * *lesser_component* is neither :code:`'application'` nor
                :code:`'subsystem'`.

              * *greater_component* is neither :code:`'organization'` nor
                :code:`'application'`.

              * *lesser_component* refers to a component scope that is
                greater than or equal to that of *greater_component*.

        """

        if lesser_component not in ('application', 'subsystem'):
            raise ValueError('invalid lesser component scope {!r}'
                              .format(lesser_component))
        if greater_component not in ('organization', 'application'):
            raise ValueError('invalid greater component scope {!r}'
                              .format(greater_component))
        if lesser_component == greater_component \
               or greater_component == 'subsystem' \
               or lesser_component == 'organization':
            raise ValueError('the lesser component scope must be less than the'
                              ' greater component scope (lesser: {}; greater:'
                              ' {})'
                              .format(lesser_component, greater_component))

        self._component_fallback_enabled[(lesser_component,
                                          greater_component)] = \
            enabled

    def set_value(self, key, value):

        """Assign a value to the setting identified by some key

        If *value* is not a string object, then :samp:`repr({value})` is the
        actual value assigned.

        .. warning:: **Bug:**
            Writing settings in the conf format is not yet implemented, so any
            synchronization after calling this will raise a
            :exc:`~exceptions.NotImplementedError`.

        .. note::
            :samp:`set_value({key}, None)` has the same effect as
            :samp:`remove({key})`.

        .. note::
            Some formats, such as conf, assign a default group to settings that
            do not belong to a group.

        .. seealso:: :meth:`contains`, :meth:`remove`, and :meth:`value`

        """

        abskey = self.absname(key)

        if isinstance(value, str) or isinstance(value, unicode):
            self._cache[abskey] = value
        else:
            self._cache[abskey] = repr(value)

        self._keys_in_primarylocation.add(abskey)
        self._keystowrite.add(abskey)

    @property
    def subsystem(self):
        """The subsystem name used for storing and retrieving settings

        .. seealso::
            :attr:`application`, :attr:`base_scope`, :attr:`component_scope`,
            :attr:`format`, and :attr:`organization`

        :type: :obj:`str`

        """
        return self._subsystem

    def sync(self):

        """
        Write any unsaved changes to persistent storage and reload any settings
        that have been changed externally

        This function is called by :meth:`open` and :meth:`close`.

        .. warning:: **Bug:**
            Writing settings in the conf format is not yet implemented, so
            calling this after calling one of the mutator methods will raise a
            :exc:`~exceptions.NotImplementedError`.

        .. note:: **TODO:**
            conflict detection, resolution, exceptions

        :raise EnvironmentError:
            Raised if an error is encountered outside the Python system while
            reading or writing settings to persistent storage.

        :raise spruce.settings.MalformedSettingsLocation:
            Raised if a malformed settings location is encountered.

        """

        format_ = self._formats[self.format]
        read = format_.read_func
        write = format_.write_func

        # determine all applicable locations
        locations = []
        locations.append(self._paths[self.format]
                                    [self.base_scope]
                                    [self.component_scope])
        for greater_component \
                in self._greater_components(self.component_scope):
            if self.component_scope_fallback(self.component_scope,
                                             greater_component):
                locations.append(self._paths[self.format]
                                            [self.base_scope]
                                            [greater_component])
        if self.base_scope == 'user' and self.base_scope_fallback:
            locations.append(self._paths[self.format]
                                        ['system']
                                        [self.component_scope])
            for greater_component \
                    in self._greater_components(self.component_scope):
                if self.component_scope_fallback(self.component_scope,
                                                 greater_component):
                    locations.append(self._paths[self.format]
                                                ['system']
                                                [greater_component])
        for index, location in enumerate(locations):
            location = location.replace('{organization}', self.organization)
            if self.application is not None:
                location = location.replace('{application}', self.application)
            if self.subsystem is not None:
                location = location.replace('{subsystem}', self.subsystem)
            location = location.replace('{extension}', format_.extension)
            locations[index] = location
        self._locations = locations

        # actuate :meth:`clear`
        if '' in self._keystowrite:
            assert '' in self._cache_
            assert self._cache_[''] is None

            write(self.locations[0], {'': None})

            self._keystowrite.remove('')
            del self._cache_['']

        # actuate :meth:`set_value` and :meth:`remove`
        try:
            write(self.locations[0],
                  _odict((key, value)
                         for key, value in self._cache_.iteritems()
                         if key in self._keystowrite))
        except _exc.MalformedSettingsLocation as exc:
            raise _exc.MalformedSettingsLocation(self.locations[0],
                                                 message=exc.message_)

        # update :attr:`_cache_` and :attr:`_keys_in_primarylocation`
        if not self._deleting:
            self._cache_.clear()
            self._cache_.update({key: str(value)
                                 for key, value in self.defaults.items()})
            for index, location in enumerate(reversed(self.locations)):
                try:
                    location_settings = read(location, [''])
                except _exc.MalformedSettingsLocation as exc:
                    raise _exc.MalformedSettingsLocation(location,
                                                         message=exc.message_)
                self._cache_.update(location_settings)

                if index == len(self.locations) - 1:
                    self._keys_in_primarylocation = \
                        set(location_settings.keys())
            self._cache_creationtime = _datetime.now()

    def value(self, key, default=None, required=False):

        """
        The value of the setting identified by some key in the current
        group

        If the setting is not found, then

          * if *required* is false, *default* is returned.

          * if *required* is true, a
            :exc:`~spruce.settings._exc.MissingRequiredSettingsValue` is
            raised.

        If the setting is blank, an empty string is returned.

        .. seealso::
            :meth:`boolvalue`, :meth:`contains`, :meth:`floatvalue`,
            :meth:`intvalue`, :meth:`remove`, and :meth:`set_value`

        :param str key:
            A settings key.

        :param default:
            A default value.
        :type default: :obj:`str` or null

        :param bool required:
            Whether the setting is required.

        :rtype: :obj:`str` or null

        :raise spruce.settings.MissingRequiredSettingsValue:
            Raised if *required* is true and the setting is not found.

        """

        abskey = self.absname(key)

        if abskey in self._cache and self._cache[abskey] is not None:
            return self._cache[abskey]
        else:
            if required:
                raise _exc.MissingRequiredSettingsValue(abskey,
                                                        locations=
                                                            self.locations)
            else:
                return default

    @property
    def writable(self):
        """Whether settings can be written by this settings object

        This may be :obj:`False` if, for example, the primary location is
        read-only.

        .. note::
            Writing settings in the conf format is not yet implemented, so this
            is always :obj:`False`.

        :type: :obj:`bool`

        """
        # FIXME
        return False

    @classmethod
    def register_format(cls, name, extension, read_func, write_func):
        """Register a storage format

        :param str name:
            A string that is unique among settings formats.

        :param str extension:
            A valid file extension, including a leading period if applicable.
            May be an empty string.

        :param read_func:
            A function with the following signature:

                :samp:`read_func({file}, {keys})` -> :samp:`{settings}`

                wherein:

                  * *file* is a file-like object.  It can be assumed that
                    *file* is open for reading.

                  * *keys* is a list of requested settings keys.  A value of
                    :code:`['']` indicates that all keys are requested.

                  * *settings* is a mapping from *keys* to the values read from
                    *file*.  If a setting is blank, its key should be mapped to
                    an empty string.  If a setting is omitted, its key should
                    be mapped to :obj:`None`.

                  * :exc:`~exceptions.EnvironmentError` is raised if an error
                    is encountered outside the Python system.

                  * :exc:`~spruce.settings._exc.MalformedSettingsLocation` is
                    raised if a malformed location is encountered.
        :type read_func: :obj:`file`, [:obj:`str`] -> {:obj:`str`: :obj:`str`}

        :param write_func:
            A function with the following signature:

                :samp:`write_func({file}, {settings})` ->

                wherein:

                  * *file* is a file-like object.  It can be assumed that
                    *file* is open for reading.

                  * *settings* is a mapping from settings keys to the values
                    that should be assigned to them.  If a setting should be
                    blank, its key should be mapped to an empty string.  If a
                    setting should be omitted, its key should be mapped to
                    :obj:`None`.  The special mapping :code:`{'': None}`
                    indicates that all settings should be cleared.

                  * :exc:`~exceptions.EnvironmentError` is raised if an error
                    is encountered outside the Python system.

                  * :exc:`~spruce.settings._exc.MalformedSettingsLocation` is
                    raised if a malformed location is encountered.
        :type write_func: :obj:`file`, {:obj:`str`: :obj:`str`} ->

        .. seealso:: :meth:`set_path`

        """
        cls._formats[name] = \
            cls._Format(name=name, extension=extension, read_func=read_func,
                        write_func=write_func)

    @classmethod
    def set_path(cls, format, base_scope, component_scope, path):

        """Set the path used for storing settings in some format and scope

        When resolving the path, the strings ``{organization}``,
        ``{application}``, ``{subsystem}``, and ``{extension}`` are substituted
        respectively with the organization name, application name, subsystem
        name, and file extension.

        The default paths are given in the following table.

        +--------+------------+-----------------+------------------------------------------------------------------+
        | Format | Base Scope | Component Scope | Path                                                             |
        +========+============+=================+==================================================================+
        | conf   | user       | organization    | :file:`~/.{organization}/{organization}{extension}`              |
        |        |            +-----------------+------------------------------------------------------------------+
        |        |            | application     | :file:`~/.{organization}/{application}{extension}`               |
        |        |            +-----------------+------------------------------------------------------------------+
        |        |            | subsystem       | :file:`~/.{organization}/{application}/{subsystem}{extension}`   |
        |        +------------+-----------------+------------------------------------------------------------------+
        |        | system     | organization    | :file:`/etc/{organization}/{organization}{extension}`            |
        |        |            +-----------------+------------------------------------------------------------------+
        |        |            | application     | :file:`/etc/{organization}/{application}{extension}`             |
        |        |            +-----------------+------------------------------------------------------------------+
        |        |            | subsystem       | :file:`/etc/{organization}/{application}/{subsystem}{extension}` |
        +--------+------------+-----------------+------------------------------------------------------------------+

        .. note::
            The substituted file extension includes a leading period, if
            applicable.

        .. seealso:: :meth:`register_format`

        :param str format:
            A settings format.

        :param str base_scope:
            A base scope.  Either :code:`'user'` or :code:`'system'`.

        :param str component_scope:
            A component scope.  One of :code:`'organization'`,
            :code:`'application'`, or :code:`'subsystem'`.

        :param str path:
            A file path.

        """

        if format not in cls._paths:
            cls._paths[format] = {}
        if base_scope not in cls._paths[format]:
            cls._paths[format][base_scope] = {}

        cls._paths[format][base_scope][component_scope] = path

    @property
    def _cache(self):
        if self._cache_lifespan is not None:
            min_creation_time = _datetime.now() - self._cache_lifespan
            if self._cache_creationtime is None \
                   or self._cache_creationtime < min_creation_time:
                self.sync()
        return self._cache_

    def _child_group_name(self, key):
        relative_key = None
        if not self.group:
            relative_key = key
        else:
            relative_key = key[(len(self.group) + 1):]
        return relative_key[:relative_key.index('/')]

    def _child_key_name(self, key):
        if not self.group:
            return key
        else:
            return key[(len(self.group) + 1):]

    def _descendant_key_name(self, key):
        if not self.group:
            return key
        else:
            return key[(len(self.group) + 1):]

    def _greater_components(self, component):
        if component == 'organization':
            return []
        greater_components = []
        if component == 'subsystem':
            greater_components.append('application')
        greater_components.append('organization')
        return greater_components

    def _in_child_group(self, key):
        if not self.group:
            return True
        else:
            return key.startswith(self.group + '/') \
                   and '/' in key[(len(self.group) + 1):]

    def _is_child_key(self, key):
        if not self.group:
            return '/' not in key
        else:
            return key.startswith(self.group + '/') \
                   and '/' not in key[(len(self.group) + 1):]

    def _is_descendant_key(self, key):
        return not self.group or key.startswith(self.group + '/')

    class _Defaults(dict):

        def __init__(self, settings):
            self._settings = settings

        def __setitem__(self, name, value):
            super(Settings._Defaults, self).__setitem__(name, value)
            self._settings.sync()

    class _Format(_namedtuple('_Format',
                              ('name', 'extension', 'read_func',
                               'write_func'))):
        pass

    _formats = {}

    _paths = {}
