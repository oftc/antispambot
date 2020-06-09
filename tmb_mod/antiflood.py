import weechat
# stdlib imports
from collections import deque
import enum
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.tokenbucket import token_bucket
from tmb_util.lcsv import lcsv
from tmb_util.msg import msg
# from tmb_util.userstr import UserStr


# To make calling weechat stuff take fewer characters
w = weechat
# The name of this module (wow such good comment)
MOD_NAME = 'antiflood'
# Store per-(chan, nick) token buckets that cause us to take action against the
# speaker when they run out of tokens
TOKEN_BUCKETS = {}
# A function to call every time a user sends a message to take away a token
# from their bucket. The function takes the user's state as an argument and
# returns (wait_time, new_state). wait_time is the amount of time they need to
# wait until they would have a non-zero number of tokens left (so if they
# currently have tokens, wait_time is 0), and new_state is the user's updated
# state that should be passed in next time.
# TODO: Be able to update this function's parameters if weechat's config
# changes
TB_FUNC = None
# A FIFO list of Actions we've recently made. This is used to not repeat
# ourselves in case the flooder is able to send multiple messages after
# crossing the "is flooding" threshold yet before we've stopped them.
# Append Actions that you are taking to the RIGHT and cleanup old actions from
# the LEFT.
# The items in this queue are a tuple:
#    (timestamp, Action, UserStr, '#channel')
# If this fact changes, then _action_done_recently(...) needs to be updated.
RECENT_ACTIONS = deque()
# The RECENT_ACTIONS cleanup function will forgot Actions older than this
# number of seconds.
RECENT_SECS = 300


class Action(enum.Enum):
    ''' Actions we can take when a user floods.

    The integer values are arbitrary and meaningless. I would use enum.auto(),
    but weechat on Debian 10 (buster) comes with python 2.7 (via the
    weechat-python package) and enum.auto() was added in 3.6.
    '''
    # tell chanserv to +q *!*@example.com
    quiet_host = 'quiet_host'


def enabled():
    ''' Main tormodbot code calls this to see if this module is enabled '''
    a = w.config_string_to_boolean(w.config_get_plugin(_conf_key('enabled')))
    return a


def notice_cb(sender, receiver, message):
    pass


def join_cb(user, chan):
    pass


def privmsg_cb(user, receiver, message):
    # TODO: notice nick changes somehow and update our TOKEN_BUCKET state to
    # use the new nick. That way people can't spam a little, change nick, spam
    # a little, etc. to avoid exhausting one nick's token bucket.
    global TOKEN_BUCKETS
    global TB_FUNC
    global RECENT_ACTIONS
    # The first two are sanity checks: that the receiver is a non-empty string
    # and that it looks like a channel name.
    # The third check is that it is one of our moderated channels. We only care
    # about those.
    receiver = receiver.lower()
    if not len(receiver) or \
            receiver[0] != '#' or \
            receiver not in tmb.mod_chans():
        return
    # Until we are able to "initialize" modules, we need to make sure here that
    # our TB_FUNC actually exists
    if not TB_FUNC:
        TB_FUNC = token_bucket(_tb_size(), _tb_rate())
    # Add the channel to our state, if needed
    if receiver not in TOKEN_BUCKETS:
        TOKEN_BUCKETS[receiver] = {}
    # Add the speaker to our state, if needed
    if user.nick not in TOKEN_BUCKETS[receiver]:
        TOKEN_BUCKETS[receiver][user.nick] = None
    # Take a token from them and update their state
    wait_time, new_state = TB_FUNC(TOKEN_BUCKETS[receiver][user.nick])
    TOKEN_BUCKETS[receiver][user.nick] = new_state
    # A positive wait_time indicates that they've run out of tokens, thus are
    # flooding
    if wait_time > 0:
        # Get the configured list of Actions to take
        actions = _actions()
        tmb.log('{} is flooding {}', user, receiver)
        # Do each Action that has not been done recently to this user in this
        # channel
        for a in actions:
            if _action_done_recently(a, user, receiver):
                tmb.log('{} done recently, skipping', a.name)
                continue
            RECENT_ACTIONS.append((time.time(), a, user, receiver))
            tmb.log('Doing {} against {} in {}', a.name, user, receiver)
            {
                'quiet_host': _action_quiet_host,
            }[a.name](user, receiver)
    # tmb.log('{} {} {} {}', wait_time, new_state, user.nick, message)


def _conf_key(s):
    ''' This modules config options are all prefixed with the module name and
    an underscore. Prefix the given string with that.

    >>> conf_key('enabled')
    'antiflood_enabled'
    '''
    s = MOD_NAME + '_' + s
    return s


def _tb_size():
    ''' How many tokens (messages) a user may send before they are considered
    to be flooding '''
    return int(w.config_get_plugin(_conf_key('msg_limit')))


def _tb_rate():
    ''' The amount of time, in seconds, that must pass before the user earns
    another token '''
    return float(w.config_get_plugin(_conf_key('msg_limit_seconds'))) /\
        _tb_size()


def _actions():
    ''' The list of Actions we will take when we detect someone flooding '''
    return [Action(s) for s in lcsv(w.config_get_plugin(_conf_key('actions')))]


def _action_quiet_host(user, chan):
    ''' Tell chanserv to quiet the UserStr user's host on channel chan '''
    reason = 'Flooding (tmb auto)'
    s = 'quiet {chan} add *!*@{host} {r}'.format(
        chan=chan, host=user.host, r=reason)
    msg(tmb.chanserv_user().nick, s)


def _action_done_recently(action, user, chan):
    ''' Returns True if Action action has NOT been taken against UserStr user
    in channel str chan recently, otherwise False '''
    global RECENT_ACTIONS
    # Cleanup RECENT_ACTIONS of any Action not recent anymore
    now = time.time()
    while len(RECENT_ACTIONS) and RECENT_ACTIONS[0][0] + RECENT_SECS < now:
        RECENT_ACTIONS.popleft()
    for ts, ac, u, c in RECENT_ACTIONS:
        if (ac, u, c) == (action, user, chan):
            return True
    return False
