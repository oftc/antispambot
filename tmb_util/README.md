# weechat-mod-utils

A collection of classes and whatnot to speed up my weechat python script
writing ability.

# Contents

## `cmdqueue.py`

Use this to queue and throttle the bot's outbound messages/commands so that it
doesn't overload the IRCd and get itself forcibly disconnected.

## `lcsv.py`

Function for converting between a `str` of comma-separated values and a `list`.
Consider using this if you want to store a list of items in weechat's
configuration. **Note that lcsv() does not understand quoting**.

## `msg.py`

Provides helper functions to make sending messages or commands a bit easier.
For example, use `notice(...)` to send NOTICEs and `msg(...)` to send
PRIVMSGes. Helpers for joining channels, setting modes, and voicing are also
provided.

## `tokenbucket.py`

Provides `token_bucket(...)`, used to generate a token bucket function that
relies on its caller to keep state. Call the generated function right after
performing an action that consumes a token, and the function will return (1)
the amount of time you need to wait before having a positive number of tokens
again, and (2) the new state object.

## `userstr.py`

Class to store `nick!user@host` string in a richer class. Offers `.nick`,
`.user`, and `.host` properties that convert the values to lower case before
returning them. Convert a `UserStr` to a string to get the original
`nick!user@host`.

# Testing

    pytest --doctest-modules
