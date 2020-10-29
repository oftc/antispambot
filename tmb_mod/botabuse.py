''' Anti-bot abuse module

If enabled, look for bots spamming a specific channel and temporarily mute
them.

This is a lot like the anti-flood module, except we undo our mutes and are
specifically meant for mitigating bots' nicks from spamming.
'''

import weechat
# stdlib imports
from collections import deque
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util import chanserv
from tmb_util.lcsv import lcsv
from tmb_util.userstr import UserStr
from . import Module

w = weechat
SECS_IN_DAY = 60 * 60 * 24


class BotAbuseModule(Module):
    ''' See the module-level documentation '''
    NAME = 'botabuse'

    def __init__(self):
        #: Storage for recent bot messages. Items are three-tuples:
        #:     (ts, nick, chan)
        #: If the above changes, then _clear_old and handle_message needs to be
        #: updated.
        self.recent = deque()
        #: How many messages a bot chan send in a channel per recent_secs.
        #: Hitting this causes us to mute the bot
        self.recent_max = 5
        #: How long ago a message is considered recent
        self.recent_secs = 5
        #: How long to mute, in seconds
        self.mute_secs = 180
        #: Storage for recording actions we've taken so that we don't remake
        #: them and end up spamming a channel ourselves. Items are a
        #: the same as in self.recent, and the same places need to be updated
        #: if this changes.
        self.actions = deque()
        #: How long we remember an action that we took.
        self.actions_secs = self.mute_secs + 5

    def _botnames(self):
        return set(lcsv(w.config_get_plugin(self._conf_key('bots'))))

    def _clear_old(self):
        now = time.time()
        while len(self.recent) and \
                self.recent[0][0] + self.recent_secs < now:
            self.recent.popleft()
        while len(self.actions) and \
                self.actions[0][0] + self.actions_secs < now:
            self.actions.popleft()
        return

    def handle_message(self, nick, chan):
        self._clear_old()
        # sanity checks
        if nick not in self._botnames() or \
                chan not in tmb.mod_chans():
            return
        now = time.time()
        self.recent.append((now, nick, chan))
        # How many times *nick* has sent a message in *chan* recently
        num_msgs = len([
            '' for (_, n, c) in self.recent
            if nick == n and chan == c])
        # How many times we've taken action against *nick* in *chan* recently
        num_actions = len([
            '' for (_, n, c) in self.actions
            if nick == n and chan == c])
        if num_msgs >= self.recent_max and num_actions == 0:
            chanserv.internal_handle_command(
                nick, [chan], ['nick'],
                'bot suspected to be used as flood toy',
                is_quiet=True,
                duration=self.mute_secs * 1.0 / SECS_IN_DAY)
            self.actions.append((now, nick, chan))

    def privmsg_cb(self, user, receiver, message):
        if user.nick not in self._botnames() or \
                not len(receiver) or \
                receiver[0] != '#' or \
                receiver not in tmb.mod_chans():
            return
        chan = receiver
        return self.handle_message(user.nick, chan)

    def notice_cb(self, sender, receiver, message):
        if '!' not in sender or '@' not in sender:
            return
        user = UserStr(sender)
        if user.nick not in self._botnames() or \
                not len(receiver) or \
                receiver[0] != '#' or \
                receiver not in tmb.mod_chans():
            return
        chan = receiver
        return self.handle_message(user.nick, chan)
