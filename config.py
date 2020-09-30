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

# ### antiflood.py configuration options ####
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
#: - 'quiet_host': tell chanserv to +q \*!\*@example.com
#:
#: If you, the developer, want to add new actions, then add them to the
#: Action enum in :mod:`tmb_mod.antiflood`.
ANTIFLOOD_ACTIONS = 'quiet_host'

# ### autovoice.py configuration options ####
#: Whether to enable the :mod:`tmb_mod.autovoice` module
AUTOVOICE_ENABLED = 'off'
#: How long ago the nick in question must have been registered with nickserv
#: in order for a positive regex match to result in the nick getting +v
AUTOVOICE_REGISTERED_SECONDS = '86400'
#: Comma-separated list of regex strings that, if one matches the ``n!u@h``
#: **and** the nick registered with nickserv at least
#: :data:`AUTOVOICE_REGISTERED_SECONDS` ago, result in +v on the user
AUTOVOICE_REGEX_REGISTERED = '.*'
#: Comma-separated list of regex strings that, if one matches the ``n!u@h``,
#: results in +v on the user
AUTOVOICE_REGEX_ALWAYS = '.*!.*@pastly.netop.oftc.net'

# ### badwords.py configuration options ####
#: Whether to enable the :mod:`tmb_mod.badwords` module
BADWORDS_ENABLED = 'on'
#: Comma-separated list of bad words
BADWORDS_BADWORDS = ''
#: Comma-separated list of actions to take when a nick is detected as having
#: said a bad word.
#:
#: Assume for example user is
#: pastly!~pastly@example.com. Possible actions are:
#:
#: - 'quiet_nick': tell chanserv to +q pastly!\*@\*
#:
#: If you, the developer, want to add new actions, then add them to the
#: Action enum in :mod:`tmb_mod.badwords`.
BADWORDS_ACTIONS = 'quiet_nick'

# ### hello.py configuration options ####
#: Whether to enable the :mod:`tmb_mod.hello` module
HELLO_ENABLED = 'off'
#: If a message is longer than this, assume it is not a "hello?" message
HELLO_MSG_MAX_LEN = '20'
#: Comma-separated list of strings that, if found in a message, indicate the
#: message is a "hello?" message
HELLO_HELLO_WORDS = 'hi,hello,test,help,noob,guys,anyone'
#: After this many joins in a channel, a user can send a "hello?" message
#: without us sending an automated response
HELLO_NEW_JOINS = '100'
#: After this many messages in a channel, a user can send a "hello?" message
#: without us sending an automated response
HELLO_NEW_MSGS = '2'
#: If enabled, **anyone** in a moderated chan with a configured automated
#: response can say '!hello' and get the response for that channel printed
HELLO_MANUAL_ENABLED = 'on'
#: The amount of time, in seconds, that must pass before we will send our
#: autoreponse in a a specific channel again
HELLO_INTERVAL = '60'

# ### faq.py configuration options ###
#: Whether to enable the :mod:`tmb_mod.faq` module
FAQ_ENABLED = 'on'
#: How many FAQ responses we can burst to a specific channel without waiting
FAQ_BURST = '3'
#: How long, in milliseconds, we must wait between FAQ responses in a specific
#: channel
FAQ_RATE = '5000'
#: How long, in seconds, we must wait between given *the same* FAQ response in
#: the same channel.
FAQ_RECENT = '120'

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
    'autovoice_enabled': AUTOVOICE_ENABLED,
    'autovoice_regex_always': AUTOVOICE_REGEX_ALWAYS,
    'autovoice_regex_registered': AUTOVOICE_REGEX_REGISTERED,
    'autovoice_registered_seconds': AUTOVOICE_REGISTERED_SECONDS,
    'antiflood_enabled': ANTIFLOOD_ENABLED,
    'antiflood_msg_limit': ANTIFLOOD_MSG_LIMIT,
    'antiflood_msg_limit_seconds': ANTIFLOOD_MSG_LIMIT_SECONDS,
    'antiflood_actions': ANTIFLOOD_ACTIONS,
    'badwords_enabled': BADWORDS_ENABLED,
    'badwords_badwords': BADWORDS_BADWORDS,
    'badwords_actions': BADWORDS_ACTIONS,
    'hello_enabled': HELLO_ENABLED,
    'hello_msg_max_len': HELLO_MSG_MAX_LEN,
    'hello_hello_words': HELLO_HELLO_WORDS,
    'hello_new_joins': HELLO_NEW_JOINS,
    'hello_new_msgs': HELLO_NEW_MSGS,
    'hello_manual_enabled': HELLO_MANUAL_ENABLED,
    'hello_interval': HELLO_INTERVAL,
    'faq_enabled': FAQ_ENABLED,
    'faq_burst': FAQ_BURST,
    'faq_rate': FAQ_RATE,
    'faq_recent': FAQ_RECENT,
}
