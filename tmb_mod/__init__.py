import weechat

#: To make calling weechat functions easier
w = weechat


class Module:
    ''' TorModBot modules -- essentially major "self contained" features --
    have this class as a parent. We provide a uniform interface for
    ``tormodbot.py`` to use and default implementations for all of the
    functions exposed to it.

    There are required static class values values that must be set.
    '''
    #: Required: The name of this module, used for finding config options
    NAME = ''

    def __init__(self):
        pass

    def _conf_key(self, s):
        ''' Prefix the given string *s* with our module's name, thus creating
        a config key.

        It is very unlikely that you should overwrite this member function with
        your own.

        We expect *s* to be something like 'enabled'. We prefix that with the
        module's ``NAME``, e.g. 'faq', thus producing 'faq_enabled'. We can
        pass 'faq_enabled' to ``weechat.config_get_plugin()`` and it will
        prefix it the rest of the way to the full key,
        'plugin.var.python.tormodbot.faq_enabled'.
        '''
        return self.NAME + '_' + s

    def enabled(self):
        ''' Returns True if this module is configured to be enabled, otherwise
        False.

        It is very unlikely that you should overwrite this member function with
        your own.
        '''
        return w.config_string_to_boolean(
            w.config_get_plugin(self._conf_key('enabled')))

    def initialize(self):
        ''' Called whenever the plugin is restarting or reloading and this
        module is *enabled*.

        It's possible you need to overwrite this member function with your own
        if your module keeps state. '''
        pass

    # ### Commented out because while it's probably a good idea, no module does
    # ### this right now
    # def deinitialize(self):
    #     ''' Called whenever the plugin is restarting or reloading and this
    #     module is *disabled*.

    #     If you needed to overwrite :meth:`Module.initialize`, you probably
    #     hsould overwrite this one too. Make sure this function can be called
    #     multiple times safely. '''
    #     pass

    def timer_cb(self):
        ''' ``tormodbot.py`` needs to be edited to call this if you use
        WeeChat timers. '''
        pass

    def join_cb(self, user, chan):
        ''' Called whenever we are enabled and see a JOIN.

        You want to overwrite this function if you care about JOINs.

        :param UserStr user: Who JOINed.
        :param str chan: The channel that was JOINed.
        '''
        pass

    # ### Commented out because right now no *modules* look for PARTs.
    # def part_cb(self, user, chan):
    #     ''' Called whenever we are enabled and see a PART.

    #     You want to overwrite this function if you care about PARTs.

    #     :param UserStr user: Who PARTed.
    #     :param str chan: The channel that was PARTed.
    #     '''
    #     pass

    def privmsg_cb(self, user, dest, message, is_opmod):
        ''' Called whenever we are enabled and see a PRIVMSG.

        You want to overwrite this function if you care about messages in
        moderated channels and/or PMs directly to us.

        .. note::

            Globally-ignored users do not trigger this.

        :param UserStr user: Who PRIVMSGed.
        :param str dest: The channel name (e.g. "#foo") in which the message
            was seen, or our nick (if a literal PM to us).
        :param str message: The message sent, without leading or trailing
            whitespace.
        :param bool is_opmod: Whether or not this message is a statusmsg
            targeted to @#channel as opposed to #channel as usual. OFTC's +z
            channel mode (hybrid, not solanum) sends messages that would
            otherwise be blocked to chanops using this method, and when it
            does, it calls it opmod. If this is set on this message, you must
            be a chanop in the channel (congratulations!) and you and your
            fellow chanops are the only ones that saw the message.
        '''
        pass

    def notice_cb(self, sender, receiver, message):
        ''' Called whenever we are enabled and see a NOTICE.

        .. note::

            Bots aren't supposed to take action based on notices. It's in the
            standards! Most likely you don't want to overwrite this.

        .. note::

            Globally-ignored users do not trigger this.

        :param str sender: Who sent the NOTICE. *Not necessarily a string that
            can be turned into a :class:`UserStr`*. Servers send NOTICEs.
            Expect something like "dacia.oftc.net" or "nick!user@host". Only
            the latter can be turned into a :class:`UserStr`.
        :param str receiver: The channel name in which the NOTICE was seen, or
            our nick.
        :param str messge: The message sent, without leading or trailing
            whitespace.
        '''
        pass

    def whois_cb(self, whois_code, nick, message):
        ''' Called whenever we are enabled and receive certain /whois-related
        codes.

        .. note::

            At the time of writing, a tiny subset of codes are actually
            listened for: just enough for the liberaham module to work. If you
            want to know more than (i) what nick this is about, (ii) if they
            are registered with nickserv, and (iii) when the whois data is
            done, you will have to listen for more in tormodbot.py.

        .. note::

            Whois information about globally-ignored users does not trigger
            this.

        :param int whois_code: The code number for this whois line. Refer to
            http://www.faqs.org/rfcs/rfc1459.html and
            https://github.com/oftc/oftc-hybrid/blob/develop/include/numeric.h and
            https://github.com/oftc/oftc-hybrid/blob/develop/modules/m_whois.c
        :param str nick: The nick that is the subject of this whois message.
        :param str message: The remaining part of this whois message.
            '''  # noqa: E501
        pass
