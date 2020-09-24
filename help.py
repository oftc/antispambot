''' Documentation for IRC masters

This module outputs documentation for other modules when requested by one of
our masters.
'''
import weechat
# stdlib imports
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.chanserv import TEMP_BAN_DAYS
from tmb_util.msg import notice


# To make calling weechat stuff take fewer characters
w = weechat

#: All known commands for which we can provide help
KNOWN_CMDS = [
    'reconnect', 'ping', 'mode', 'info',
    'akick', 'ban',
    'quiet', 'mute',
]
KNOWN_CMDS.sort()
#: Main help function calls into these to get help on specific commands
TOP_LVL_CMDS = {
    'akick': lambda s: _help_akickquiet(s, 'akick'),
    'ban': lambda s: _help_akickquiet(s, 'akick'),
    'info': lambda s: _help_info(s),
    'mode': lambda s: _help_mode(s),
    'mute': lambda s: _help_akickquiet(s, 'quiet'),
    'ping': lambda s: _help_ping(s),
    'quiet': lambda s: _help_akickquiet(s, 'quiet'),
    'reconnect': lambda s: _help_reconnect(s),
}
for _ in KNOWN_CMDS:
    assert _ in TOP_LVL_CMDS


def _help():
    ''' Help string for empty 'help' command '''
    return 'Known commands are: ' + ', '.join(KNOWN_CMDS) + '\n' +\
        'Try: help ping'


def _help_akickquiet(s, which):
    ''' Help string for akick/ban/mute/quiet '''
    return '''{which} a user from a channel.
By default, an {which} is temporary for {temp_d} days.
Usage:
.   {which} [-p|--permanent] [-d|--duration DAYS] <chans_csv> <nick> <patterns_csv> <reason ...>
-p,--permanent: Make the {which} permanent. This overrides -d if it is also provided.
-d,--duration DAYS: Make the {which} temporary for the provided number of DAYS.
chans_csv: CSV list of channels from which to {which} the user.
nick: The nick of the user to {which}.
patterns_csv: CSV list of hostmask patterns to {which}.
reason: Required. The reason for the {which} to record with chanserv.
.
Consider the user crazycake!jasper@example.com.
To permanently {which} his nick and host from #foo and #bar:
.    {which} -p #foo,#bar crazycake nick,host asks too many stupid questions
This results in {me} issuing four chanserv commands:
.    {which} add #foo crazycake!*@* asks too many stupid questions
.    {which} add #bar crazycake!*@* asks too many stupid questions
.    {which} add #foo *!*@example.com asks too many stupid questions
.    {which} add #bar *!*@example.com asks too many stupid questions
.
Instead of a CSV of channels, you can simply provide "all", resulting in a {which} in every moderated channel.
.
The hostmask patterns are:
.    nick nick* *nick *nick*
.    user user* *user *user*
.    host host* *host *host*
They add asterisks ('*') to the corresponding spots in the nick!user@host hostmask. For example:
.    {which} #foo crazycake nick*,user*,*host* thinks he knows more than he does
This results in {me} issuing three chanserv commands:
.    {which} add #foo crazycake*!*@*
.    {which} add #foo *!jasper*@*
.    {which} add #foo *!*@*example.com*
'''.format(  # noqa: E501
        which=which,
        me=tmb.my_nick(),
        temp_d=TEMP_BAN_DAYS)


def _help_info(cmd_msg):
    ''' Help string for 'help info' command '''
    return '''Get info on a nick.
Ex: "info crazycake" returns information we have on crazycake
Additional info may be provided in future updates, thus this help is vague.
'''


def _help_mode(cmd_msg):
    ''' Help string for 'help mode' '''
    return '''Set a channel or user mode.
Ex: "mode #tor +R" makes us execute "/mode #tor +R"
If you'd like to mute/quiet (+q) or ban/akick (+b) someone, use the
quiet/akick commands instead.
'''


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
