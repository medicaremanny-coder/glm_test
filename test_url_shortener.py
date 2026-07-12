"""Tests for the URLShortener class."""

import tempfile
import os
import unittest
from pathlib import Path

from url_shortener import URLShortener


class TestInit(unittest.TestCase):
    def test_default_code_length(self):
        s = URLShortener()
        self.assertEqual(s.code_length, 6)

    def test_custom_code_length(self):
        for length in (4, 6, 8, 12):
            s = URLShortener(code_length=length)
            self.assertEqual(s.code_length, length)

    def test_invalid_code_length_too_short(self):
        with self.assertRaises(ValueError):
            URLShortener(code_length=3)

    def test_invalid_code_length_too_long(self):
        with self.assertRaises(ValueError):
            URLShortener(code_length=13)

    def test_invalid_code_length_type(self):
        with self.assertRaises(TypeError):
            URLShortener(code_length="6")

    def test_starts_empty(self):
        s = URLShortener()
        self.assertEqual(s.get_stats()['total_urls'], 0)


class TestShortenURL(unittest.TestCase):
    def setUp(self):
        self.s = URLShortener()

    def test_returns_string(self):
        code = self.s.shorten_url('https://example.com')
        self.assertIsInstance(code, str)

    def test_code_length_matches_setting(self):
        code = self.s.shorten_url('https://example.com')
        self.assertEqual(len(code), self.s.code_length)

    def test_same_url_returns_same_code(self):
        url = 'https://example.com'
        self.assertEqual(self.s.shorten_url(url), self.s.shorten_url(url))

    def test_different_urls_return_different_codes(self):
        code1 = self.s.shorten_url('https://example.com')
        code2 = self.s.shorten_url('https://example.org')
        self.assertNotEqual(code1, code2)

    def test_http_url_accepted(self):
        code = self.s.shorten_url('http://example.com')
        self.assertIsNotNone(code)

    def test_invalid_protocol_raises(self):
        with self.assertRaises(ValueError):
            self.s.shorten_url('ftp://example.com')

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            self.s.shorten_url('')

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            self.s.shorten_url('   ')

    def test_non_string_raises(self):
        with self.assertRaises(TypeError):
            self.s.shorten_url(123)

    def test_none_raises(self):
        with self.assertRaises(TypeError):
            self.s.shorten_url(None)

    def test_increments_stats(self):
        self.s.shorten_url('https://example.com')
        self.assertEqual(self.s.get_stats()['total_urls'], 1)
        self.s.shorten_url('https://example.org')
        self.assertEqual(self.s.get_stats()['total_urls'], 2)

    def test_reshortening_same_url_does_not_increment(self):
        url = 'https://example.com'
        self.s.shorten_url(url)
        self.s.shorten_url(url)
        self.assertEqual(self.s.get_stats()['total_urls'], 1)


class TestExpandURL(unittest.TestCase):
    def setUp(self):
        self.s = URLShortener()
        self.url = 'https://example.com/path?q=1'
        self.code = self.s.shorten_url(self.url)

    def test_roundtrip(self):
        self.assertEqual(self.s.expand_url(self.code), self.url)

    def test_unknown_code_returns_none(self):
        self.assertIsNone(self.s.expand_url('xxxxxx'))

    def test_empty_code_raises(self):
        with self.assertRaises(ValueError):
            self.s.expand_url('')

    def test_whitespace_code_raises(self):
        with self.assertRaises(ValueError):
            self.s.expand_url('   ')

    def test_non_string_code_raises(self):
        with self.assertRaises(TypeError):
            self.s.expand_url(42)


class TestGetStats(unittest.TestCase):
    def test_keys_present(self):
        stats = URLShortener().get_stats()
        self.assertIn('total_urls', stats)
        self.assertIn('total_codes', stats)
        self.assertIn('code_length', stats)

    def test_counts_match(self):
        s = URLShortener()
        for i in range(5):
            s.shorten_url(f'https://example.com/{i}')
        stats = s.get_stats()
        self.assertEqual(stats['total_urls'], 5)
        self.assertEqual(stats['total_codes'], 5)


class TestClear(unittest.TestCase):
    def test_clear_empties_mappings(self):
        s = URLShortener()
        s.shorten_url('https://example.com')
        s.clear()
        self.assertEqual(s.get_stats()['total_urls'], 0)
        self.assertEqual(s.get_stats()['total_codes'], 0)

    def test_can_reshorten_after_clear(self):
        s = URLShortener()
        url = 'https://example.com'
        code1 = s.shorten_url(url)
        s.clear()
        code2 = s.shorten_url(url)
        self.assertEqual(code1, code2)  # same hash → same code


class TestSaveAndLoad(unittest.TestCase):
    def setUp(self):
        self.s = URLShortener()
        self.urls = [
            'https://example.com',
            'https://github.com/user/repo',
            'https://docs.python.org/3/',
        ]
        for url in self.urls:
            self.s.shorten_url(url)

    def test_save_creates_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            path = f.name
        try:
            self.s.save_to_file(path)
            self.assertTrue(Path(path).exists())
        finally:
            os.unlink(path)

    def test_load_restores_mappings(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w') as f:
            path = f.name
        try:
            self.s.save_to_file(path)
            s2 = URLShortener()
            s2.load_from_file(path)
            self.assertEqual(s2.get_stats()['total_urls'], len(self.urls))
            for url in self.urls:
                self.assertEqual(s2.expand_url(self.s.shorten_url(url)), url)
        finally:
            os.unlink(path)

    def test_save_invalid_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.s.save_to_file('/nonexistent_dir/file.txt')

    def test_load_missing_file_raises(self):
        s2 = URLShortener()
        with self.assertRaises(FileNotFoundError):
            s2.load_from_file('/nonexistent/file.txt')

    def test_load_invalid_format_raises(self):
        with tempfile.NamedTemporaryFile(
            delete=False, suffix='.txt', mode='w'
        ) as f:
            f.write("this_line_has_no_comma\n")
            path = f.name
        try:
            s2 = URLShortener()
            with self.assertRaises(ValueError):
                s2.load_from_file(path)
        finally:
            os.unlink(path)

    def test_save_empty_path_raises(self):
        with self.assertRaises(ValueError):
            self.s.save_to_file('')

    def test_load_empty_path_raises(self):
        with self.assertRaises(ValueError):
            URLShortener().load_from_file('')

    def test_load_non_string_raises(self):
        with self.assertRaises(TypeError):
            URLShortener().load_from_file(123)

    def test_save_non_string_raises(self):
        with self.assertRaises(TypeError):
            self.s.save_to_file(None)


class TestCodeLengthVariants(unittest.TestCase):
    def test_code_length_respected(self):
        for length in (4, 7, 12):
            s = URLShortener(code_length=length)
            code = s.shorten_url('https://example.com')
            self.assertEqual(len(code), length)


if __name__ == '__main__':
    unittest.main(verbosity=2)
