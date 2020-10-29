''' Anti-flood module

If enabled,
we keep a token bucket for every unique ``(user, channel)`` pair, and if the
bucket runs out of tokens, we take some action(s) against the user.

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
from tmb_util.tokenbucket import token_bucket
from tmb_util.lcsv import lcsv
from . import Module
# from tmb_util.userstr import UserStr


# To make calling weechat stuff take fewer characters
w = weechat
#: The :data:`RECENT_ACTIONS` cleanup function will forgot :class:`Action`\s
#: older than this number of seconds.
RECENT_SECS = 300


class Action(enum.Enum):
    ''' Actions we can take when a user floods.  '''
    #: tell chanserv to +q \*!\*@example.com
    quiet_host = 'quiet_host'


class AntiFloodModule(Module):
    ''' See the module-level documentation '''
    NAME = 'antiflood'

    def __init__(self):
        #: Store per-``(chan, nick)`` token buckets that cause us to take
        #: action against the speaker when they run out of tokens
        self.token_buckets = {}
        #: Function to call every time a user sends a message to take away a
        #: token from their bucket. The function takes the user's state as an
        #: argument and returns ``(wait_time, new_state)``. ``wait_time`` is
        #: the amount of time they need to wait until they would have a
        #: non-zero number of tokens left (so if they currently have tokens,
        #: ``wait_time`` is 0), and ``new_state`` is the user's updated state
        #: that should be passed in next time.
        #:
        #: TODO: Be able to update this function's parameters if weechat's
        #: config changes
        self.tb_func = token_bucket(self._tb_size(), self._tb_rate())
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

    def privmsg_cb(self, user, receiver, message):
        ''' Main tormodbot code calls into this when we're enabled and the
        given :class:`tmb_util.userstr.UserStr` has sent ``message`` (``str``)
        to ``recevier`` (``str``). The receiver can be a channel ("#foo") or a
        nick ("foo").  '''
        # TODO: notice nick changes somehow and update our TOKEN_BUCKET state
        # to use the new nick. That way people can't spam a little, change
        # nick, spam a little, etc. to avoid exhausting one nick's token
        # bucket.
        # The first two are sanity checks: that the receiver is a non-empty
        # string and that it looks like a channel name.
        # The third check is that it is one of our moderated channels. We only
        # care about those.
        receiver = receiver.lower()
        if not len(receiver) or \
                receiver[0] != '#' or \
                receiver not in tmb.mod_chans():
            return
        # Add the channel to our state, if needed
        if receiver not in self.token_buckets:
            self.token_buckets[receiver] = {}
        # Add the speaker to our state, if needed
        if user.nick not in self.token_buckets[receiver]:
            self.token_buckets[receiver][user.nick] = None
        # Take a token from them and update their state
        wait_time, new_state = self.tb_func(
            self.token_buckets[receiver][user.nick])
        self.token_buckets[receiver][user.nick] = new_state
        # A positive wait_time indicates that they've run out of tokens, thus
        # are flooding
        if wait_time > 0:
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

    def _tb_size(self):
        ''' How many tokens (messages) a user may send before they are
        considered to be flooding '''
        return int(w.config_get_plugin(self._conf_key('msg_limit')))

    def _tb_rate(self):
        ''' The amount of time, in seconds, that must pass before the user
        earns another token '''
        return \
            float(w.config_get_plugin(self._conf_key('msg_limit_seconds'))) /\
            self._tb_size()

    def _actions(self):
        ''' The list of Actions we will take when we detect someone flooding
        '''
        return [Action(s) for s in
                lcsv(w.config_get_plugin(self._conf_key('actions')))]

    def _action_done_recently(self, action, user, chan):
        ''' Returns True if Action action has NOT been taken against UserStr
        user in channel str chan recently, otherwise False '''
        # Cleanup recent_actions of any Action not recent anymore
        now = time.time()
        while len(self.recent_actions) and \
                self.recent_actions[0][0] + RECENT_SECS < now:
            self.recent_actions.popleft()
        for ts, ac, u, c in self.recent_actions:
            if (ac, u, c) == (action, user, chan):
                return True
        return False


def _action_quiet_host(user, chan):
    ''' Tell chanserv to quiet the UserStr user's host on channel chan '''
    chanserv.internal_handle_command(
        user.nick, [chan], ['host'], 'flooding', is_quiet=True)
