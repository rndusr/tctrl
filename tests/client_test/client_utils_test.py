from stig.client import utils

import unittest
from unittest.mock import MagicMock, call


class Test_cached_property(unittest.TestCase):
    def test_no_arguments(self):
        foo = MagicMock(return_value='bar')
        class X:
            @utils.cached_property
            def foo(self):
                return foo()
        x = X()
        for _ in range(5):
            self.assertEqual(x.foo, 'bar')
        foo.assert_called_once_with()

    def test_after_creation(self):
        foo = MagicMock(return_value='bar')
        callback = MagicMock()
        class X:
            @utils.cached_property(after_creation=callback)
            def foo(self):
                return foo()
        x = X()
        for _ in range(5):
            self.assertEqual(x.foo, 'bar')
        foo.assert_called_once_with()
        callback.assert_called_once_with(x)


class TestURL(unittest.TestCase):
    def test_empty_string(self):
        url = utils.URL('')
        self.assertEqual(url.scheme, None)
        self.assertEqual(url.host, None)
        self.assertEqual(url.port, None)
        self.assertEqual(str(url), '')

    def test_attributes(self):
        url = utils.URL('http://user:pw@localhost:123/foo')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.user, 'user')
        self.assertEqual(url.password, 'pw')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 123)
        self.assertEqual(url.path, '/foo')

    def test_no_scheme(self):
        url = utils.URL('localhost/foo')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, None)
        self.assertEqual(url.path, '/foo')

    def test_authentication(self):
        url = utils.URL('https://foo:bar@localhost:123')
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 123)
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_authentication_empty_password(self):
        url = utils.URL('foo:@localhost')
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_authentication_no_password(self):
        url = utils.URL('foo@localhost')
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_authentication_empty_user(self):
        url = utils.URL(':bar@localhost')
        self.assertEqual(url.user, None)
        self.assertEqual(url.password, 'bar')
        self.assertEqual(url.host, 'localhost')

    def test_authentication_empty_user_and_password(self):
        url = utils.URL(':@localhost')
        self.assertEqual(url.user, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_invalid_port(self):
        url = utils.URL('foohost:70123')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 70123)

    def test_no_scheme_with_port(self):
        url = utils.URL('foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 9999)

    def test_no_scheme_user_and_pw(self):
        url = utils.URL('foo:bar@foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 9999)
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_str(self):
        url = utils.URL('https://foo:bar@localhost:123')
        self.assertEqual(str(url), 'https://foo:bar@localhost:123')
        url = utils.URL('localhost')
        self.assertEqual(str(url), 'http://localhost')

    def test_repr(self):
        url = utils.URL('https://foo:bar@localhost:123/foo/bar/baz')
        self.assertEqual(repr(url), "URL('https://foo:bar@localhost:123/foo/bar/baz')")

    def test_mutability_and_cache(self):
        url = utils.URL('https://foo.example.com:123/foo')
        url.port = 321
        url.host = 'bar.example.com'
        url.scheme = 'http'
        self.assertEqual(str(url), 'http://bar.example.com:321/foo')

        self.assertEqual(url.domain, 'example.com')
        url.host = 'foo.bar.com'
        self.assertEqual(url.domain, 'bar.com')
        self.assertEqual(str(url), 'http://foo.bar.com:321/foo')
