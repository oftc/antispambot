import weechat
# stdlib imports
import sys
# stuff that comes with tormodbot itself
from config import conf as CONF
import tmb_mod.autovoice
import tmb_mod.antiflood
# other modules/packages
import tmb_util.cmdqueue as cmd_q
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
    # log to core window
    w.prnt('', w.prefix('error') + s.format(*a, **kw))
    # log to log channel
    if not log_chan():
        return
    notice(log_chan(), s, *a, **kw)


def my_nick():
    ''' Returns my current nick on the configured server '''
    return w.info_get('irc_nick', CONF['serv'])


def cmd_chan():
    s = CONF['cmd_chan']
    return s.lower() if s else None


def masters():
    ''' Returns the list of my currently configured masters. Nicks are
    normalized to lowercase '''
    return lcsv(CONF['masters'].lower())


def ignores():
    ''' Returns the list of nicks which we ignore all PRIVMSG and NOTICE. Nicks
    are normalized to lowercase. '''
    return lcsv(CONF['ignores'].lower())


def mod_chans():
    ''' Returns the list of my currently configured channels to moderate. Chans
    are normalized to lowercase. '''
    return lcsv(CONF['mod_chans'].lower())


def log_chan():
    ''' Return the currently configured logging channel, or None if not
    configured. Chan is normalized to lowercase '''
    s = CONF['log_chan']
    return s.lower() if s else None


def nickserv_user():
    ''' Returns UserStr of the configured nickserv '''
    return UserStr(CONF['nickserv_userstr'])


def chanserv_user():
    ''' Returns UserStr of the configured chanserv '''
    return UserStr(CONF['chanserv_userstr'])


def timer_cb(data, remaining_calls):
    ''' Whenever a timer expires, this function should be called. If data is
    set, then it was that module that set a timer that expired, so we should
    hand control off to it. Otherwise it was us.
    '''
    if data == 'cmd_q':
        return cmd_q.timer_cb()
    log(
        'timer_cb called with empty or unrecognized data arg "{}", so don\'t '
        'know who to tell about this.', data)
    return w.WEECHAT_RC_OK


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
    if tmb_mod.antiflood.enabled():
        tmb_mod.antiflood.join_cb(user, chan)
    return w.WEECHAT_RC_OK


def handle_command(user, where, message):
    ''' UserStr *user* sent us str *message* that should be treated as a
    command.  The caller verified this user has permission to command us and
    that they sent us the message in a proper place. The str *where* indicates
    the place where we we got it: either '#channel' if the cmd channel, or our
    own nick. '''
    # If it came in as a PM: *where* is our own nick and any response should go
    # to the user's nick. If it came in via the command channel: any response
    # should go to the command channel
    dest = user.nick if where != cmd_chan() else cmd_chan()
    words = message.split()
    if not len(words):
        return
    if words[0].lower() == 'ping':
        notice(dest, 'pong' if where == my_nick() else user.nick + ': pong')
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
    # If it is a user to ignore, ignore them
    if user.nick in ignores():
        log('Ignore PRIVMSG from {} in {}', user.nick, dest)
        return w.WEECHAT_RC_OK
    # If it is a PM to us or a message in our cmd channel, AND if the sender is
    # one of our masters, handle it as a command
    if (dest == my_nick() or dest == cmd_chan()) and user.nick in masters():
        return handle_command(user, dest, message)
    ###########
    # It wasn't a command at this point
    ###########
    # If it came in our cmd channel, then ignore
    if dest == cmd_chan():
        return w.WEECHAT_RC_OK
    # If it was a PM, then ignore
    if dest == my_nick():
        return w.WEECHAT_RC_OK
    # If it came in on something other than a moderated channel, ignore it
    if dest not in mod_chans():
        return w.WEECHAT_RC_OK
    # Tell our modules about this message
    if tmb_mod.autovoice.enabled():
        tmb_mod.autovoice.privmsg_cb(user, dest, message)
    if tmb_mod.antiflood.enabled():
        tmb_mod.antiflood.privmsg_cb(user, dest, message)
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
    # parse out who sent this message. It could be a 'n!u@h' str, but it could
    # also be an IRC server if we are an op
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
    # If it is a user to ignore, ignore them.
    if '!' in sender and sender[:sender.index('!')].lower() in ignores():
        log('Ignore NOTICE from {}', sender)
        return w.WEECHAT_RC_OK
    # If not to us, just stop
    if receiver != my_nick():
        return w.WEECHAT_RC_OK
    if tmb_mod.autovoice.enabled():
        tmb_mod.autovoice.notice_cb(sender, receiver, message)
    if tmb_mod.antiflood.enabled():
        tmb_mod.antiflood.notice_cb(sender, receiver, message)
    return w.WEECHAT_RC_OK


def chanop_chans(chans, up):
    ''' Given a list of channels, ask chanserv to op us in each one (if *up* is
    True) otherwise deop ourself '''
    for chan in chans:
        if up:
            msg(chanserv_user().nick, 'op {} {}', chan, my_nick())
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

    # (re)init systems
    cmd_q.initialize(int(CONF['msg_burst']), float(CONF['msg_rate'])/1000)

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
    s = 'Using: Python {}'.format(sys.version.split('\n')[0])
    log(s)
    # for opt, def_val in CONF.items():
    #     log('{} => {}', opt, CONF[opt])

# vim: ts=4 sw=4 et
