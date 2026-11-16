"""Geocoding configuration and failure-safe behavior (no live network)."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from address_lookup import reverse_address, _cached_kakao


class ReverseAddressTests(unittest.TestCase):
    def setUp(self):
        self.original = os.environ.get("KAKAO_REST_API_KEY")
        _cached_kakao.cache_clear()

    def tearDown(self):
        if self.original is None:
            os.environ.pop("KAKAO_REST_API_KEY", None)
        else:
            os.environ["KAKAO_REST_API_KEY"] = self.original

    def test_missing_key_returns_null_without_external_request(self):
        os.environ.pop("KAKAO_REST_API_KEY", None)
        with patch("address_lookup.requests.get") as get:
            self.assertEqual(reverse_address(37.50, 127.02), {"address": None, "source": "unconfigured"})
            get.assert_not_called()

    def test_invalid_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            reverse_address(float("nan"), 127.02)

    def test_kakao_road_address_and_cache(self):
        os.environ["KAKAO_REST_API_KEY"] = "dummy"
        response = Mock()
        response.json.return_value = {"documents": [{"road_address": {"address_name": "서울특별시 강남구 테스트로 1"}, "address": None}]}
        with patch("address_lookup.requests.get", return_value=response) as get:
            a = reverse_address(37.5, 127.02)
            b = reverse_address(37.5, 127.02)
            self.assertEqual(a["address"], "서울특별시 강남구 테스트로 1")
            self.assertEqual(a, b)
            self.assertEqual(get.call_count, 1)
            self.assertIn("KakaoAK dummy", get.call_args.kwargs["headers"]["Authorization"])


if __name__ == "__main__":
    unittest.main()
