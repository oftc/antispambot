''' Anti-flood module

If enabled, we keep track of messages sent by all users in all moderated
channels. If a user sends more than the configured number of messages within
the configured time period, they are considered to be flooding and we take some
action(s) against them.

The :class:`Action` class lists all possible actions to take. For example,
``quiet_host`` will mute the user's host in the channel they flooded.

See the ``ANTIFLOOD_*`` options in :mod:`config` for our configuration options.
'''
import weechat
# stdlib imports
from collections import deque
import enum
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util import chanserv
from tmb_util.lcsv import lcsv
from . import Module
# from tmb_util.userstr import UserStr


# To make calling weechat stuff take fewer characters
w = weechat
#: The :data:`RECENT_ACTION_SECS` cleanup function will forgot
#: :class:`Action`\s #: older than this number of seconds.
RECENT_ACTION_SECS = 300
#: The duration of a quiet. 0.25/24 is 15 minutes
TEMP_QUIET_DAYS = 0.25/24


class Action(enum.Enum):
    ''' Actions we can take when a user floods.  '''
    #: tell chanserv to +q \*!\*@example.com
    quiet_host = 'quiet_host'


class AntiFloodModule(Module):
    ''' See the module-level documentation '''
    NAME = 'antiflood'

    def __init__(self):
        #: Storage for recent message timestamps. Items are a three-tuple:
        #:     (ts, nick, chan)
        #: If the above changes, then look for usage of this and update it.
        self.recent = deque()
        #: A FIFO list of :class:`Action`\s we've recently made. This is used
        #: to not repeat ourselves in case the flooder is able to send multiple
        #: messages after crossing the "is flooding" threshold before we've
        #: stopped them.
        #:
        #: Append Actions that you are taking to the **right** and cleanup old
        #: actions from the **left**.
        #:
        #: The items in this queue are a tuple::
        #:
        #:    (timestamp, Action, UserStr, '#channel')
        #:
        #: If this fact changes, then
        #: :meth:`AntiFloodModule._action_done_recently` needs to be updated
        self.recent_actions = deque()

    def privmsg_cb(self, user, receiver, message, is_opmod):
        ''' Main tormodbot code calls into this when we're enabled and the
        given :class:`tmb_util.userstr.UserStr` has sent ``message`` (``str``)
        to ``recevier`` (``str``). The receiver can be a channel ("#foo") or a
        nick ("foo").  '''
        # TODO: notice nick changes somehow.  That way people can't spam a
        # little, change nick, spam a little, etc.
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
        num_msgs = len([
            '' for (_, n, c) in self.recent
            if nick == n and chan == c])
        if num_msgs > self.max_msgs():
            # Get the configured list of Actions to take
            actions = self._actions()
            tmb.log('{} is flooding {}', user, receiver)
            # Do each Action that has not been done recently to this user in
            # this channel
            for a in actions:
                if self._action_done_recently(a, user, receiver):
                    tmb.log('{} done recently, skipping', a.name)
                    continue
                self.recent_actions.append((time.time(), a, user, receiver))
                tmb.log('Doing {} against {} in {}', a.name, user, receiver)
                {
                    'quiet_host': _action_quiet_host,
                }[a.name](user, receiver)
        # tmb.log('{} {} {} {}', wait_time, new_state, user.nick, message)

    def max_msgs(self):
        ''' How many messages a user may send "recently" before they are
        considered to be flooding '''
        return int(w.config_get_plugin(self._conf_key('msg_limit')))

    def recent_secs(self):
        ''' The duration in which a user may send max_msgs, and if they send
        more, they are flooding. '''
        return float(w.config_get_plugin(self._conf_key('msg_limit_seconds')))

    def _actions(self):
        ''' The list of Actions we will take when we detect someone flooding
        '''
        return [Action(s) for s in
                lcsv(w.config_get_plugin(self._conf_key('actions')))]

    def _action_done_recently(self, action, user, chan):
        ''' Returns True if Action action has NOT been taken against UserStr
        user in channel str chan recently, otherwise False '''
        for ts, ac, u, c in self.recent_actions:
            if (ac, u, c) == (action, user, chan):
                return True
        return False

    def _clear_old(self):
        ''' Clear our memory of recent messages and recent actions taken '''
        now = time.time()
        while len(self.recent) and \
                self.recent[0][0] + self.recent_secs() < now:
            self.recent.popleft()
        while len(self.recent_actions) and \
                self.recent_actions[0][0] + RECENT_ACTION_SECS < now:
            self.recent_actions.popleft()
        return


def _action_quiet_host(user, chan):
    ''' Tell chanserv to quiet the UserStr user's host on channel chan '''
    chanserv.internal_handle_command(
        user.nick, [chan], ['host'], 'flooding',
        is_quiet=True, duration=TEMP_QUIET_DAYS)
