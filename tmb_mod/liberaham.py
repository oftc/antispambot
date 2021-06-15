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
# stuff that comes with tormodbot itself
import tormodbot as tmb
# other modules/packages
from tmb_util.msg import notice, voice
from . import Module

# To make calling weechat stuff take fewer characters
w = weechat

#: Additional response to give when voicing a person and restating their
#: message. Parameter is their nick.
EXTRA_RESPONSE = 'I am an antispam bot and voiced {0} automatically '\
    'because they "definitely" aren\'t a spammer. {0} can now speak without '\
    'my interference. Have a nice day!'
#: The regex string that tells us whether the message is likely spam or not.
REGEX = re.compile(
    'ǃ|ɑ|ɡ|ː|։|ഠ|፡|Ꭱ|Ꭲ|Ꭹ|Ꭻ|Ꮃ|Ꮇ|Ꮢ|Ꮤ|Ꮪ|Ꮯ|Ꮳ|Ꮴ|ᖇ|ᖴ|ᗷ|᛬|᜵|ᥒ|ᥙ|ᥱ|ᴠ|ᴡ|ỿ|․|⁄|Ⅰ|Ⅽ'
    '|ⅰ|ⅴ|ⅹ|ⅼ|ⅽ|ⅾ|ⅿ|∕|∨|∪|⋁|⎼|⠆|⧸|ⲟ|ⲣ|Ⲥ|ⲭ|ⵑ|︓|﹕|﹗|．|／')


class LiberaHamModule(Module):
    ''' See the module-level documentation '''
    NAME = 'liberaham'

    def __init__(self):
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
        # It is indeed spam, so don't voice
        if REGEX.search(message):
            tmb.log(
                '{} is probably spamming {}, so not voicing.',
                user.nick, receiver)
            return
        voice(receiver, user.nick)
        notice(receiver, EXTRA_RESPONSE, user.nick)
        notice(receiver, '{} said: {}', user.nick, message)
        return
