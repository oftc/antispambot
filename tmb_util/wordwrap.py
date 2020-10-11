import textwrap


def _wrap_line(tw, s):
    ''' Given a :class:`textwrap.TextWrapper` and a single long line of text
    ``s``, wrap ``s`` after reducing whitespace between its words to a single
    space. '''
    return tw.wrap(' '.join(s.split()))


def wrap_text(s, max_width):
    ''' Wrap the given multi-line string ``s`` such that each line is no more
    than ``max_width`` characters.

    The input text can be more than one paragraph, in which case each paragraph
    is wrapped separately. Paragraphs are deliminated with blank lines::

        This is one
        very short paragraph.

        And this is the start of another paragraph.

    This function yields wrapped lines, each *with* a trailing newline. It may,
    in the case of the input containing multiple paragraphs, return lines that
    are simply a single newline character.
    '''
    # object that actually does the wrapping
    tw = textwrap.TextWrapper(width=max_width)
    # accumulate the current working paragraph here
    acc = ''
    # strip unnecessary whitespace from left of top-most line and right of
    # bottom-most line
    s = s.strip()
    for in_line in s.split('\n'):
        # Append the input line to the accumulating paragraph. Add a space so
        # that there's always *at least* one space between words. Later we will
        # make it *exactly* one space.
        acc += ' ' + in_line
        # if the in_line is actually all just whitespace, then we've reached
        # the end of the current paragraph and should output it as wrapped
        # lines.
        if not len(in_line.strip()):
            for out_line in _wrap_line(tw, acc):
                yield out_line + '\n'
            # clear paragraph
            acc = ''
            # output a blank line before the next paragraph
            yield '\n'
    # if there's leftover text, print it
    if len(acc):
        for out_line in _wrap_line(tw, acc):
            yield out_line + '\n'


#: Width to which to wrap lines in most (all?) tests
TEST_W = 10


def _lgts(lg):
    ''' Line Generator To String. Test helper that takes a generator of lines
    (each with a trailing \n character) and returns a single string containing
    them concatenated '''
    return ''.join(_ for _ in lg)


def test_empty():
    assert _lgts(wrap_text('', TEST_W)) == '\n'
    assert _lgts(wrap_text('\n', TEST_W)) == '\n'
    assert _lgts(wrap_text('\n \t \n   \n', TEST_W)) == '\n'


def test_multi_whitespace_to_single():
    assert _lgts(wrap_text('a  b\tc\t d\t\te\n', TEST_W)) == 'a b c d e\n'


def test_single_para():
    assert _lgts(wrap_text('f', TEST_W)) == 'f\n'
    assert _lgts(wrap_text('f f f f f', TEST_W)) == 'f f f f f\n'
    assert _lgts(wrap_text('f f f f f f', TEST_W)) == 'f f f f f\nf\n'
    assert _lgts(wrap_text('aaaabbbb cccc', TEST_W)) == 'aaaabbbb\ncccc\n'
    assert _lgts(wrap_text('aaaa bbbbcccc', TEST_W)) == 'aaaa\nbbbbcccc\n'


def test_multi_para():
    # bare minimum to indicate multiple paragraphs
    assert _lgts(wrap_text('a\n\nb', TEST_W)) == 'a\n\nb\n'
    # a bunch of stuff that is ultimately whitespace between paragraphs. The
    # only thing that should be kept is the newlines.
    assert _lgts(wrap_text('a\n\n  \n\t \nb', TEST_W)) == \
        'a\n\n\n\nb\n'
