'''
This is the default configuration for tormodbot. After running tormodbot for
the first time, these options will be saved in weechat's configuration system
and to its plugins.conf file. AT THIS POINT EDITING THIS FILE WILL DO NOTHING
TO CHANGE YOUR CONFIG. If you want to change your configuration, you should use
weechat's /set command. For example:

    /set plugins.python.tormodbot.serv "freenode"

If you want to add a configuration option, IT'S VALUE MUST BE A STRING. Boolean
values are interpreted as per
https://weechat.org/files/doc/stable/weechat_plugin_api.en.html#_config_string_to_boolean,
i.e.:
    - 1 if text is "true" ("on", "yes", "y", "true", "t", "1")
    - 0 if text is "false" ("off", "no", "n", "false", "f", "0")
'''
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
    # The antiflood modlue can, if enabled:
    # - detect slow floods where a nick slowly spams many messages
    'antiflood_enabled': 'off',
    # The maximum number of messages any one nick can send in a channel over
    # the course of msg_limit_seconds
    'antiflood_msg_limit': '10',
    # If a nick sends msg_limit messages in this amount of time, it is
    # considered to be flooding
    'antiflood_msg_limit_seconds': '30',
    # Comma-separated list of actions to take when a nick is detected as
    # flooding. Assume for example the flooding user is
    # pastly!~pastly@example.com. Possible actions are:
    # - 'quiet-host': tell chanserv to +q *!*@example.com
    # If you, the developer, want to add new actions, then add them to the
    # Action enum in antiflood.py
    'antiflood_actions': 'quiet_host',
}
