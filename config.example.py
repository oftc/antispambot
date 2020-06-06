conf = {
    # IRC server we're joining and on which all the channels are
    'serv': 'oftc',
    # Channel/user in which to log messages in addition to the core window
    'log_chan': '#pastly-log',
    # Channel from which to take commands. If empty, only takes commands from
    # PM
    'cmd_chan': '#pastly-log',
    # Channels that we moderate
    'mod_chans': '#pastly-test,#pastly-test2',
    # Nicks from which we will accept commands (as private messages or in the
    # command channel)
    'masters': 'pastly',
    # The full nick!user@host string for nickserv
    'nickserv_userstr': 'NickServ!services@services.oftc.net',
}
