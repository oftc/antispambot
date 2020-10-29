''' Auto-voice module

If enabled, the autovoice module can:

- auto +v users with a matching ``nick!user@host`` string
- auto +v users who have registered at least ``X`` seconds ago with a matching
  ``nick!user@host`` string

See the ``AUTOVOICE_*`` options in :mod:`config` for our configuration options.

See :ref:`limits`, especially regarding cloaks.
'''
import weechat
# stdlib imports
import calendar
import re
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.lcsv import lcsv
from tmb_util.msg import msg, voice
from tmb_util.userstr import UserStr
from . import Module


# To make calling weechat stuff take fewer characters
w = weechat


class AutoVoiceModule(Module):
    ''' See the module-level documentation '''
    NAME = 'autovoice'

    def __init__(self):
        #: Queue of (UserStr, chan) we want to ask nickserv about to see if
        #: they registered, and if so, when they did so
        self.nickserv_time_reg_q = []

    def join_cb(self, user, chan):
        ''' Main tormodbot code calls into this when we're enabled and the
        given :class:`tmb_util.userstr.UserStr` has joined the given channel
        '''
        # If this isn't a channel we're moderating, then exit early
        if chan not in tmb.mod_chans():
            return
        # If we always want to +v the nick, then do so
        for regex in self._regex_always():
            if re.match(regex, str(user)):
                tmb.log('Voice {} (always!) because matches {}', user, regex)
                voice(chan, user.nick)
                return
        # Otherwise, maybe we want to +v the nick if they registered long
        # enough ago. Ask nickserv for info on the nick, and later when we are
        # parsing the messages we get back from nickserv, we will act on it (or
        # not).
        # TODO: be smarter about this. Don't need to ask if we've asked
        # recently (in the last day?)
        if (user, chan) not in self.nickserv_time_reg_q:
            self.nickserv_time_reg_q.append((user, chan))
            msg(tmb.nickserv_user().nick, 'info {}', user.nick)

    def notice_cb(self, sender, receiver, message):
        ''' Main tormodbot code calls into this when we're enabled and have
        received a notice message '''
        # if it doesn't look the sender is a user (parse-able as n!u@h), ignore
        if '!' not in sender or '@' not in sender:
            return
        user = UserStr(sender)
        # if it isn't nickserv, then we don't care
        if user != tmb.nickserv_user():
            return
        self._handle_nickserv_message(message)

    def _handle_nickserv_message(self, message):
        ''' Called when we've parsed a NOTICE from nickserv and might want to
        do something with the information in this message. We don't know yet,
        and might just want to ignore it. '''
        # As of now, the only reason we want to hear back from nickserv is if
        # we are checking the registration status of a nick. So check if
        # there's any nicks in the queue.
        # Note that just because a nick is registered, that doesn't mean the
        # person using it is actually the one who owns that nick. The nick may
        # not have ENFORCE set.
        # Make sure we are actually looking for info on a nick
        if not len(self.nickserv_time_reg_q):
            return
        # We do not currently use 'start of text' bytes to help us parse these
        # messages, so strip them out so we don't get confused later.
        message = message.replace('\x02', '')
        if 'is not registered' in message:
            # Get the second word:
            #     "Nickname foooooo is not registered. The nickname you ..."
            nick = message.split()[1].lower()
            try:
                idx = [
                    u.nick for (u, _) in self.nickserv_time_reg_q].index(nick)
            except ValueError:
                tmb.log(
                    'Told that {} is not registered, but we don\'t seem ' +
                    'to care.', nick)
                return
            if idx != 0:
                tmb.log(
                    'Told that {} is not registered, but learned that out '
                    'of order by {}', nick, idx)
            # Remove the nick
            _ = self.nickserv_time_reg_q.pop(idx)
            tmb.log('{} is not registered', nick)
        elif 'Time registered: ' in message:
            # Assume the latest nick in the queue is the one we got the answer
            # for.  Also remove it. Do this right away so that we always remove
            # the nick even if future revisions of this code path return early.
            user, chan = self.nickserv_time_reg_q.pop(0)
            # Get the words that are part of the date:
            #   "Time registered:  Thu 13 Oct 2016 20:50:28 +0000 (3y ...)"
            # I'm always seeing +0000 for the timezone, so I'm going to assume
            # we're always told UTC
            date_words = message.split()[2:8]
            date_str = ' '.join(date_words)
            day_month_year_time = ' '.join(date_str.split()[1:5])
            # WTF why is this so hard? Just convert the timestamp to the number
            # of seconds since 1970. Doing datetime.strptime(...) complained
            # about a NoneType somewhere and it didn't make any sense. So this
            # is the next best thing.
            ts = calendar.timegm(time.strptime(
                day_month_year_time, '%d %b %Y %H:%M:%S'))
            # How many seconds have passed since this nick registered
            life = time.time() - ts
            life_str = _seconds_to_duration(life)
            if life >= self._min_seconds():
                tmb.log('{} registered {} ago, so voice', user.nick, life_str)
                voice(chan, user.nick)
            else:
                tmb.log(
                    '{} registered {} ago, so no voice', user.nick, life_str)

    def _regex_always(self):
        ''' Return the list of n!u@h regex patterns that should always get +v
        '''
        return lcsv(w.config_get_plugin(self._conf_key('regex_always')))

    def _min_seconds(self):
        ''' Return the int number of seconds for which a nick must have been
        registered in order for it to be autovoiced '''
        return int(w.config_get_plugin(self._conf_key('registered_seconds')))


def _seconds_to_duration(secs):
    ''' Take a number of seconds and return the amount of time passed as a
    string and measured in days/hours/minutes/seconds '''
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    d, h, m, s = int(d), int(h), int(m), int(round(s, 0))
    if d > 0:
        return '{}d{}h{}m{}s'.format(d, h, m, s)
    elif h > 0:
        return '{}h{}m{}s'.format(h, m, s)
    elif m > 0:
        return '{}m{}s'.format(m, s)
    else:
        return '{}s'.format(s)
