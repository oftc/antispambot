import weechat
# stdlib imports
from collections import deque
import time
# stuff that comes with tormodbot itself
# other modules/packages
from tmb_util.tokenbucket import token_bucket


# To make calling weechat stuff take fewer characters
w = weechat
# The queue. Add to the right with append() and take from the left with
# popleft().
Q = deque()
# The function we call every time we send a message to update our token bucket
TB_FUNC = None
# Our token bucket state. We are responsible for holding on to it and passing
# it to the TB_FUNC every time we call it.
TB_STATE = None
# Every time we spend a token, we are told how far into the future we must wait
# before spending another one. We may have to wait 0s if we still have tokens
# left, or we may have to wait some positive number of seconds if we ran out.
# Regardless, this is the timestamp after which we will have earned a new token
# and it is okay to send another message.
NEXT_SEND = 0
# The hook for the timer that expires when we can next send a message. We have
# to use this when we run out of burst tokens and must wait to earn another.
TIMER_HOOK = None


def initialize(tb_size, tb_rate):
    ''' Initialize this queue system. tb_size is an int number of messages we
    can burst at once, and tb_rate is how often we earn a new token, as a float
    number of seconds (i.e. how fast we can send messages in steady-state). '''
    global TB_FUNC
    global TB_STATE
    global NEXT_SEND
    global TIMER_HOOK
    TB_FUNC = token_bucket(tb_size, tb_rate)
    TB_STATE = None
    NEXT_SEND = 0
    if TIMER_HOOK:
        w.unhook(TIMER_HOOK)
        TIMER_HOOK = None


def send(s):
    ''' Called from elsewhere to queue the sending of some command or message.
    We add it to our queue of messages and send it later s.t. we don't flood
    the network. '''
    global Q
    global NEXT_SEND
    Q.append(s)
    _send_as_much_as_possible()
    # If there is still stuff to send, schedule a timer to expire at the point
    # in the future when we can send again
    _schedule_next()


def timer_cb():
    global Q
    global TIMER_HOOK
    # Clear out the hook
    w.unhook(TIMER_HOOK)
    TIMER_HOOK = None
    # Send stuff
    _send_as_much_as_possible()
    # Schedule ourselves again, if needed
    _schedule_next()
    return w.WEECHAT_RC_OK


def _schedule_next():
    ''' Called when we still have stuff queued to send but have run out of
    tokens.  Schedule a weechat timer to call us back when enough time has
    passed that we've earned another token. '''
    global Q
    global NEXT_SEND
    global TIMER_HOOK
    # Make sure there's actually a reason for this.
    if not len(Q):
        return
    # Make sure we don't already have a timer going. If we do, it'll call back,
    # do its thing, and reschedule.
    if TIMER_HOOK:
        return
    # Get the time difference, and make sure it is positive.
    now = time.time()
    diff = NEXT_SEND - now
    if diff < 0:
        return
    # Convert to milliseconds, and add 1 for to be extra sure we will have
    # earned a token when we get the callback.
    diff = (diff * 1000) + 1
    TIMER_HOOK = w.hook_timer(
        int(diff),  # interval. Num of milliseconds before we call the callback
        0,  # align_second. We don't care about second alignment
        1,  # max_calls. Just call us once. We'll schedule again if needed
        # Function to call. NOTE: this is NOT our timer_cb(). The
        # callback function must exist in the same file as the plugin's
        # __main__ module. Thus tormodbot.py's timer_cb() is the one called,
        # which should be written to call OUR timer_cb() when it sees the
        # "cmd_q" callback_data.
        'timer_cb',
        'cmd_q')  # callback_data. A weechat way of send data to the callback


def _send_as_much_as_possible():
    ''' Pull messages from the queue, sending them, until either (1) there are
    no more messages, or (2) we have to wait some amount of time into the
    future to send more according to the token bucket. '''
    global NEXT_SEND
    global Q
    global TB_STATE
    now = time.time()
    # while the next time we are allowed to send is now or in the past, and
    # while there are even message we want to send
    while NEXT_SEND <= now and len(Q):
        # Take a message and send it
        m = Q.popleft()
        _send(m)
        # Get the amount of time until we will have a positive number of tokens
        # again, and update our state
        wait_time, TB_STATE = TB_FUNC(TB_STATE)
        # Reset NEXT_SEND. Either it will equal now if we still have tokens
        # (wait_time is 0) or it will be in the future, in which case we will
        # stop looping.
        NEXT_SEND = now + wait_time


def _send(s):
    ''' Called internally when we're actually ready to send a command '''
    return w.command('', s)
