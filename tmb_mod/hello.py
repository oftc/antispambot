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

#: The name of this module (wow such good comment)
MOD_NAME = 'hello'
# To make calling weechat stuff take fewer characters
w = weechat
#: sqlite3 database for this module. Use :meth:`db_fname` to get the real full
#: path; this here is relative to this module's data directory
DB_FNAME = 'data.db'


def enabled():
    ''' Main tormodbot code calls this to see if this module is enabled '''
    a = w.config_string_to_boolean(w.config_get_plugin(_conf_key('enabled')))
    return a


def datadir():
    ''' Return the datadir for this specific module '''
    return os.path.join(tmb.datadir(), MOD_NAME)


def db_fname():
    ''' Returns the full path to the sqlite3 database for this module '''
    return os.path.join(datadir(), DB_FNAME)


def msg_max_len():
    return int(w.config_get_plugin(_conf_key('msg_max_len')))


def hello_words():
    return set(lcsv(w.config_get_plugin(_conf_key('hello_words'))))


def new_joins():
    ''' Return maximum number of joins in a channel we can see from a nick and
    still consider the nick a new user '''
    return int(w.config_get_plugin(_conf_key('new_joins')))


def new_msgs():
    ''' Return maximum number of messages in a channel we can see from a nick
    and still consider the nick a new user '''
    return int(w.config_get_plugin(_conf_key('new_msgs')))


def response_for_chan(chan):
    ''' Returns the response we have for *chan*, or ``None`` if no configured
    response '''
    key = _conf_key('response_' + chan)
    if not w.config_is_set_plugin(key):
        # tmb.log('{} is not set', key)
        return None
    val = w.config_get_plugin(key)
    val = val.strip()
    if not len(val):
        # tmb.log('{} has no len', key)
        return None
    return val


def initialize():
    ''' Called whenever we are (re)starting '''
    w.mkdir(datadir(), 0o755)
    db_conn = sqlite3.connect(db_fname())
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


def notice_cb(sender, receiver, message):
    ''' Main tormodbot code calls into this when we're enabled and have
    received a notice message '''
    pass


def join_cb(user, chan):
    ''' Main tormodbot code calls into this when we're enabled and the given
    :class:`tmb_util.userstr.UserStr` has joined the given channel '''
    _update_join_table(user.nick, chan)


def privmsg_cb(user, receiver, message):
    ''' Main tormodbot code calls into this when we're enabled and the given
    :class:`tmb_util.userstr.UserStr` has sent ``message`` (``str``) to
    ``recevier`` (``str``). The receiver can be a channel ("#foo") or a nick
    ("foo").
    '''
    # The first two are sanity checks: that the receiver is a non-empty string
    # and that it looks like a channel name.
    # The third check is that it is one of our moderated channels. We only care
    # about those.
    receiver = receiver.lower()
    if not len(receiver) or \
            receiver[0] != '#' or \
            receiver not in tmb.mod_chans():
        return
    _update_msgs_table(user.nick, receiver)
    # If we don't have a configured response for this channel, then there's no
    # reason going any farther, because we have nothing to say.
    response = response_for_chan(receiver)
    if not response:
        # tmb.log('No response for {}', receiver)
        return
    # If this user should be ignored, return early
    if _should_ignore(user.nick, receiver):
        # tmb.log('{} should be ignored in {}', user.nick, receiver)
        return
    # If the message itself doesn't seem like a "hello?" type message, return
    # early
    if not _seems_like_hello_msg(message):
        # tmb.log('"{}" is not a hello msg', message)
        return
    # If the user's history does not suggest they need an automated response,
    # return early
    if not _seems_like_new_user(user.nick, receiver):
        # tmb.log('{} is not a new user', user.nick)
        return
    # Yup. We should send the automated response.
    response = '{}: {}'.format(user.nick, response)
    notice(receiver, response)
    _update_ignore_table(user.nick, receiver, True)
    return


def _conf_key(s):
    ''' This modules config options are all prefixed with the module name and
    an underscore. Prefix the given string with that.

    >>> conf_key('enabled')
    'antiflood_enabled'
    '''
    s = MOD_NAME + '_' + s
    return s


def _update_join_table(nick, chan):
    ''' Someone has joined a channel, so update the table accordingly '''
    db_conn = sqlite3.connect(db_fname())
    # SQL to insert the row if possible
    insert = '''
INSERT OR IGNORE INTO joins (nick, chan) VALUES (?, ?);
'''
    # Now we definitely have a row, so increment the count and update the last
    # join time
    increment = '''
UPDATE joins
SET count = count + 1, last = ?
WHERE nick = ? AND chan = ?;
'''
    with db_conn:
        db_conn.execute(insert, (nick, chan))
        db_conn.execute(increment, (int(time.time()), nick, chan))
    db_conn.close()


def _update_msgs_table(nick, chan):
    ''' Someone has sent a message in channel, so update the table accordingly
    '''
    db_conn = sqlite3.connect(db_fname())
    # SQL to insert the row if possible
    insert = '''
INSERT OR IGNORE INTO msgs (nick, chan) VALUES (?, ?);
'''
    # Now we definitely have a row, so increment the count and update the last
    # msg time
    increment = '''
UPDATE msgs
SET count = count + 1, last = ?
WHERE nick = ? AND chan = ?;
'''
    with db_conn:
        db_conn.execute(insert, (nick, chan))
        db_conn.execute(increment, (int(time.time()), nick, chan))
    db_conn.close()


def _update_ignore_table(nick, chan, should_ignore):
    db_conn = sqlite3.connect(db_fname())
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


def _seems_like_hello_msg(s):
    ''' Return whether or not the given message *s* seems to be a "hello
    message" that would indicate a copy/paste response may be necessary '''
    s = s.lower().strip()
    # Probably not a 'hello?' if more than 20 chars
    if len(s) >= msg_max_len():
        return False
    # Remove all non-alphanum chars, and keep spaces for word boundaries
    s = ''.join([c for c in s if c.isalnum() or c == ' '])
    # Check if any of the words in the message are a "hello?" word
    hello_words_ = hello_words()
    for word in s.split():
        if word in hello_words_:
            return True
    return False


def _seems_like_new_user(nick, chan):
    ''' Return whether or not this user seems new enough to deserve an
    automated response if they sent a "hello?" message '''
    seems_new = True
    joins_query = 'SELECT count FROM joins WHERE nick = ? AND chan = ?;'
    msgs_query = 'SELECT count FROM msgs WHERE nick = ? AND chan = ?;'
    db_conn = sqlite3.connect(db_fname())
    db_conn.row_factory = sqlite3.Row
    with db_conn:
        for row in db_conn.execute(joins_query, (nick, chan)):
            # should just be 0 or 1 row, but whatever do it "multiple times" in
            # a for loop
            if row['count'] > new_joins():
                seems_new = False
                break
        for row in db_conn.execute(msgs_query, (nick, chan)):
            # should just be 0 or 1 row, but whatever do it "multiple times" in
            # a for loop
            if row['count'] > new_msgs():
                seems_new = False
                break
    db_conn.close()
    return seems_new


def _should_ignore(nick, chan):
    ''' Return whether or not we should ignore this nick in this channel,
    allowing them to send "hello?" messages '''
    should_ignore = False
    db_conn = sqlite3.connect(db_fname())
    db_conn.row_factory = sqlite3.Row
    query = 'SELECT ignore FROM ignores WHERE nick = ? AND chan = ?;'
    with db_conn:
        for row in db_conn.execute(query, (nick, chan)):
            # should just be 0 or 1 row, but do it "multiple times" anyway
            should_ignore = not not row['ignore']
    db_conn.close()
    return should_ignore
