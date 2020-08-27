import weechat
# stdlib imports
# import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.userstr import UserStr


#: Our cache of data. Keys are channels (like ``#foo``) and values are sets of
#: :class:`UserStr`.
D = {}
# To make calling weechat stuff take fewer characters
w = weechat
#: Weechat timer hook on our reoccurring event on refreshing all nick!user@host
#: that we know about.
REFRESH_TIMER_HOOK = None
#: The initial and minimum interval used, in seconds
REFRESH_TIMER_INTERVAL_MIN = 10
#: The next interval to use, in seconds
REFRESH_TIMER_INTERVAL = REFRESH_TIMER_INTERVAL_MIN
#: Target interval, in seconds, on our complete refresh of all nick!user@host
#: strings we know about. When in steady state and not manually refreshing, we
#: double our interval repeatedly until it is more than this, at which point
#: we use this.
REFRESH_TIMER_INTERVAL_MAX = 86400


def _monitored_chans():
    ''' Channels in which we fetch all known :class:`UserStr` '''
    return set(tmb.mod_chans() + [tmb.log_chan()])


def nick_to_user(nick):
    ''' See if we cann find a :class:`UserStr` for the given nick. If so,
    return it. Else return ``None``. '''
    global D
    nick = nick.lower()
    for users_in_a_chan in D.values():
        for user in users_in_a_chan:
            if user.nick == nick:
                return user
    return None


def user_in_chans(user):
    ''' Return all monitored channels that :class:`UserStr` *user* is in.  '''
    global D
    out = set()
    if not user:
        return out
    # Just grab the nick and search all channels with it
    for chan, users in D.items():
        if user in users:
            out.add(chan)
    return out


def join_cb(user, chan):
    ''' Called on join events from :class:`UserStr` *user* joining str *chan*
    '''
    global D
    if chan not in _monitored_chans():
        # We don't care. This shouldn't happen, but we definitely don't care
        return
    if chan not in D:
        # How did we not know about this channel??? We need to figure out what
        # other nicks are in this channel, and perhaps what other channels we
        # don't know about. Schedule a new refresh ASAP
        _schedule_next(REFRESH_TIMER_INTERVAL_MIN)
        return
    assert chan in D
    assert isinstance(user, UserStr)
    D[chan].add(user)


def part_cb(user, chan):
    ''' Called on part events from :class:`UserStr` *user* joining str *chan*
    '''
    global D
    if chan not in D:
        # This shouldn't happen, but we definitely don't care
        return
    # old_len = len(D[chan])
    D[chan].remove(user)
    # tmb.log('{} left {}, {} to {}', user.nick, chan, old_len, len(D[chan]))


def initialize():
    _set_options()
    _schedule_next(REFRESH_TIMER_INTERVAL_MIN)


def connect_cb():
    ''' Called whenever we have connected to the server '''
    _schedule_next(REFRESH_TIMER_INTERVAL_MIN)


def timer_cb():
    _reload_from_nicklists()
    _schedule_next(REFRESH_TIMER_INTERVAL)
    return w.WEECHAT_RC_OK


def _reload_from_nicklists():
    ''' Clear out our stored n!u@h and load them again from the weechat nick
    lists '''
    global D
    D = {}
    serv = tmb.serv()
    # time_start = time.time()
    chans = _monitored_chans()
    logged_warning = False
    for chan in chans:
        D[chan] = set()
        ilist = w.infolist_get('irc_nick', '', '{},{}'.format(serv, chan))
        while w.infolist_next(ilist):
            # tmb.log('{}', w.infolist_fields(ilist))
            nick = w.infolist_string(ilist, 'name')
            user_host = w.infolist_string(ilist, 'host')
            if not user_host:
                if not logged_warning:
                    tmb.log(
                        'WARNING: No user@host found for {} in {}. This is '
                        'only expected to happen in two cases. 1. if weechat '
                        'has not been configured correctly, which we should '
                        'have already done for you. 2. Just once or twice on '
                        'initial startup. Are you ignoring warnings?',
                        nick, chan)
                    logged_warning = True
                continue
            s = '{}!{}'.format(nick, user_host)
            D[chan].add(UserStr(s))
        w.infolist_free(ilist)
    # time_end = time.time()
    # tmb.log(
    #     'Cached {} n!u@h strings in {} chans in {:0.3f} seconds',
    #     sum([len(_) for _ in D.values()]), len(chans), time_end - time_start)


def _schedule_next(after):
    ''' Schedule our timer callback to be called after *after* seconds from
    now. If there is a current callback scheduled, cancel it. '''
    global REFRESH_TIMER_INTERVAL
    global REFRESH_TIMER_INTERVAL_MAX
    global REFRESH_TIMER_HOOK
    if REFRESH_TIMER_HOOK:
        w.unhook(REFRESH_TIMER_HOOK)
        REFRESH_TIMER_HOOK = None
    # Double the interval with which we call our timer_cb until it reaches the
    # max acceptable interval
    REFRESH_TIMER_INTERVAL = min(
        2 * after, REFRESH_TIMER_INTERVAL_MAX)
    # tmb.log(
    #     'Scheduling next total refresh of all known n!u@h in {} seconds',
    #     after)
    REFRESH_TIMER_HOOK = w.hook_timer(
        int(after * 1000),  # interval, num ms
        0,  # align_second, which we don't care about
        1,  # max calls, we'll schedule ourselves again manually
        # Function to call. NOTE: this is NOT our timer_cb(). The
        # callback function must exist in the same file as the plugin's
        # __main__ module. Thus tormodbot.py's timer_cb() is the one called,
        # which should be written to call OUR timer_cb() when it sees the
        # our callback_data.
        'timer_cb',
        'userlist')  # callback_data


def _set_options():
    ''' Set options necessary for the userlist stuff to work.

    Weechat can optionally get away information for everyone in a channel, and
    by doing so it fetches user@host info for each nick. We need that info, so
    set away_check options as we need them: no limit on number of nicks in a
    chan, and check every hour. We don't need to check away status very often
    because joins/parts also feed us with user@host info, which we should
    expect to be the primary source of info after we've been connected to the
    network longer than most people.
    '''
    # Max nicks: unlimited
    max_nicks_key = 'irc.server.{}.away_check_max_nicks'.format(tmb.serv())
    max_nicks_opt = w.config_get(max_nicks_key)
    max_nicks_val = '0'  # unlimited
    max_nicks_ret = w.config_option_set(max_nicks_opt, max_nicks_val, 0)
    # Check every 60 minutes
    away_check_key = 'irc.server.{}.away_check'.format(tmb.serv())
    away_check_opt = w.config_get(away_check_key)
    away_check_val = '60'  # minutes
    away_check_ret = w.config_option_set(away_check_opt, away_check_val, 0)
    if max_nicks_ret == w.WEECHAT_CONFIG_OPTION_SET_ERROR:
        tmb.log(
            'WARNING: userlist.py may NOT get the nick!user@host information '
            'because it was unable to set {} to {} (unlimited).',
            max_nicks_key, max_nicks_val)
    if away_check_ret == w.WEECHAT_CONFIG_OPTION_SET_ERROR:
        tmb.log(
            'WARNING: userlist.py may NOT get the nick!user@host information '
            'because it was unable to set {} to {} minutes.',
            away_check_key, away_check_val)
