import weechat
# stdlib imports
# stuff that comes with tormodbot itself
from tormodbot import mod_chans, log
# other modules/packages
from tmb_util.tokenbucket import token_bucket
# from tmb_util.lcsv import lcsv
# from tmb_util.msg import msg, voice
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
    # The first two are sanity checks: that the receiver is a non-empty string
    # and that it looks like a channel name.
    # The third check is that it is one of our moderated channels. We only care
    # about those.
    receiver = receiver.lower()
    if not len(receiver) or receiver[0] != '#' or receiver not in mod_chans():
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
    log('{} {} {} {}', wait_time, new_state, user.nick, message)


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
    return _tb_size() /\
        float(w.config_get_plugin(_conf_key('msg_limit_seconds')))
