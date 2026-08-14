import unittest

from rate_limiter import PerUserRateLimiter


class PerUserRateLimiterTests(unittest.TestCase):
    def test_allows_only_forty_requests_in_a_rolling_minute(self):
        limiter = PerUserRateLimiter(limit=40, window_seconds=60)

        for _ in range(40):
            self.assertTrue(limiter.allow(101, now=100.0))
        self.assertFalse(limiter.allow(101, now=159.9))
        self.assertTrue(limiter.allow(101, now=160.0))

    def test_limits_are_independent_for_each_user(self):
        limiter = PerUserRateLimiter(limit=1, window_seconds=60)

        self.assertTrue(limiter.allow(101, now=0.0))
        self.assertFalse(limiter.allow(101, now=1.0))
        self.assertTrue(limiter.allow(202, now=1.0))

    def test_sends_only_one_overload_warning_per_minute(self):
        limiter = PerUserRateLimiter(limit=1, window_seconds=60)

        self.assertTrue(limiter.should_notify(101, now=0.0))
        self.assertFalse(limiter.should_notify(101, now=59.9))
        self.assertTrue(limiter.should_notify(101, now=60.0))


if __name__ == "__main__":
    unittest.main()
