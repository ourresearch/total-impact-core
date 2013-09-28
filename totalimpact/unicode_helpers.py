import unicodedata
import logging

logger = logging.getLogger('ti.unicode_helpers')

#from http://farmdev.com/talks/unicode/
def to_unicode_or_bust(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def printing_character_or_space(c):
    is_printing_character_or_space = True
    # see http://www.fileformat.info/info/unicode/category/index.htm
    char_classes_to_remove = ["C", "M", "Z"]
    if unicodedata.category(c)[0] in char_classes_to_remove:
        if c != " ":
            is_printing_character_or_space = False
    return is_printing_character_or_space


def remove_nonprinting_characters(input, encoding='utf-8'):
    input_was_unicode = True
    if isinstance(input, basestring):
        if not isinstance(input, unicode):
            input_was_unicode = False

    unicode_input = to_unicode_or_bust(input)


    response = u''.join(c for c in unicode_input if printing_character_or_space(c))

    if not input_was_unicode:
        response = response.encode(encoding)
        
    return response

