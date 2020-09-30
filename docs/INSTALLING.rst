Installation and Setup
======================

.. warning::

   This document is unfinished :(

.. note::

   The last time this note was updated (which is an approximation of the last
   time this document was updated) is 24 September 2020.

.. note::

   I expect TorModBot to work without changes with a newer WeeChat that uses
   Python 3. I (pastly, the one writing TorModBot) only really know Python 3
   and the issues I run into while writing TMB are not related to 2-vs-3.


.. note::

   The assumptions are as follows:

   - This is a fresh WeeChat install. If you have existing Python plugins, you
     know how to keep them.
   - You are happy with WeeChat's default data directory, ``~/.weechat``. If
     you don't like it, then you include ``-d custom-weechat-datadir`` as an
     argument every time you run WeeChat and replace it in every data directory
     reference below.

Obtain WeeChat. Version 2.3 is the latest tested and is what you get with
Debian Buster. When using version 2.3, TorModBot will come with Python 2.7.15,
as shown with a ``/debug libs`` command in WeeChat::

    │17:00  weechat     | Libs:
    [...]
    │17:00  weechat     |   python: 2.7.15+
    [...]

Run WeeChat once to establish its basic data directory structure. It's probably
``~/.weechat``.

Add the IRC server.  See ``/help server`` for usage info.

.. code-block:: text

   /server add oftc irc.oftc.net/6697 -ssl -autoconnect

If you want to connect to the IRC network over Tor, add a proxy and configure
the server to use it. See ``/help proxy`` for usage info.

.. code-block:: text

   /proxy add tor socks5 127.0.0.1 9050
   /set irc.server.oftc.proxy tor

Configure the nickname and username of the bot.

.. code-block:: text

   /set irc.server.oftc.nicks testmodbot
   /set irc.server.oftc.username testmodbot

Execute ``/quit`` to exit.

Remove the ``python`` directory from WeeChat's data directory. Of course, copy
stuff out that you want; this document assumes this is a clean WeeChat install.

Clone the code into ``~/.weechat/python``::

   git clone https://gitlab.torproject.org/pastly/weechat-tormodbot ~/.weechat/python

Start WeeChat again. Wait for it to connect to IRC. Execute the following to
load the plugin::

   /script load tormodbot.py

Upon doing so, the following means success::

    python: loading script "/home/matt/weechat-temp/python/tormodbot.py"
    python: registered script "tormodbot", version 0.1.0 (Help Tor Project moderate their many channels)
    tormodbot v0.1.0 (re)loaded
    Using: Python 2.7.16 (default, Oct 10 2019, 22:02:15)

A know source of failure is an import error.  For example, the following means
you need to install the backport of Python 3.4's ``enum``, something you might
see on Buster with WeeChat 2.3. One way to do so is simply ``sudo apt install
python-enum34``. Alternatively use ``pip`` to install it for your user or in a
virtualenv for WeeChat.

.. code-block:: text

   python: loading script "/home/matt/weechat-temp/python/tormodbot.py"
   python: stdout/stderr (?): Traceback (most recent call last):
   python: stdout/stderr (?):   File "/home/matt/weechat-temp/python/tormodbot.py", line 7, in <module>
   python: stdout/stderr (?):     import tmb_mod.autovoice
   python: stdout/stderr (?):   File "/home/matt/weechat-temp/python/tmb_mod/autovoice.py", line 19, in <module>
   python: stdout/stderr (?):     import tormodbot as tmb
   python: stdout/stderr (?):   File "/home/matt/weechat-temp/python/tormodbot.py", line 8, in <module>
   python: stdout/stderr (?):     import tmb_mod.antiflood
   python: stdout/stderr (?):   File "/home/matt/weechat-temp/python/tmb_mod/antiflood.py", line 15, in <module>
   python: stdout/stderr (?):     import enum
   python: stdout/stderr (?): ImportError: No module named enum
   python: unable to parse file "/home/matt/weechat-temp/python/tormodbot.py"
