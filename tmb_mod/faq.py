''' FAQ module

If enabled, we can read a library of FAQ responses from plain-text files on
disk, both bundled with tormodbot and ones the operator wrote themself.

FAQ responses can be specific to a moderated channel, or they can be general
for all channels. Assuming the default WeeChat data directory, when searching
for the response to FAQ keyword ``bar`` in channel ``#foo``, we search in the
following places **in order** and select the first FAQ response found:

.. code-block:: text

    ~/.weechat/tmb_data/#foo/bar.txt
    ~/.weechat/tmb_data/all/bar.txt
    ~/.weechat/python/faq/#foo/bar.txt
    ~/.weechat/python/faq/all/bar.txt

The motivation for this order is to allow the operator to have a general
keyword with the same response in all channels, but override that response in
specific channels. Additionally, any FAQ responses that come bundled with this
code will be overridden by *any* operator-created FAQ response that uses the
same keyword.

The keyword is not case-sensistive, has no spaces, and otherwise lacks any
characters that would constitute an invalid filename.

To limit the extent to which we can be used for a spam tool, we rate limits
ourself in *each* moderated channel. See the ``FAQ_*`` options in :mod:`config`
for the options how many responses we can *burst* in a channel, as well as the
steady-state *rate* at which we will send responses in a channel. Additionally,
we won't give the same FAQ response in a channel if we have done so *recently*.

FAQ response files can be multiple liness; however, blank lines are ignored and
leading/trailing whitespace is stripped. Comment lines -- those whose first
non-whitespace character is '#' -- are also ignored. There is no such thing as
an end-of-line comment.

.. code-block:: text

    This is the first line of a FAQ response.

    This line is printed right after the first, with no blank line in between.
    # This is a comment, thus isn't printed.
    This entire line is printed # because this isn't a comment.

'''
import weechat
# stdlib imports
import os
from collections import deque
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.msg import notice
from tmb_util.tokenbucket import token_bucket


# To make calling weechat stuff take fewer characters
w = weechat
#: The name of this module (wow such good comment)
MOD_NAME = 'faq'
#: Store per-``chan`` token buckets so we prevent ourselves from flooding when
#: used as a toy
TOKEN_BUCKETS = {}
#: Function to call every time we send a message to take away a token from
#: that channel's bucket. The function takes the channels's state as an
#: argument and returns ``(wait_time, new_state)``. ``wait_time`` is the amount
#: of time we need to wait until we would have a non-zero number of tokens left
#: (so if we currently have tokens for this channel, ``wait_time`` is 0), and
#: ``new_state`` is the channels's updated state that should be passed in next
#: time.
#:
#: TODO: Be able to update this function's parameters if weechat's config
#: changes
TB_FUNC = None
#: A FIFO list of responses we've recently made. This is used to not
#: repeat ourselves in case we are asked to paste the same FAQ rapidly.
#:
#: Append responses that you are taking to the **right** and cleanup old ones
#: from the **left**.
#:
#: The items in this queue are a tuple::
#:
#:    (timestamp, #channel, keyword)
#:
#: If this fact changes, then :meth:`_action_done_recently` needs to be updated
RECENT_FAQS = deque()


def enabled():
    ''' Main tormodbot code calls this to see if this module is enabled '''
    a = w.config_string_to_boolean(w.config_get_plugin(_conf_key('enabled')))
    return a


def datadir():
    ''' Return the datadir for this specific module '''
    return os.path.join(tmb.datadir(), MOD_NAME)


def _bundled_faq_dir():
    ''' The directory in which the bundled FAQ responses are stored '''
    return os.path.join(tmb.codedir(), MOD_NAME)


def initialize():
    ''' Called whenever we are (re)starting '''
    global TB_FUNC
    w.mkdir(datadir(), 0o755)
    TB_FUNC = token_bucket(_tb_size(), _tb_rate())


def notice_cb(sender, receiver, message):
    ''' Main tormodbot code calls into this when we're enabled and have
    received a notice message '''
    pass


def join_cb(user, chan):
    ''' Main tormodbot code calls into this when we're enabled and the given
    :class:`tmb_util.userstr.UserStr` has joined the given channel '''
    pass


def privmsg_cb(user, receiver, message):
    ''' Main tormodbot code calls into this when we're enabled and the given
    :class:`tmb_util.userstr.UserStr` has sent ``message`` (``str``) to
    ``recevier`` (``str``). The receiver can be a channel ("#foo") or a nick
    ("foo").
    '''
    global TOKEN_BUCKETS
    global TB_FUNC
    global RECENT_FAQS
    # The first two are sanity checks: that the receiver is a non-empty string
    # and that it looks like a channel name.
    # The third check is that it is one of our moderated channels. We only care
    # about those.
    receiver = receiver.lower()
    if not len(receiver) or \
            receiver[0] != '#' or \
            receiver not in tmb.mod_chans():
        return
    words = message.lower().split()
    # Determine if this is a message asking us to paste a FAQ response
    if len(words) != 2 or words[0] != '!faq':
        return
    keyword = words[1]
    # Find the response, if any. Will be None if we have no response.
    resp = _find_response(receiver, keyword)
    if not resp:
        tmb.log('{} asked for FAQ {}, but not known', user.nick, keyword)
        return
    # Make sure we haven't pasted this response too recently
    if _faq_done_recently(receiver, keyword):
        tmb.log('{} in {} done recently, so skipping', keyword, receiver)
        return
    # Add the channel to our state, if needed
    if receiver not in TOKEN_BUCKETS:
        TOKEN_BUCKETS[receiver] = None
    # Take a token from the channel and update its state
    wait_time, TOKEN_BUCKETS[receiver] = TB_FUNC(TOKEN_BUCKETS[receiver])
    # A positive wait_time indicates that we've run out of tokens, thus are
    # flooding. Just do not respond.
    if wait_time > 0:
        tmb.log(
            'Not responding to {} FAQ from {} because no more tokens',
            message, user.nick)
        return
    # Send the response
    for line in resp.split('\n'):
        line = line.strip()
        if not len(line) or line[0] == '#':
            continue
        notice(receiver, line)
    RECENT_FAQS.append((time.time(), receiver, keyword))


def _find_response(chan, keyword):
    ''' Find a response file that we have saved for channel ``chan`` that is
    keyed with ``keyword``. If no such response can be found, return ``None``,
    otherwise the response in its entirety. Note that the response could be a
    multi-line string. '''
    # List of dirs in which we might find the keyword file, ordered from most
    # specific to least. This way, we stop as soon as we find a file.
    possible_dirs = [
        os.path.join(datadir(), chan),
        os.path.join(datadir(), 'all'),
        os.path.join(_bundled_faq_dir(), chan),
        os.path.join(_bundled_faq_dir(), 'all'),
    ]
    base = keyword + '.txt'
    for d in possible_dirs:
        fname = os.path.join(d, base)
        if os.path.exists(fname) and not os.path.isdir(fname):
            with open(fname, 'rt') as fd:
                return fd.read()
    return None


def _conf_key(s):
    ''' This modules config options are all prefixed with the module name and
    an underscore. Prefix the given string with that.

    >>> conf_key('enabled')
    'faq_enabled'
    '''
    s = MOD_NAME + '_' + s
    return s


def _tb_size():
    ''' How many tokens (FAQ responses) we may burst in a channel before we
    must respect our self-imposed rate limit '''
    return int(w.config_get_plugin(_conf_key('burst')))


def _tb_rate():
    ''' The amount of time, in seconds, that must pass before the we earn
    another token '''
    return float(w.config_get_plugin(_conf_key('rate'))) / 1000


def _recent():
    ''' The amount of time, in seconds, that must pass before we will say the
    same FAQ response in the same channel again. '''
    return int(w.config_get_plugin(_conf_key('recent')))


def _faq_done_recently(chan, faq):
    ''' Returns True if we've shared the given FAQ in the given channel
    recently, otherwise False '''
    global RECENT_FAQS
    # Cleanup of any FAQs not recent anymore
    now = time.time()
    while len(RECENT_FAQS) and RECENT_FAQS[0][0] + _recent() < now:
        RECENT_FAQS.popleft()
    for ts, chan_i, faq_i in RECENT_FAQS:
        if (chan_i, faq_i) == (chan, faq):
            return True
    return False
