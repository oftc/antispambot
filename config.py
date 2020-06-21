'''
The default configuration for tormodbot.

After running tormodbot for the first time, these options will be saved in
weechat's configuration system and to its plugins.conf file. **At this point,
editing this file will do nothing to change settings that exist in
plugins.conf**.  If you want to change your configuration, you should use
weechat's /set command. For example::

    /set plugins.python.tormodbot.serv "freenode"

If you want to add a configuration option, **It's value must be a string**.
Boolean values are interpreted as per
https://weechat.org/files/doc/stable/weechat_plugin_api.en.html#_config_string_to_boolean,
i.e.::

    1 if text is "true" ("on", "yes", "y", "true", "t", "1")
    0 if text is "false" ("off", "no", "n", "false", "f", "0")
'''

#: Whether to enable the :mod:`tmb_mod.antiflood` module
ANTIFLOOD_ENABLED = 'off'
#: The maximum number of messages any one nick can send in a channel over
#: the course of :data:`ANTIFLOOD_MSG_LIMIT_SECONDS`
ANTIFLOOD_MSG_LIMIT = '10'
#: If a nick sends :data:`ANTIFLOOD_MSG_LIMIT` messages in this amount of time,
#: it is considered to be flooding
ANTIFLOOD_MSG_LIMIT_SECONDS = '30'
#: Comma-separated list of actions to take when a nick is detected as
#: flooding.
#:
#: Assume for example the flooding user is
#: pastly!~pastly@example.com. Possible actions are:
#:
#: - 'quiet-host': tell chanserv to +q *!*@example.com
#:
#: If you, the developer, want to add new actions, then add them to the
#: Action enum in :mod:`tmb_mod.antiflood`.
ANTIFLOOD_ACTIONS = 'quiet_host'

conf = {
    # IRC server we're joining and on which all the channels are
    'serv': 'oftc',
    # Channel/user in which to log messages in addition to the core window
    'log_chan': '#pastly-log',
    # Channel from which to take commands. If empty, only takes commands from
    # PM. We always take commands from PM.
    'cmd_chan': '#pastly-log',
    # Channels that we moderate
    'mod_chans': '#pastly-test,#pastly-test2',
    # Nicks from which we will accept commands (as private messages or in the
    # command channel)
    'masters': 'pastly',
    # No matter what the context, if we see a PRIVMSG or a NOTICE from these
    # nicks, we do nothing in response.
    'ignores': 'weasel',
    # The full nick!user@host string for nickserv
    'nickserv_userstr': 'NickServ!services@services.oftc.net',
    # The full nick!user@host string for chanserv
    'chanserv_userstr': 'ChanServ!services@services.oftc.net',
    # How many messages we can burst to the server. This must always be at
    # least 1. Setting this to 1 means you can't burst at all.
    'msg_burst': '5',
    # How many milliseconds must pass between our messages to the server in
    # steady state. To be safe, set this slightly higher than whatever the IRCd
    # actually requires.
    'msg_rate': '505',
    # The autovoice module can, if enabled:
    # - auto +v users with a matching n!u@h string
    # - auto +v users who have registered with a matching n!u@h string at least
    # X seconds ago
    'autovoice_enabled': 'off',
    # Comma-separated list of regex strings that, if one matches the n!u@h,
    # result in +v on the user
    'autovoice_regex_always': '.*!.*@pastly.netop.oftc.net',
    # Comma-separated list of regex strings that, if one matches the n!u@h AND
    # the nick is registered with nickserv at least X seconds ago, result in +v
    # on the user
    'autovoice_regex_registered': '.*',
    # How long ago the nick in question must have been registered with nickserv
    # in order for a positive regex match to result in the nick getting +v
    'autovoice_registered_seconds': '86400',
    'antiflood_enabled': ANTIFLOOD_ENABLED,
    'antiflood_msg_limit': ANTIFLOOD_MSG_LIMIT,
    'antiflood_msg_limit_seconds': ANTIFLOOD_MSG_LIMIT_SECONDS,
    'antiflood_actions': ANTIFLOOD_ACTIONS,
}
