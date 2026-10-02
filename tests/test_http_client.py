from __future__ import annotations

from io import BytesIO
import unittest
from unittest.mock import call, patch
from urllib.error import HTTPError

from github_trending_daily.http_client import HttpError, get_text


class HttpClientRetryTests(unittest.TestCase):
    def test_retries_gateway_timeout_with_extended_backoff(self) -> None:
        url = "https://github.com/trending?since=daily"
        gateway_timeouts = [
            HTTPError(url, 504, "Gateway Time-out", {}, BytesIO(b"504"))
            for _ in range(5)
        ]
        with (
            patch(
                "github_trending_daily.http_client.urlopen",
                side_effect=[*gateway_timeouts, BytesIO(b"ready")],
            ) as open_mock,
            patch("github_trending_daily.http_client.time.sleep") as sleep_mock,
        ):
            result = get_text(
                url,
                retries=5,
                retry_base_delay=5,
                retry_max_delay=60,
            )
        for error in gateway_timeouts:
            error.close()

        self.assertEqual("ready", result)
        self.assertEqual(6, open_mock.call_count)
        self.assertEqual(
            [call(5), call(10), call(20), call(40), call(60)],
            sleep_mock.call_args_list,
        )

    def test_does_not_retry_authentication_error(self) -> None:
        url = "https://example.com/private"
        unauthorized = HTTPError(url, 401, "Unauthorized", {}, BytesIO(b"invalid key"))
        with (
            patch("github_trending_daily.http_client.urlopen", side_effect=unauthorized)
            as open_mock,
            patch("github_trending_daily.http_client.time.sleep") as sleep_mock,
        ):
            with self.assertRaisesRegex(HttpError, "HTTP 401"):
                get_text(url, retries=5, retry_base_delay=5, retry_max_delay=60)
        unauthorized.close()

        self.assertEqual(1, open_mock.call_count)
        sleep_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
