"""Tests for core/cache.py — cache_result decorator, clear_cache."""

import time

import pytest

from aura_cli.core.cache import cache_result, clear_cache, get_cache_stats


@pytest.fixture(autouse=True)
def clean():
    clear_cache()
    yield
    clear_cache()


class TestCacheResult:
    def test_caches_return_value(self):
        call_count = 0

        @cache_result(ttl=60)
        def expensive(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert call_count == 1

    def test_different_args_different_cache(self):
        call_count = 0

        @cache_result(ttl=60)
        def fn(x):
            nonlocal call_count
            call_count += 1
            return x

        fn(1)
        fn(2)
        assert call_count == 2

    def test_ttl_expiry(self):
        call_count = 0

        @cache_result(ttl=0.05)
        def fn():
            nonlocal call_count
            call_count += 1
            return "result"

        fn()
        time.sleep(0.1)
        fn()
        assert call_count == 2

    def test_clear_cache_resets(self):
        call_count = 0

        @cache_result(ttl=60)
        def fn(x):
            nonlocal call_count
            call_count += 1
            return x

        fn(42)
        assert call_count == 1
        clear_cache()
        fn(42)
        assert call_count == 2

    def test_get_cache_stats_returns_dict(self):
        stats = get_cache_stats()
        assert isinstance(stats, dict)
