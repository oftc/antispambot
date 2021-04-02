''' Chanserv utils

We provide helper interfaces for quiet/akick lists across multiple channels.
Additionally we provide a way to temporarily quick/akick.
'''
import weechat
# stdlib imports
from argparse import ArgumentParser
import os
import sqlite3
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util import userlist
from tmb_util.lcsv import lcsv
from tmb_util.msg import msg

# To make calling weechat stuff take fewer characters
w = weechat
#: All valid n!u@h patterns on which we can act
ALL_PATTERNS = {
    '*nick', 'nick', 'nick*', '*nick*',
    '*user', 'user', 'user*', '*user*',
    '*host', 'host', 'host*', '*host*',
}
#: sqlite3 database for us. Use :meth:`db_fname` to get the real full path;
#: this here is relative to the data directory
DB_FNAME = 'chanserv.db'
#: For permanent bans, this is the timestamp at which the ban expires
PERMANENT_TS = 99999999999
#: How long a temporary ban should last, in days
TEMP_BAN_DAYS = 30
#: Number of seconds in a day
# SECS_IN_DAY = 1  # for debugging purposes
SECS_IN_DAY = 60 * 60 * 24
#: Query string for inserting one ban (quiet or akick) into table
INSERT_QUERY = '''
INSERT INTO bans (glob, chan, is_quiet, expire) VALUES (?, ?, ?, ?);
'''
FIND_OLD_QUERY = '''
SELECT rowid, * FROM bans WHERE expire < ? AND deleted = 0;
'''
#: Weechat timer hook on our reoccuriring event for deleting old bans
DELETE_BAN_TIMER_HOOK = None
#: Interval, in seconds, with which we check for old bans that we should
#: delete. Ideally we wouldn't poll, but if we must, then ideally we wouldn't
#: poll so often. It has been lowered from hourly to this because the
#: botabuse module issues very short mutes through us. Also now the joinspam
#: module issues bans >1h but <1d.
DELETE_BAN_INTERVAL = 10
# DELETE_BAN_INTERVAL = 60 * 60


def db_fname():
    return os.path.join(tmb.datadir(), DB_FNAME)


def _pattern_to_glob_string(pat):  # noqa: C901
    ''' Convert pattern *pat* into a "glob string" for chanserv.

    ::

        nick --> {}!*@*
        nick* --> {}*!*@*
        *nick --> *{}!*@*
        *nick* --> *{}*!*@*

    And likewise for user- and host-based patterns. If *pat* is not a valid
    pattern, return ``None``.
    '''
    if pat not in ALL_PATTERNS:
        return None
    # here we go. can't think of anything better at the moment
    if pat == 'nick':
        return '{}!*@*'
    elif pat == 'nick*':
        return '{}*!*@*'
    elif pat == '*nick':
        return '*{}!*@*'
    elif pat == '*nick*':
        return '*{}*!*@*'
    elif pat == 'user':
        return '*!{}@*'
    elif pat == 'user*':
        return '*!{}*@*'
    elif pat == '*user':
        return '*!*{}@*'
    elif pat == '*user*':
        return '*!*{}*@*'
    elif pat == 'host':
        return '*!*@{}'
    elif pat == 'host*':
        return '*!*@{}*'
    elif pat == '*host':
        return '*!*@*{}'
    elif pat == '*host*':
        return '*!*@*{}*'
    # either a programming error in the above mash of strings, or some new
    # pattern in ALL_PATTERNS that we didn't account for
    return None


def _parser():
    p = ArgumentParser()
    p.add_argument('cmd', choices=['quiet', 'akick'])
    # comma-seperated list of '#chan1,#chan2' or 'all'
    p.add_argument('chans', type=str)
    p.add_argument('nick', type=str)
    p.add_argument('pats', type=str)
    p.add_argument('reason', type=str, nargs='+')
    # If given, ignore --duration and make the ban permanent
    p.add_argument('-p', '--permanent', action='store_true')
    # Duration, in days, of a temporary ban
    p.add_argument('-d', '--duration', type=float, default=TEMP_BAN_DAYS)
    return p


def _try_parse(p, s):
    try:
        return p.parse_args(s.split())
    except:  # noqa: E722, for whatever reason can't even catch Exception in weechat
        tmb.log('Unable to parse chanserv command "{}"', s)
        return None


def _handle_command(master_nick, args):
    ''' *master* told use to execute a valid command, described in *args*. Do
    it and return the number of new bans we create '''
    num_new_bans = 0
    # Get channels, and make sure we ignore any that aren't moderated chans
    chans = args.chans
    ignored_chans = {c for c in chans if c not in tmb.mod_chans()}
    chans = {c for c in chans if c not in ignored_chans}
    if len(ignored_chans):
        tmb.log('Ignoring non-moderated channels {}', ', '.join(ignored_chans))
    # Get the :class:`UserStr` for the given nick, if possible
    user = userlist.nick_to_user(args.nick)
    if not user:
        tmb.log(
            'Nick {} has no known n!u@h, so will have to ignore non-nick '
            'patterns', args.nick)
    # Get only the valid patterns, then remove non-nick pats if needed, and log
    # about all ignored patterns
    pats = {p for p in args.pats if p in ALL_PATTERNS}
    if not user:
        pats = {p for p in pats if 'nick' in p}
    ignored_pats = {p for p in pats if p not in args.pats}
    if len(ignored_pats):
        tmb.log('Ignoring patterns: {}', ', '.join(ignored_pats))
    now = int(time.time())
    # get expire time for each of the bans
    if args.permanent:
        expire = PERMANENT_TS
    else:
        expire = now + args.duration * SECS_IN_DAY
    expire = int(expire)
    # Now act on all the valid patterns that are left
    db_conn = sqlite3.connect(db_fname())
    with db_conn:
        # execute each of the bans
        for pat in pats:
            # get glob for this ban pattern
            glob = _pattern_to_glob_string(pat)
            if 'nick' in pat:
                glob = glob.format(args.nick.lower())
            elif 'user' in pat:
                glob = glob.format(user.user)
            elif 'host' in pat:
                glob = glob.format(user.host)
            else:
                assert None, 'nick, user, or host must have been in glob'
            # here we go, do it for each channel
            for chan in chans:
                s = '{cmd} {chan} add {glob} {reason}'.format(
                    cmd=args.cmd, chan=chan,
                    glob=glob, reason=args.reason)
                msg(tmb.chanserv_user().nick, s)
                tmb.log(s + ' (by {})'.format(master_nick))
                # save it in the db
                db_conn.execute(INSERT_QUERY, (
                    glob, chan, 1 if args.cmd == 'quiet' else 0, expire))
                num_new_bans += 1
    db_conn.close()
    return num_new_bans


def internal_handle_command(
        nick, chans, pats, reason, is_quiet=False, is_permanent=False,
        duration=TEMP_BAN_DAYS):
    ''' Internal version of :meth:`handle_command` for our own code to issue
    akicks/quiets.

    :param nick: Nick to akick/quiet. We'll look up the n!u@h string.
    :param chans: List of channels in which to akick/quiet. If 'all' appears in
        the list, it will be replaced with all moderated channels.
    :param pats: List of hostmask patterns such as 'nick', 'user*', '*host',
        and '*host*'.
    :param reason: String reason for the akick/quiet. A reason must be
        provided.
    :param is_quiet: ``True`` if this is a quiet/mute. ``False`` means this is
        a ban/akick.
    :param is_permanent: Whether or not the akick/quiet is permanent. If True,
        overrides whatever ``duration`` is set to.
    :param duration: The duration of the ban, in days. Gets overridden by
        ``is_permanent`` if it is True.

    :returns: ``True`` if we were able to do *any* akick/quiet, otherwise
        ``False``.
    '''
    reason = reason.strip()
    if not len(chans) or not len(pats) or not len(reason) or not len(nick):
        return False
    s = '{act} {chans_csv} {n} {pats_csv} {r} {perm} {dur}'.format(
        act='quiet' if is_quiet else 'akick',
        chans_csv=lcsv(chans),
        n=nick,
        pats_csv=lcsv(pats),
        r=reason,
        perm='--permanent' if is_permanent else '',
        dur='--duration %.9f' % (duration,) if not is_permanent else '')
    args = _try_parse(_parser(), s)
    if not args:
        # error should already be logged
        return False
    args.pats = lcsv(args.pats)
    args.chans = lcsv(args.chans)
    args.reason = ' '.join(args.reason) + ' (tmb)'
    num_new = _handle_command(tmb.my_nick(), args)
    return num_new > 0


def handle_command(user, where, message):
    ''' Main tormodbot code calls into this when we're enabled and the given
    :class:`tmb_util.userstr.UserStr` has sent us a command stored in
    ``message`` (``str``), via ``where`` (``str``, either a "#channel" or our
    nick if PM). It has already been verified that the user is a master and
    that ``where`` is a proper place.
    '''
    args = _try_parse(_parser(), message)
    if not args:
        # error message already logged
        return w.WEECHAT_RC_OK
    args.pats = lcsv(args.pats)
    if args.chans == 'all':
        args.chans = tmb.mod_chans()
    else:
        args.chans = lcsv(args.chans)
    args.reason = ' '.join(args.reason) + ' (tmb)'
    _handle_command(user.nick, args)
    return w.WEECHAT_RC_OK


def initialize():
    ''' Called whenever we are (re)starting '''
    db_conn = sqlite3.connect(db_fname())
    bans_schema = '''
CREATE TABLE IF NOT EXISTS bans (
    glob TEXT NOT NULL,
    chan TEXT NOT NULL,
    expire INTEGER NOT NULL,
    is_quiet BOOLEAN NOT NULL CHECK (is_quiet IN (0, 1)),
    deleted BOOLEAN DEFAULT 0 CHECK (deleted IN (0, 1))
);'''
    with db_conn:
        db_conn.execute(bans_schema)
    db_conn.close()
    timer_cb()


def timer_cb():
    _delete_old_bans()
    _schedule_next()
    return w.WEECHAT_RC_OK


def _schedule_next():
    global DELETE_BAN_TIMER_HOOK
    global DELETE_BAN_INTERVAL
    if DELETE_BAN_TIMER_HOOK:
        w.unhook(DELETE_BAN_TIMER_HOOK)
        DELETE_BAN_TIMER_HOOK = None
    DELETE_BAN_TIMER_HOOK = w.hook_timer(
        int(DELETE_BAN_INTERVAL * 1000),  # interval, num ms
        0,  # align_second, don't care
        1,  # call once, we'll schedule ourselves again
        # Function to call. NOTE: this is NOT our timer_cb(). The
        # callback function must exist in the same file as the plugin's
        # __main__ module. Thus tormodbot.py's timer_cb() is the one called,
        # which should be written to call OUR timer_cb() when it sees the
        # our callback_data.
        'timer_cb',
        'chanserv')  # callback_data


def _delete_old_bans():
    # tmb.log('Looking for old bans to delete')
    now = int(time.time())
    db_conn = sqlite3.connect(db_fname())
    db_conn.row_factory = sqlite3.Row
    with db_conn:
        rows = db_conn.execute(FIND_OLD_QUERY, (now,))
        # tmb.log('These are old undeleted rows:')
        for row in rows:
            quiet_or_akick = 'quiet' if row['is_quiet'] else 'akick'
            chan = row['chan']
            glob = row['glob']
            tmb.log(
                'Deleting old {} on {} in {}', quiet_or_akick, glob, chan)
            s = '{which} {chan} del {glob}'.format(
                which=quiet_or_akick,
                chan=chan, glob=glob)
            msg(tmb.chanserv_user().nick, s)
            q = 'UPDATE bans SET deleted = 1 WHERE rowid = ?'
            db_conn.execute(q, (row['rowid'],))
    db_conn.close()
