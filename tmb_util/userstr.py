class UserStr:
    ''' Store a nick/user/host parsed from nick!user@host '''
    def __init__(self, s):
        self._nick, s = s.split('!', 1)
        self._user, s = s.split('@', 1)
        self._host = s

    def __str__(self):
        return '{n}!{u}@{h}'.format(n=self._nick, u=self._user, h=self._host)

    def __eq__(self, rhs):
        return self.nick == rhs.nick and \
            self.user == rhs.user and \
            self.host == rhs.host

    def __ne__(self, rhs):
        return self.nick != rhs.nick or \
                self.user != rhs.user or \
                self.host != rhs.host

    @property
    def nick(self):
        return self._nick.lower()

    @property
    def user(self):
        return self._user.lower()

    @property
    def host(self):
        return self._host.lower()

    def __hash__(self):
        return hash('{}!{}@{}'.format(self._nick, self._user, self._host))
