''' Bad words module

If enabled, look for people sending a message that matches a "bad word," and if
found, take action against them.

The :class:`Action` class lists all possible actions to take. For example,
``quiet_nick`` will mute the user's nick in the channel they flooded.

See the ``BADWORDS_*`` options in :mod:`config` for our configuration options.
'''
import weechat
# stdlib imports
import enum
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util import chanserv
from tmb_util.lcsv import lcsv
from tmb_util.msg import mode
from . import Module

# To make calling weechat stuff take fewer characters
w = weechat


class Action(enum.Enum):
    ''' Actions we can take when a user says a bad word.  '''
    #: tell chanserv to +q pastly!\*@\*
    quiet_nick = 'quiet_nick'
    #: set the channel to +R
    plusr_chan = 'plusr_chan'


class BadWordsModule(Module):
    ''' See the module-level documentation '''
    NAME = 'badwords'

    def privmsg_cb(self, user, receiver, message):
        ''' Main tormodbot code calls into this when we're enabled and the
        given :class:`tmb_util.userstr.UserStr` has sent ``message`` (``str``)
        to ``recevier`` (``str``). The receiver can be a channel ("#foo") or a
        nick ("foo").  '''
        # The first two are sanity checks: that the receiver is a non-empty
        # string and that it looks like a channel name.
        # The third check is that it is one of our moderated channels. We only
        # care about those.
        receiver = receiver.lower()
        if not len(receiver) or \
                receiver[0] != '#' or \
                receiver not in tmb.mod_chans():
            return
        bad_words = lcsv(w.config_get_plugin(self._conf_key('badwords')))
        # Make message lower case for case-insensitive matching
        message = message.lower()
        # Check to see if any of the bad words are in the message
        for bad_word in bad_words:
            # Make every bad word lower case for case-insensitive matching
            bad_word = bad_word.lower()
            if bad_word in message:
                tmb.log(
                    '{} said bad word "{}" in {}', user.nick, bad_word,
                    receiver)
                for a in self._actions():
                    {
                        'quiet_nick': _action_quiet_nick,
                        'plusr_chan': _action_plusr_chan,
                    }[a.name](user, receiver)
                return

    def _actions(self):
        ''' The list of Actions we will take when we detect a bad word '''
        return [Action(s) for s in
                lcsv(w.config_get_plugin(self._conf_key('actions')))]


def _action_quiet_nick(user, chan):
    ''' Tell chanserv to quiet the UserStr user's host on channel chan '''
    chanserv.internal_handle_command(
        user.nick, [chan], ['nick'], 'badword', is_quiet=True)


def _action_plusr_chan(user, chan):
    mode(chan, '+R')
