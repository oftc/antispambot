''' Join spam module

If enabled, look for people (possibly unintentionally) join/part or join/quit
spamming.  If found, take action against them.

See the ``JOINSPAM_*`` options in :mod:`config` for our configuration options.
'''
import weechat
# stdlib imports
from collections import deque
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util import chanserv
from . import Module

# To make calling weechat stuff take fewer characters
w = weechat
#: The reason to log for a temporary ban
TEMP_BAN_REASON = 'Join spam, please fix your client or connection. '\
    'Tell pastly or wait 4 hours for the ban to expire.'
#: The duration of a temporary ban
TEMP_BAN_DAYS = 4.0/24


class JoinSpamModule(Module):
    ''' See the module-level documentation '''
    NAME = 'joinspam'

    def __init__(self):
        #: Storage for recent joins. Items are three-tuples:
        #:     (ts, nick, chan)
        #: If the above changes, then look for usage of this and update it.
        self.recent = deque()

    def join_cb(self, user, receiver):
        # The first two are sanity checks: that the receiver is a non-empty
        # string and that it looks like a channel name.
        # The third check is that it is one of our moderated channels. We only
        # care about those.
        receiver = receiver.lower()
        if not len(receiver) or \
                receiver[0] != '#' or \
                receiver not in tmb.mod_chans():
            return
        self._clear_old()
        nick = user.nick
        chan = receiver
        now = time.time()
        self.recent.append((now, nick, chan))
        # How many times *nick* has joined *chan* recently
        num_joins = len([
            '' for (_, n, c) in self.recent
            if nick == n and chan == c])
        will_ban = num_joins >= self.max_joins()
        tmb.log(
            '{} has joined {} {}/{} times in last {} mins{}.',
            nick, chan, num_joins, self.max_joins(), self.recent_mins(),
            ' Banning.' if will_ban else '')
        if will_ban:
            chanserv.internal_handle_command(
                nick, [chan], ['nick'],
                TEMP_BAN_REASON,
                is_quiet=False,
                duration=TEMP_BAN_DAYS)

    def _clear_old(self):
        now = time.time()
        while len(self.recent) and \
                self.recent[0][0] + self.recent_mins() * 60 < now:
            self.recent.popleft()
        return

    def max_joins(self):
        return int(w.config_get_plugin(self._conf_key('max_joins')))

    def recent_mins(self):
        return int(w.config_get_plugin(self._conf_key('recent_mins')))
