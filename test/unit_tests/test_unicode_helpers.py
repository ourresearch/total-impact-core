from nose.tools import raises, assert_equals, nottest

from totalimpact import unicode_helpers



class TestUnicodeHelpers():

    def setUp(self):
        pass

    def test_remove_nonprinting_characters(self):
        unicode_input = u"hi"
        response = unicode_helpers.remove_nonprinting_characters(unicode_input)
        expected = u"hi"
        assert_equals(response, expected)

    def test_remove_nonprinting_characters(self):
        unicode_input = '0000-0001-8907-4150\xe2\x80\x8e' # a nonprinting character at the end
        response = unicode_helpers.remove_nonprinting_characters(unicode_input)
        expected = "0000-0001-8907-4150"
        assert_equals(response, expected)

    def test_remove_nonprinting_characters_unicode_input(self):
        unicode_input = u'0000-0001-8907-4150\u200e'  # a nonprinting character at the end
        response = unicode_helpers.remove_nonprinting_characters(unicode_input)
        expected = u"0000-0001-8907-4150"
        assert_equals(response, expected)
