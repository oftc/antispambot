def lcsv(str_or_list):
    ''' List of Comma-Separated Values.

    Convert a str of comma-separated values to a list over the items, or
    convert such a list back to a comma-separated string.

    This function does not understand quotes.

    See the unit tests for examples of how ``lcsv`` works.
    '''
    if isinstance(str_or_list, str):
        s = str_or_list
        if not s:
            return []
        else:
            return s.split(',')
    lst = str_or_list
    return ','.join(lst)


def test_empty():
    assert lcsv('') == []
    assert lcsv([]) == ''


def test_str_simple():
    assert lcsv('a,b,c') == ['a', 'b', 'c']


def test_list_simple():
    assert lcsv(['foo', 'bar', 'baz']) == 'foo,bar,baz'


def test_list_with_confusing_quotes():
    # Make sure the quotes don't mean shit. It's all about them commas
    a = lcsv('quotes,"multi, word", are,not,understood')
    assert a[1:3] == ['"multi', ' word"']
