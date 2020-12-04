'''
FAQ module
==========

If enabled, we can read a library of FAQ responses from plain-text files on
disk, both bundled with tormodbot and ones the operator wrote themself.

Usage
-----

In public (in a moderated channel)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A FAQ query can take one of two forms:

.. code-block:: text

    # public usage
    !faq
    !faq <keyword>


- A simple ``!faq`` in public will case us to list, in public, all keywords
  we know about in that channel.

- ``!faq foo``, where *foo* is a keyword known in that channel, will case us to
  respond with the FAQ response for *foo*. If we do not have a response, we
  respond saying so and include a link to the configured source code
  repository.

If more than one argument is provided, we behave as if we received just
``!faq``.


In private (via a private message)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A FAQ query can take one of four forms:

.. code-block:: text

    # private usage
    !faq
    !faq <#chan>
    !faq <keyword>
    !faq <#chan> <keyword>

- A simple ``!faq`` will case us to behave as if we received ``!faq
  all about``, i.e.  we respond with text regarding this bot.
- ``!faq #bar`` will case us to list all keywords we know about in *#bar*.
- ``!faq foo`` will case us to behave as if we received ``!faq all foo``.
- ``!faq #bar foo`` will case us to respond with the FAQ response for *foo* in
  *#bar*.

In all the above cases where a channel can be specified, instead you can
provide ``all`` to search the globally known FAQ responses only, as opposed to
responses known to a specific channel *and* those known globally.

If more than two arguments are provided, we behave as if we received just
``!faq``.

If we cannot find a FAQ response, we respond saying so and include a link to
the configured source code repository.

.. note::

    If just one argument is provided and it is not ``all`` or a moderated
    channel, it is treated as a keyword. Assume *#baz* is **not** a moderated
    channel.  That means while ``!faq #baz`` *looks like* we should respond
    with the list of known keywords in *#baz*, since we don't have **any**
    (it's not moderated), we treat it as a keyword and act as if we received
    ``!faq all #baz``.

FAQ response file format
------------------------

FAQ response files can be multiple lines; however, blank lines are ignored and
leading/trailing whitespace is stripped. Comment lines -- those whose first
non-whitespace character is '#' -- are also ignored. There is no such thing as
an end-of-line comment.

.. code-block:: text

    This is the first line of a FAQ response.

    This line is printed right after the first, with no blank line in between.
    # This is a comment, thus isn't printed.
    This entire line is printed # because this isn't a comment.

Regardless of the length of the lines in the input file, *paragraphs* are
wrapped to 400-character-length lines. Paragraphs are separated by a blank
line.

.. code-block:: text

    This is the first paragraph.
    This is the second sentence
    of the first paragraph, and these
    five lines appear as a single
    IRC message.

    This is the second paragraph and
    would start a second IRC message.

FAQ response search order
-------------------------

FAQ responses can be specific to a moderated channel, or they can be general
for all channels. Assuming the default WeeChat data directory, when searching
for the response to FAQ keyword ``bar`` in channel ``#foo``, we search in the
following places **in order** and select the first FAQ response found:

.. code-block:: text

    ~/.weechat/tmb_data/faq/#foo/bar.txt
    ~/.weechat/tmb_data/faq/all/bar.txt
    ~/.weechat/python/faq/#foo/bar.txt
    ~/.weechat/python/faq/all/bar.txt

**Put your FAQ responses in ``~/.weechat/tmb_data/faq``**. If you believe your
FAQ response should be bundled with the code, make a pull request, get it
merged, and then you can pull the latest code and have tne FAQ response in
``~/.weechat/python/faq``.

The motivation for this order is to allow the operator to have a general
keyword with the same response in all channels, but override that response in
specific channels. Additionally, any FAQ responses that come bundled with this
code will be overridden by *any* operator-created FAQ response that uses the
same keyword.

Keywords
--------

The keyword is not case-sensitive, has no spaces, and otherwise lacks any
characters that would constitute an invalid filename.

Anti-spam
---------

To limit the extent to which we can be used for a spam tool, we rate limits
ourself in *each* moderated channel. See the ``FAQ_*`` options in :mod:`config`
for the options how many responses we can *burst* in a channel, as well as the
steady-state *rate* at which we will send responses in a channel. Additionally,
we won't give the same FAQ response in a channel if we have done so *recently*.



'''
import weechat
# stdlib imports
import glob
import os
import time
from collections import deque
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.msg import notice
from tmb_util.tokenbucket import token_bucket
from tmb_util.wordwrap import wrap_text
from . import Module


# To make calling weechat stuff take fewer characters
w = weechat
#: Reponse template to give when we do not know the answer. The arguments, in
#: order:
#: - The channel
#: - The unknown keyword
#: - The URL at which to report bugs
UNKNOWN_FAQ_RESP = 'I do not know about "{1}" in {0}. If I should, please '\
    'open a ticket at {2}. Also try sending me a private message with '\
    '"!faq {0}".'


class FAQModule(Module):
    ''' See the module-level documentation '''
    NAME = 'faq'

    def __init__(self):
        #: Store per-``chan`` token buckets so we prevent ourselves from
        #: flooding when used as a toy
        self.token_buckets = {}
        #: Function to call every time we send a message to take away a token
        #: from that channel's bucket. The function takes the channels's state
        #: as an argument and returns ``(wait_time, new_state)``. ``wait_time``
        #: is the amount of time we need to wait until we would have a non-zero
        #: number of tokens left (so if we currently have tokens for this
        #: channel, ``wait_time`` is 0), and ``new_state`` is the channels's
        #: updated state that should be passed in next time.
        self.tb_func = token_bucket(self._tb_size(), self._tb_rate())
        #: A FIFO list of responses we've recently made. This is used to not
        #: repeat ourselves in case we are asked to paste the same FAQ rapidly.
        #:
        #: Append responses that you are taking to the **right** and cleanup
        #: old ones from the **left**.
        #:
        #: The items in this queue are a tuple::
        #:
        #:    (timestamp, destination, channel, keyword)
        #:
        #: If this fact changes, then :meth:`_faq_done_recently` needs to be
        #: updated
        self.recent_faqs = deque()

    def initialize(self):
        ''' Called whenever we are (re)starting '''
        w.mkdir(self._datadir(), 0o755)
        self.tb_func = token_bucket(self._tb_size(), self._tb_rate())

    def _datadir(self):
        ''' Return the datadir for this specific module '''
        return os.path.join(tmb.datadir(), self.NAME)

    def _bundled_faq_dir(self):
        ''' The directory in which the bundled FAQ responses are stored '''
        return os.path.join(tmb.codedir(), self.NAME)

    def _tb_size(self):
        ''' How many tokens (FAQ responses) we may burst in a channel before we
        must respect our self-imposed rate limit '''
        return int(w.config_get_plugin(self._conf_key('burst')))

    def _tb_rate(self):
        ''' The amount of time, in seconds, that must pass before the we earn
        another token '''
        return float(w.config_get_plugin(self._conf_key('rate'))) / 1000

    def _recent(self):
        ''' The amount of time, in seconds, that must pass before we will say
        the same FAQ response in the same channel again. '''
        return int(w.config_get_plugin(self._conf_key('recent')))

    def _unknown_resp(self):
        ''' The response to give when there is no configured response '''
        return w.config_get_plugin(self._conf_key('unknown'))

    def _record_resp(self, dest, chan, key):
        '''
        Record the fact that we are saying something in response to "!faq chan
        key" (or similar, as both *chan* and *key* can be None) in *dest* right
        now. *dest* can be a channel or a user's nick if sending them a PM.

        Before recording that, however, first check if we even should send to
        *dest* by spending a token from its token bucket. If the token bucket
        indicates we are flooding, return False and do NOT record a response as
        going out. Otherwise returrn True after recording the response going
        out.  '''
        if dest not in self.token_buckets:
            self.token_buckets[dest] = None
        wait_time, self.token_buckets[dest] = \
            self.tb_func(self.token_buckets[dest])
        if wait_time > 0:
            tmb.log(
                'Indicating we shouldn\'t respond to {}/{} because no more '
                'tokens for {}', chan, key, dest)
            return False
        self.recent_faqs.append((time.time(), dest, chan, key))
        return True

    def _privmsg_pm_cb(self, user, receiver, message):
        ''' PRIVMSG from :class:`tmb_util.userstr.UserStr` to us via PM.  '''
        if receiver != tmb.my_nick():
            return
        words = message.lower().split()
        if words[0] != '!faq':
            return
        if len(words) == 1 or len(words) > 3:
            chan, key = None, None
        elif len(words) == 2:
            if words[1] == 'all' or words[1] in tmb.mod_chans():
                chan, key = words[1], None
            else:
                chan, key = 'all', words[1]
        else:
            chan, key = words[1:]
        resp = self._find_response(chan, key, True)
        if self._faq_done_recently(user.nick, chan, key) or \
                not self._record_resp(user.nick, chan, key):
            return
        _send_resp(user.nick, resp)

    def _privmsg_modchan_cb(self, user, receiver, message):
        if receiver not in tmb.mod_chans():
            return
        words = message.lower().split()
        if words[0] != '!faq':
            return
        if len(words) == 1 or len(words) > 2:
            chan, key = receiver, None
        else:
            chan, key = receiver, words[1]
        resp = self._find_response(chan, key, False)
        if self._faq_done_recently(receiver, chan, key) or \
                not self._record_resp(receiver, chan, key):
            return
        _send_resp(receiver, resp)

    def privmsg_cb(self, user, receiver, message):
        ''' Main tormodbot code calls into this when we're enabled and the
        given :class:`tmb_util.userstr.UserStr` has sent ``message`` (``str``)
        to ``recevier`` (``str``). The receiver can be a channel ("#foo") or a
        nick ("foo").  '''
        if not len(message) or not message.lower().split()[0] == '!faq':
            return
        receiver = receiver.lower()
        if receiver == tmb.my_nick():
            return self._privmsg_pm_cb(user, receiver, message)
        return self._privmsg_modchan_cb(user, receiver, message)

    def _faq_done_recently(self, dest, chan, key):
        ''' Returns True if we've given *chan's* *key* FAQ response in *dest*
        recently, otherwise False.

        Both chan and key can be None without it being an error.
        '''
        # Cleanup of any FAQs not recent anymore
        now = time.time()
        while len(self.recent_faqs) and \
                self.recent_faqs[0][0] + self._recent() < now:
            self.recent_faqs.popleft()
        # Check if the given FAQ was done recently
        for ts, dest_i, chan_i, key_i in self.recent_faqs:
            if (dest_i, chan_i, key_i) == (dest, chan, key):
                return True
        return False

    def _search_dirs(self, chan):
        ''' Return the ordered list of dirs in which we should look for FAQ
        responses. *chan* is either a '#channel' or 'all' '''
        # if chan is 'all', then the list will contain duplicate items, which
        # should be fine for how this function is currently used. Just a little
        # wasteful
        return [
            os.path.join(self._datadir(), chan),
            os.path.join(self._datadir(), 'all'),
            os.path.join(self._bundled_faq_dir(), chan),
            os.path.join(self._bundled_faq_dir(), 'all'),
        ]

    def _list_keywords_in_chan(self, chan):
        ''' Look up and return a list of all keywords we know about in *chan*,
        which is either a '#channel' or 'all' '''
        return {
            # Convert 'a/b/c.txt' to 'c'
            os.path.basename(os.path.splitext(f)[0])
            # For each file in each search directory
            for d in self._search_dirs(chan)
            for f in glob.iglob(os.path.join(d, '*.txt'))
        }

    def _find_response(self, chan, key, is_pm):
        ''' Find the appropriate response to keyword *key* in *chan* and return
        it, or ``None`` if none is found.

        - *chan*: ``#chan`` a moderated channel, ``all``, or ``None``.
        - *key*: some keyword, or ``None``.
        - *is_pm*: whether or not the FAQ command came as a PM. We want to
        know, because we behave different in certain situations based on how we
        got the message.

        The return value is a single string, but it may have multiple lines. It
        may or may not have a trailing \n; the caller must handle each case
        gracefully.
        '''
        # Empty '!faq` request
        if chan is None and key is None:
            # if it was public, then there must be a channel
            assert is_pm
            return self._ondisk_response('all', 'about') or \
                UNKNOWN_FAQ_RESP.format('all', 'about', tmb.code_url())
        # Only receieved a keyword. This shouldn't happen?
        elif chan is None:
            assert key is not None
            tmb.log(
                'Asked to find response to {} without a channel. Should be '
                'impossible. Pretending channel is all', key)
            return self._ondisk_response('all', key) or \
                UNKNOWN_FAQ_RESP.format('all', key, tmb.code_url())
        # Only receieved chan or 'all'
        elif key is None:
            assert chan is not None
            keys = list(self._list_keywords_in_chan(chan))
            keys.sort()
            if chan == 'all':
                return 'Globally known FAQs: ' + ' '.join(keys)
            return 'FAQs known in ' + chan + ': ' + ' '.join(keys)
        # Both a chan (or 'all') and keyword
        assert chan is not None
        assert key is not None
        return self._ondisk_response(chan, key) or \
            UNKNOWN_FAQ_RESP.format(chan, key, tmb.code_url())

    def _ondisk_response(self, chan, keyword):
        ''' Find a response file that we have saved for channel ``chan`` that
        is keyed with ``keyword``. If no such response can be found, return
        ``None``, otherwise the response in its entirety. Note that the
        response could be a multi-line string. '''
        # List of dirs in which we might find the keyword file, ordered from
        # most specific to least. This way, we stop as soon as we find a file.
        possible_dirs = self._search_dirs(chan)
        base = keyword + '.txt'
        for d in possible_dirs:
            fname = os.path.join(d, base)
            if os.path.exists(fname) and not os.path.isdir(fname):
                with open(fname, 'rt') as fd:
                    s = ''
                    for line in fd:
                        line = line.strip()
                        if len(line) and line[0] == '#':
                            continue
                        # either line is '', which is fine and we do indeed
                        # want to add a newline, or it's not '' but it
                        # definitely is NOT a comment.
                        s += line + '\n'
                    return s
        return None


def _send_resp(dest, resp):
    ''' Send the multi-line *resp* string to the nick or channel *dest* '''
    if not resp or not dest:
        return
    for line in wrap_text(resp, 400):
        line = line.strip()
        if not len(line):
            continue
        notice(dest, line)
