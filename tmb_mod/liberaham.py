# -*- coding: utf-8 -*-
'''
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
        #: Cache of (nick, chan, ts, msg) we are /whois-ing and waiting on the
        #: response. The msg is what they said in an opmod, so that we can
        #: restate it if necessary.
        #: Keys are nick. Values are a list of (ts, chan, msg) items.
        self.whois_cache = {}

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
        # It is indeed spam, so don't do a whois lookup
        if REGEX.search(message):
            tmb.log(
                '{} is probably spamming {}, so not voicing.',
                user.nick, receiver)
            return
        voice(receiver, user.nick)
        notice(receiver, EXTRA_RESPONSE, user.nick)
        notice(receiver, '{} said: {}', user.nick, message)
        return
