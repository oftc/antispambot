''' Documentation for IRC masters

This module outputs documentation for other modules when requested by one of
our masters.
'''
import weechat
# stdlib imports
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.msg import notice


# To make calling weechat stuff take fewer characters
w = weechat

#: All known commands for which we can provide help
KNOWN_CMDS = [
    'reconnect', 'ping',
]
KNOWN_CMDS.sort()
#: Main help function calls into these to get help on specific commands
TOP_LVL_CMDS = {
    'ping': lambda s: _help_ping(s),
    'reconnect': lambda s: _help_reconnect(s),
}
for _ in KNOWN_CMDS:
    assert _ in TOP_LVL_CMDS


def _help():
    ''' Help string for empty 'help' command '''
    return 'Known commands are: ' + ', '.join(KNOWN_CMDS) + '\n' +\
        'Try: help ping'


def _help_ping(cmd_msg):
    ''' Help string for 'help ping' '''
    return 'Responds with a pong'


def _help_reconnect(cmd_msg):
    ''' Help string for 'help reconnect' '''
    return 'Executes /reconnect, forcing us to reconnect to the IRC network'


def handle_command(user, where, message):
    ''' Main tormodbot code calls into this when we're enabled and the given
    :class:`tmb_util.userstr.UserStr` has sent us a command stored in
    ``message`` (``str``) via ``where`` (``str``, either a "#channel" or our
    nick if PM). It has already been verified that the user is a master and
    that ``where`` is a proper place.
    '''
    # If it came in as a PM: *where* is our own nick and any response should go
    # to the user's nick. If it came in via the command channel: any response
    # should go to the command channel
    dest = user.nick if where != tmb.cmd_chan() else tmb.cmd_chan()
    # Make sure it looks like a help command. If not, just return. This
    # shouldn't happen
    message = message.lower()
    if not len(message) or message.split()[0] != 'help':
        return w.WEECHAT_RC_OK
    # strip off the leading 'help' part of the message, then any additional
    # leading spaces
    cmd_msg = message[message.index('help')+len('help'):].lstrip()
    words = cmd_msg.split()
    out_msg = None
    if not len(cmd_msg):
        out_msg = _help()
    elif words[0] not in TOP_LVL_CMDS:
        out_msg = 'Unknown command "{}"'.format(words[0])
    else:
        assert words[0] in TOP_LVL_CMDS
        out_msg = TOP_LVL_CMDS[words[0]](out_msg)
    if not out_msg:
        return w.WEECHAT_RC_OK
    for line in out_msg.split('\n'):
        notice(dest, line)
    return w.WEECHAT_RC_OK
