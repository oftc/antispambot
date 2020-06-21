def lcsv(str_or_list):
    ''' List of Comma-Separated Values.

    Convert a str of comma-separated values to a list over the items, or
    convert such a list back to a comma-separated string.

    This function does not understand quotes

    >>> lcsv('')
    []
    >>> lcsv([])
    ''
    >>> lcsv('a,b,c')
    ['a', 'b', 'c']
    >>> lcsv(['foo','bar','baz'])
    'foo,bar,baz'
    >>> l = lcsv('quotes,"multi, word",are,not,understood')
    >>> l[1:3]
    ['"multi', ' word"']
    '''
    if isinstance(str_or_list, str):
        s = str_or_list
        if not s:
            return []
        else:
            return s.split(',')
    lst = str_or_list
    return ','.join(lst)
