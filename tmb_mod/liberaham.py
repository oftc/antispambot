# -*- coding: utf-8 -*-
''' Liberaham module

If enabled, we look for spam on people's first messages, and if not spam, voice
them.

**This module makes significant assumptions that should be noted.** It may not
play nicely with other moderation activities, or even with other tormodbot
modules.

**We assume** the moderated channels are ``+Mz``. The former means that
unregistered users' messages are muted, and the latter means that any message
that would be muted instead goes to the channel operators as an "opmod" or
"statusmsg" message.

**We assume** there is no other significant muting going on. People causing
trouble in other ways are not muted, but instead banned. Or perhaps they aren't
registered so you can get away with kicking them and ``+R`` the channel for a
bit.

If

    - you're not presently getting the "THIS CHANNEL HAS MOVED TO
      IRC.LIBERA.CHAT #HAMRADIO" spam, and
    - the spam you're getting doesn't happen on the first message and can be
      near-perfectly differentiated from non-spam with a single regex, then

you probably do **not** want to use this module. (That's where the name comes
from, by the way: libera.chat + #hamradio = liberaham)

See the ``LIBERAHAM_*`` options in :mod:`config` for our configuration options.
'''  # noqa: E501

import weechat
# stdlib imports
import re
import time
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.msg import notice, voice, kline
from tmb_util.userlist import user_in_chans
from . import Module

# To make calling weechat stuff take fewer characters
w = weechat

#: Additional response to give when voicing a person and restating their
#: message.
EXTRA_RESPONSE = '(What\'s this? '\
    'See https://tormodbot.pastly.xyz/liberaham.html )'
#: The regex string that tells us whether the message is likely spam or not.
REGEX = re.compile(
    'ǃ|ɑ|ɡ|ː|։|ഠ|፡|Ꭱ|Ꭲ|Ꭹ|Ꭻ|Ꮃ|Ꮇ|Ꮢ|Ꮤ|Ꮪ|Ꮯ|Ꮳ|Ꮴ|ᖇ|ᖴ|ᗷ|᛬|᜵|ᥒ|ᥙ|ᥱ|ᴠ|ᴡ|ỿ|․|⁄|Ⅰ|Ⅽ'
    '|ⅰ|ⅴ|ⅹ|ⅼ|ⅽ|ⅾ|ⅿ|∕|∨|∪|⋁|⎼|⠆|⧸|ⲟ|ⲣ|Ⲥ|ⲭ|ⵑ|︓|﹕|﹗|．|／')
#: How often, in seconds, we will allow ourselves to also state the extra
#: response. This is to make us less of a toy.
EXTRA_RESPONSE_INTERVAL = 15 * 60
#: The reason to give for the K-Line. One parameter: it is the channel.
KLINE_REASON = 'Suspected spammer. Mail support@oftc.net with questions'\
    '|libera non-ascii spam in {} !dronebl'


class LiberaHamModule(Module):
    ''' See the module-level documentation '''
    NAME = 'liberaham'

    def __init__(self):
        #: The last time we gave the extra response.
        self.last_extra_resp_ts = 0
        pass

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
        # Not a message from a muted user going to @#chan, so return
        if not is_opmod:
            return
        # User isn't in the channel, so return. With +z, messages from users
        # not in the channel go to chanops like us.
        if receiver not in user_in_chans(user):
            return
        # It is indeed spam, so don't voice
        if REGEX.search(message):
            kline('*@' + user.host, KLINE_REASON.format(receiver))
            return
        voice(receiver, user.nick)
        notice(receiver, '{} said: {}', user.nick, message)
        if time.time() - self.last_extra_resp_ts > EXTRA_RESPONSE_INTERVAL:
            notice(receiver, EXTRA_RESPONSE)
            self.last_extra_resp_ts = time.time()
        return
