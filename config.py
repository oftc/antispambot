'''
The default configuration for tormodbot.

After running tormodbot for the first time, these options will be saved in
weechat's configuration system and to its plugins.conf file. **At this point,
editing this file will do nothing to change settings that exist in
plugins.conf**.  If you want to change your configuration, you should use
weechat's ``/set`` command. For example::

    /set plugins.python.tormodbot.serv "freenode"

If you want to add a configuration option, **It's value must be a string**.
Boolean values are interpreted as per
https://weechat.org/files/doc/stable/weechat_plugin_api.en.html#_config_string_to_boolean,
i.e.::

    1 if text is "true" ("on", "yes", "y", "true", "t", "1")
    0 if text is "false" ("off", "no", "n", "false", "f", "0")
'''

# ### Main configuration options ####
#: IRC server we're joining and on which all the channels are
SERV = 'oftc'
#: Channel/user in which to log messages in addition to the core window
LOG_CHAN = '#pastly-log'
#: Channel from which to take commands. If empty, only takes commands from
#: PM. We always take commands from PM.
CMD_CHAN = '#pastly-log'
#: Channels that we moderate
MOD_CHANS = '#pastly-test,#pastly-test2'
#: Nicks from which we will accept commands (as private messages or in the
#: command channel)
MASTERS = 'pastly'
#: No matter what the context, if we see a PRIVMSG or a NOTICE from these
#: nicks, we do nothing in response.
IGNORES = 'weasel'
#: The full nick!user@host string for nickserv
NICKSERV_USERSTR = 'NickServ!services@services.oftc.net'
#: The full nick!user@host string for chanserv
CHANSERV_USERSTR = 'ChanServ!services@services.oftc.net'
#: How many messages we can burst to the server. This must always be at
#: least 1. Setting this to 1 means you can't burst at all.
MSG_BURST = '5'
#: How many milliseconds must pass between our messages to the server in
#: steady state. To be safe, set this slightly higher than whatever the IRCd
#: actually requires.
MSG_RATE = '505'
#: Where the source code for this bot is hosted
CODE_URL = 'https://gitlab.torproject.org/pastly/weechat-tormodbot'

# ### liberaham.py configuration options ###
#: Whether to enable the :mod:`tmb_mod.liberaham` module
LIBERAHAM_ENABLED = 'on'

conf = {
    'serv': SERV,
    'log_chan': LOG_CHAN,
    'cmd_chan': CMD_CHAN,
    'mod_chans': MOD_CHANS,
    'masters': MASTERS,
    'ignores': IGNORES,
    'nickserv_userstr': NICKSERV_USERSTR,
    'chanserv_userstr': CHANSERV_USERSTR,
    'msg_burst': MSG_BURST,
    'msg_rate': MSG_RATE,
    'code_url': CODE_URL,
    'liberaham_enabled': LIBERAHAM_ENABLED,
}
