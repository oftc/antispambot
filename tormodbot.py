import weechat
# stdlib imports
# stuff that comes with tormodbot itself
from config import conf as CONF
import tmb_mod.autovoice
# other modules/packages
from tmb_util.msg import notice, msg, join, mode
from tmb_util.lcsv import lcsv
from tmb_util.userstr import UserStr


w = weechat

SCRIPT_NAME = 'tormodbot'
SCRIPT_AUTHOR = 'Matt Traudt <pastly@torproject.org>'
SCRIPT_VERSION = '0.1.0'
SCRIPT_LICENSE = 'MIT'
SCRIPT_DESC = 'Help Tor Project moderate their many channels'

CONNECTED = False


def log(s, *a, **kw):
    s = s.format(*a, **kw)
    # log to core window
    w.prnt('', w.prefix('error') + s)
    # log to log channel
    if not log_chan():
        return
    notice(log_chan(), s)


def my_nick():
    ''' Returns my current nick on the configured server '''
    return w.info_get('irc_nick', CONF['serv'])


def cmd_chan():
    s = CONF['cmd_chan']
    return s if s else None


def masters():
    ''' Returns the list of my currently configured masters '''
    return lcsv(CONF['masters'])


def mod_chans():
    ''' Returns the list of my currently configured channels to moderate '''
    return lcsv(CONF['mod_chans'])


def log_chan():
    s = CONF['log_chan']
    return s if s else None


def nickserv_user():
    ''' Returns UserStr of the configured nickserv '''
    return UserStr(CONF['nickserv_userstr'])


def connected_cb(data, signal, signal_data):
    ''' Callback for when we have (dis)connected to a server '''
    # data: empty
    # signal: "irc_server_connected" or "irc_server_disconnected"
    # signal_data: "oftc"
    global CONNECTED
    CONNECTED = signal == "irc_server_connected"
    log('We are {}connected to {}', '' if CONNECTED else 'not ', signal_data)
    if CONNECTED:
        # make sure we're in all the chans for modding, and for logging
        for c in mod_chans():
            join(c)
        if log_chan():
            join(log_chan())
        # make sure we're op in all the modding chans
        chanop_chans(mod_chans(), True)
    return w.WEECHAT_RC_OK


def join_cb(data, signal, signal_data):
    ''' Callback for when we see a JOIN '''
    global NICKSERV_TIME_REG_Q
    # signal is for example: "freenode,irc_in2_join"
    # signal_data is IRC message, for example: ":nick!user@host JOIN :#channel"
    data = w.info_get_hashtable('irc_message_parse', {'message': signal_data})
    user, chan = UserStr(data['host']), data['channel']
    if tmb_mod.autovoice.enabled():
        tmb_mod.autovoice.join_cb(user, chan)
    return w.WEECHAT_RC_OK


def privmsg_cb(data, signal, signal_data):
    ''' Callback for when we see a PRIVMSG '''
    # signal is for example: "oftc,irc_raw_in2_PRIVMSG"
    # signal_data is for example:
    #     ":nick!~user@host PRIVMSG #chan :the message" (if sent to a channel)
    #     ":nick!~user@host PRIVMSG mynick :the message" (if sent to us)
    #############
    # Parse data
    #############
    # remove leading ':'
    assert signal_data.startswith(':')
    signal_data = signal_data[1:]
    # parse out user that sent this message
    user, signal_data = signal_data.split(' ', 1)
    user = UserStr(user)
    # trim cruft
    assert signal_data.startswith('PRIVMSG ')
    signal_data = signal_data[len('PRIVMSG '):]
    # get the place to which the user sent this message
    dest, signal_data = signal_data.split(' ', 1)
    # trim leading ':'
    assert signal_data.startswith(':')
    signal_data = signal_data[1:]
    # the message that was sent
    message = signal_data.strip()
    #######################
    # Determine what to do
    #######################
    # If looks like a comment, just stop
    if message.startswith('#'):
        return w.WEECHAT_RC_OK
    # If not from a master, just stop
    if user.nick not in masters():
        log('Ignoring message from non-master {}: {}', user.nick, message)
        return w.WEECHAT_RC_OK
    # If not sent private to us or in the command channel, just stop
    # cmd_chan() might be None, but this should be fine
    if dest != my_nick() and dest != cmd_chan():
        log(
            'Ignoring message from master {} in non-cmd context {}: {}',
            user.nick, dest, message)
        return w.WEECHAT_RC_OK
    # It's safe to act on this message as a command
    recv_command(user, dest, message)
    return w.WEECHAT_RC_OK


def notice_cb(data, signal, signal_data):
    ''' Callback for when we see a NOTICE '''
    # signal is for example: "oftc,irc_raw_in2_NOTICE"
    # signal_data is for example:
    #     ":dacia.oftc.net NOTICE pastly :Activating Cloak: example.com -> foo.oftc.net for foo"
    #     ":nick!user@host NOTICE #channel :some messge"
    #############
    # Parse data
    #############
    # remove leading ':'
    assert signal_data.startswith(':')
    signal_data = signal_data[1:]
    # parse out who sent this message (will always be a IRC server?)
    sender, signal_data = signal_data.split(' ', 1)
    sender = sender.lower()
    # trim cruft
    assert signal_data.startswith('NOTICE ')
    signal_data = signal_data[len('NOTICE '):]
    # get the place to which the user sent this message (will always be us?)
    receiver, signal_data = signal_data.split(' ', 1)
    receiver = receiver.lower()
    # trim leading ':'
    assert signal_data.startswith(':')
    signal_data = signal_data[1:]
    # the message that was sent
    message = signal_data.strip()
    #######################
    # Determine what to do
    #######################
    # If not to us, just stop
    if receiver != my_nick():
        return w.WEECHAT_RC_OK
    if tmb_mod.autovoice.enabled():
        tmb_mod.autovoice.notice_cb(sender, receiver, message)
    return w.WEECHAT_RC_OK


def send_pong(user, chan_nick):
    ''' Send a pong message to UserStr *user* in location str *chan_nick*. The
    location will either be our the user's nick, if a private message, or a
    channel name.

    If it was a private message, just reponsd with 'pong'. If it was in a
    channel, prefix the response with their nick. For example: 'pastly: pong'.
    '''
    if chan_nick[0] == '#':
        msg = user.nick + ': pong'
    else:
        msg = 'pong'
    return notice(chan_nick, msg)


def recv_command(user, dest, message):
    ''' Act on the command str *message* received from master UserStr *user* at
    location str *dest*. The location will either be our nick or a channel
    name, starting with a '#'. '''
    # log('Message from master {}: {}', user.nick, message)
    words = message.split()
    if words[0].lower() == 'ping':
        send_pong(user, dest if dest[0] == '#' else user.nick)


def chanop_chans(chans, up):
    ''' Given a list of channels, ask chanserv to op us in each one (if *up* is
    True) otherwise deop ourself '''
    for chan in chans:
        if up:
            msg('chanserv', 'op {} {}', chan, my_nick())
        else:
            mode(chan, '-o', my_nick())


def config_cb(data, option, value):
    ''' Called whenever the user changes some script options '''
    # set the new value
    prefix = 'plugins.var.python.' + SCRIPT_NAME + '.'
    option = option[len(prefix):]
    CONF[option] = value
    # make sure we're in all the right chans for modding
    for c in mod_chans():
        join(c)
    return w.WEECHAT_RC_OK


def infolist_len(ilist):
    ''' Takes an infolist that has a cursor already at the beginning. Count the
    number of items in it. Return cursor to beginning. Return number of items
    in infolist. '''
    count = 0
    while w.infolist_next(ilist):
        # log('%s' % (w.infolist_fields(ilist),))
        n = w.infolist_string(ilist, 'name')
        h = w.infolist_string(ilist, 'host')
        a = w.infolist_string(ilist, 'prefixes')
        log('{n}@{h} "{a}"', n=n, h=h, a=a)
        count += 1
    w.infolist_reset_item_cursor(ilist)
    return count


if __name__ == '__main__':
    if not w.register(
            SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
            SCRIPT_DESC, '', ''):
        exit(1)

    # set default options
    for opt, def_val in CONF.items():
        if not w.config_is_set_plugin(opt):
            w.config_set_plugin(opt, def_val)
        else:
            CONF[opt] = w.config_get_plugin(opt)

    w.hook_signal('irc_server_connected', 'connected_cb', '')
    w.hook_signal('irc_server_disconnected', 'connected_cb', '')
    w.hook_signal('*,irc_raw_in2_JOIN', 'join_cb', '')
    w.hook_signal('*,irc_raw_in2_PRIVMSG', 'privmsg_cb', '')
    w.hook_signal('*,irc_raw_in2_NOTICE', 'notice_cb', '')
    w.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'config_cb', '')

    # count = 0
    # ilist = w.infolist_get('irc_nick', '', '%s,%s' % (log_serv, log_chan))
    # count = infolist_len(ilist)
    # log('%d nicks' % (count,))
    # w.infolist_free(ilist)

    s = '{} v{} (re)loaded'.format(SCRIPT_NAME, SCRIPT_VERSION)
    log(s)
    for opt, def_val in CONF.items():
        log('{} => {}', opt, CONF[opt])

# vim: ts=4 sw=4 et
