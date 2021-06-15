''' Module that notices new nicks saying something simple like "hello?" upon
joining and responds with a message.

The module keeps track of how many times they've seen a nick join each channel
and how many times a nick has ever sent a message in each channel. If their
number of joins and messages are sufficiently low, then we send them an
automated reply such as "this is a support channel, please ask your question."

If enabled, this module keeps track of joins and messages in all moderated
channels; however, *it will not send an automated response in channels that do
not have a response configured*.


The responses for channels are stored in weechat's configuration with the
prefix ``hello_reponse_*`` where ``*`` is the channel name.  To configure a
response for channel ``#foo``, use weechat's ``/set`` command::

    /set plugins.python.tormodbot.hello_response_#foo "This is a support channel. Please ask your question."

See the ``HELLO_*`` options in :mod:`config` for our configuration options.
'''  # noqa: E501

import weechat
# stdlib imports
import os
import sqlite3
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.lcsv import lcsv
from tmb_util.msg import notice
from . import Module

# To make calling weechat stuff take fewer characters
w = weechat


class HelloModule(Module):
    ''' See the module-level documentation '''
    NAME = 'hello'

    def __init__(self):
        #: Keep track of last time we sent a manual autoreponse in each channel
        #: so we don't spam.
        self.last_response = {}

    def _datadir(self):
        ''' Return the datadir for this specific module '''
        return os.path.join(tmb.datadir(), self.NAME)

    def _db_fname(self):
        ''' Returns the full path to the sqlite3 database for this module '''
        return os.path.join(self._datadir(), 'data.db')

    def msg_max_len(self):
        return int(w.config_get_plugin(self._conf_key('msg_max_len')))

    def hello_words(self):
        return set(lcsv(w.config_get_plugin(self._conf_key('hello_words'))))

    def new_joins(self):
        ''' Return maximum number of joins in a channel we can see from a nick
        and still consider the nick a new user '''
        return int(w.config_get_plugin(self._conf_key('new_joins')))

    def new_msgs(self):
        ''' Return maximum number of messages in a channel we can see from a
        nick and still consider the nick a new user '''
        return int(w.config_get_plugin(self._conf_key('new_msgs')))

    def interval(self):
        return int(w.config_get_plugin(self._conf_key('interval')))

    def response_for_chan(self, chan):
        ''' Returns the response we have for *chan*, or ``None`` if no
        configured response '''
        key = self._conf_key('response_' + chan)
        if not w.config_is_set_plugin(key):
            # tmb.log('{} is not set', key)
            return None
        val = w.config_get_plugin(key)
        val = val.strip()
        if not len(val):
            # tmb.log('{} has no len', key)
            return None
        return val

    def initialize(self):
        ''' Called whenever we are (re)starting '''
        w.mkdir(self._datadir(), 0o755)
        db_conn = sqlite3.connect(self._db_fname())
        joins_schema = '''
CREATE TABLE IF NOT EXISTS joins (
    nick TEXT NOT NULL,
    chan TEXT NOT NULL,
    last INTEGER,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (nick, chan)
);'''
        msgs_schema = '''
CREATE TABLE IF NOT EXISTS msgs (
    nick TEXT NOT NULL,
    chan TEXT NOT NULL,
    last INTEGER,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (nick, chan)
);'''
        ignores_schema = '''
CREATE TABLE IF NOT EXISTS ignores (
    nick TEXT NOT NULL,
    chan TEXT NOT NULL,
    ignore BOOLEAN DEFAULT 0 CHECK (ignore IN (0, 1)),
    PRIMARY KEY (nick, chan)
);
'''
        with db_conn:
            db_conn.execute(joins_schema)
            db_conn.execute(msgs_schema)
            db_conn.execute(ignores_schema)
        db_conn.close()

    def join_cb(self, user, chan):
        ''' Main tormodbot code calls into this when we're enabled and the
        given :class:`tmb_util.userstr.UserStr` has joined the given channel
        '''
        self._update_join_table(user.nick, chan)

    def privmsg_cb(self, user, receiver, message, is_opmod):
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
        self._update_msgs_table(user.nick, receiver)
        # If we don't have a configured response for this channel, then there's
        # no reason going any farther, because we have nothing to say.
        response = self.response_for_chan(receiver)
        if not response:
            # tmb.log('No response for {}', receiver)
            return
        # If we sent something to this channel too recently, don't let
        # ourselves spam
        if self._too_soon(receiver):
            # tmb.log('It\'s too soon to autorespond in {} again', receiver)
            return
        # Okay we should do something about this message. Act differently based
        # on what type of message it looks like
        if self._is_manual_command(message):
            self._handle_manual_command(user, receiver, message)
            return
        if self._seems_like_hello_msg(message):
            self._handle_hello_msg(user, receiver, message)
            return

    def _handle_manual_command(self, user, chan, message):
        # should have been checked already
        if not self._is_manual_command(message):
            return
        words = message.lower().strip().split()
        # If we don't have a configured response for this channel, then there's
        # no reason going any farther, because we have nothing to say.
        response = self.response_for_chan(chan)
        if not response:
            # tmb.log('No response for {}', receiver)
            return
        # If there's a nick in the !hello command like '!hello pastly', then
        # direct the response to that nick
        if len(words) == 2:
            response = '{}: {}'.format(words[1], response)
        notice(chan, response)
        self.last_response[chan] = time.time()

    def _handle_hello_msg(self, user, chan, message):
        ''' *message* has been determined to be a "hello?" type message. Handle
        our response to that as necessary '''
        # If no response for this channel, don't do anything. This should have
        # been already checked, but check again
        response = self.response_for_chan(chan)
        if not response:
            return
        # If this user should be ignored, return early
        if self._should_ignore(user.nick, chan):
            # tmb.log('{} should be ignored in {}', user.nick, chan)
            return
        # If the message itself doesn't seem like a "hello?" type message,
        # return early
        if not self._seems_like_hello_msg(message):
            # tmb.log('"{}" is not a hello msg', message)
            return
        # If the user's history does not suggest they need an automated
        # response, return early
        if not self._seems_like_new_user(user.nick, chan):
            # tmb.log('{} is not a new user', user.nick)
            return
        # Yup. We should send the automated response.
        response = '{}: {}'.format(user.nick, response)
        notice(chan, response)
        self.last_response[chan] = time.time()
        self._update_ignore_table(user.nick, chan, True)
        return

    def _update_join_table(self, nick, chan):
        ''' Someone has joined a channel, so update the table accordingly '''
        db_conn = sqlite3.connect(self._db_fname())
        # SQL to insert the row if possible
        insert = '''
INSERT OR IGNORE INTO joins (nick, chan) VALUES (?, ?);
'''
        # Now we definitely have a row, so increment the count and update the
        # last join time
        increment = '''
UPDATE joins
SET count = count + 1, last = ?
WHERE nick = ? AND chan = ?;
'''
        with db_conn:
            db_conn.execute(insert, (nick, chan))
            db_conn.execute(increment, (int(time.time()), nick, chan))
        db_conn.close()

    def _update_msgs_table(self, nick, chan):
        ''' Someone has sent a message in channel, so update the table
        accordingly '''
        db_conn = sqlite3.connect(self._db_fname())
        # SQL to insert the row if possible
        insert = '''
INSERT OR IGNORE INTO msgs (nick, chan) VALUES (?, ?);
'''
        # Now we definitely have a row, so increment the count and update the
        # last msg time
        increment = '''
UPDATE msgs
SET count = count + 1, last = ?
WHERE nick = ? AND chan = ?;
'''
        with db_conn:
            db_conn.execute(insert, (nick, chan))
            db_conn.execute(increment, (int(time.time()), nick, chan))
        db_conn.close()

    def _update_ignore_table(self, nick, chan, should_ignore):
        db_conn = sqlite3.connect(self._db_fname())
        # SQL to insert the row if possible
        insert = '''
INSERT OR IGNORE INTO ignores (nick, chan) VALUES (?, ?);
'''
        update = '''
UPDATE ignores
SET ignore = ? WHERE nick = ? AND chan = ?;
'''
        with db_conn:
            db_conn.execute(insert, (nick, chan))
            db_conn.execute(update, (1 if should_ignore else 0, nick, chan))
        db_conn.close()

    def _seems_like_hello_msg(self, s):
        ''' Return whether or not the given message *s* seems to be a "hello
        message" that would indicate a copy/paste response may be necessary '''
        s = s.lower().strip()
        # Probably not a 'hello?' if more than 20 chars
        if len(s) >= self.msg_max_len():
            return False
        # Remove all non-alphanum chars, and keep spaces for word boundaries
        s = ''.join([c for c in s if c.isalnum() or c == ' '])
        # Check if any of the words in the message are a "hello?" word
        hello_words_ = self.hello_words()
        for word in s.split():
            if word in hello_words_:
                return True
        return False

    def _seems_like_new_user(self, nick, chan):
        ''' Return whether or not this user seems new enough to deserve an
        automated response if they sent a "hello?" message '''
        seems_new = True
        joins_query = 'SELECT count FROM joins WHERE nick = ? AND chan = ?;'
        msgs_query = 'SELECT count FROM msgs WHERE nick = ? AND chan = ?;'
        db_conn = sqlite3.connect(self._db_fname())
        db_conn.row_factory = sqlite3.Row
        with db_conn:
            for row in db_conn.execute(joins_query, (nick, chan)):
                # should just be 0 or 1 row, but whatever do it "multiple
                # times" in a for loop
                if row['count'] > self.new_joins():
                    seems_new = False
                    break
            for row in db_conn.execute(msgs_query, (nick, chan)):
                # should just be 0 or 1 row, but whatever do it "multiple
                # times" in a for loop
                if row['count'] > self.new_msgs():
                    seems_new = False
                    break
        db_conn.close()
        return seems_new

    def _should_ignore(self, nick, chan):
        ''' Return whether or not we should ignore this nick in this channel,
        allowing them to send "hello?" messages '''
        should_ignore = False
        db_conn = sqlite3.connect(self._db_fname())
        db_conn.row_factory = sqlite3.Row
        query = 'SELECT ignore FROM ignores WHERE nick = ? AND chan = ?;'
        with db_conn:
            for row in db_conn.execute(query, (nick, chan)):
                # should just be 0 or 1 row, but do it "multiple times" anyway
                should_ignore = not not row['ignore']
        db_conn.close()
        return should_ignore

    def _is_manual_command(self, message):
        message = message.lower().strip()
        words = message.split()
        # Either '!hello' or '!hello pastly' should be the message
        if len(words) != 1 and len(words) != 2:
            return False
        return words[0] == '!hello'

    def _too_soon(self, chan):
        ''' Return whether or not it's too soon to send the automated response
        on *chan* again '''
        if chan not in self.last_response:
            # no record of saying our response in this channel, so not too soon
            return False
        now = time.time()
        if self.last_response[chan] + self.interval() > now:
            # Not enough time has passed, so too soon
            return True
        return False
