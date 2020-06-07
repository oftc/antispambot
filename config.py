'''
This is the default configuration for tormodbot. After running tormodbot for
the first time, these options will be saved in weechat's configuration system
and to its plugins.conf file. AT THIS POINT EDITING THIS FILE WILL DO NOTHING
TO CHANGE YOUR CONFIG. If you want to change your configuration, you should use
weechat's /set command. For example:

    /set plugins.python.tormodbot.serv "freenode"
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
    # The full nick!user@host string for nickserv
    'nickserv_userstr': 'NickServ!services@services.oftc.net',
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
}
