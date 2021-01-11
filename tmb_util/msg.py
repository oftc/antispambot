'''
Helper functions to make sending messages and notices a bit less fiddly in the
string manipulation department. Provide either notice(...) or msg(...) with :

- the nick or channel you'd like to talk to,
- a format string (or just a str), and
- any number of args/kwargs to pass to .format(...)

We provide join(...) so you can join a channel without having to remember
to -noswitch. Simply pass the name of the channel you want to join.

We provide mode(...) so you can easily set the mode of a channel or nick.
Provide it with:

- the target channel or nick
- the mode flags (e.g. '+R-M') all as one string
- any number of args for the flags

We provide kick(...) so you can kick someone from some channel. Provide it
with:

- the channel
- the nick
- a reason

Examples:
    mode('#tor', '-R')
    mode('#tor', '+o-o', 'pastly', 'arma')
'''
import weechat
import tmb_util.cmdqueue as cmd_q
w = weechat


def notice(who, s, *a, **kw):
    ''' Send a notice to *who* (chan or nick). The notice message is
    ``s.format(*a, **kw)`` '''
    s = s.format(*a, **kw)
    s = '/notice {} {}'.format(who, s)
    return _send(s)


def msg(who, s, *a, **kw):
    ''' Send a PRIVMSG to *who* (chan or nick). The message is ``s.format(*a,
    **kw)`` '''
    s = s.format(*a, **kw)
    s = '/msg {} {}'.format(who, s)
    return _send(s)


def join(what):
    ''' Join a channel '''
    s = '/join -noswitch ' + what
    return _send(s)


def mode(what, flags, *a):
    ''' Set the given *flags* mode on *what* (chan or nick). Additional args
    contain values for flags. For example, +o needs a nick to receive op
    status. '''
    s = '/mode {} {} {}'.format(what, flags, ' '.join(a))
    s = s.strip()
    return _send(s)


def kick(chan, nick, reason):
    ''' KICK the given nick from chan with some reason. The reason can be an
    empty string, in which case it is set to the nick. '''
    if not reason:
        reason = nick
    s = '/kick {} {} {}'.format(chan, nick, reason)
    s = s.strip()
    return _send(s)


def voice(chan, nick):
    ''' Voice the given nick on the given channel '''
    return voices(chan, [nick])


def voices(chan, nicks):
    ''' Give voice to the given nicks on the given channel '''
    MAX = 4
    i = 0
    while i < len(nicks):
        ns = nicks[i:i+MAX+1]
        flags = '+' + 'v' * len(ns)
        mode(chan, flags, *ns)
        i += MAX


def reconnect(server):
    ''' Send the reconnect command with the given *server* '''
    return _send('/reconnect ' + server)


def _send(s):
    cmd_q.send(s)
    # return w.command('', s)
