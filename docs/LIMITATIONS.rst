.. _limits:

Limitations
===========

Known issues and/or limitations of TorModBot.

Cloaks
------

**TorModBot cannot "dig under" cloaks**. Whatever the "top-level" cloak is for
a user, that is what we see.

Consider a registered user who has enabled a personal cloak and who connects
over Tor. Their real hostname is ``this-is-a-tor-exit.example.com``, OFTC's IRCd
applies a Tor cloak ``000000000.tor-irc.dnsbl.oftc.net``, and finally nickserv
applies their personal cloak ``00000000.user.oftc.net``. Assuming we "notice"
them (e.g. :mod:`tmb_mod.autovoice` sees them ``JOIN`` a channel) after
nickserv has applied their personal cloak, we won't recognize them as a Tor
user.
