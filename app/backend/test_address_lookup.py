"""VWorld reverse geocoding configuration and failure-safe behavior (no live network)."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from address_lookup import reverse_address, _cached_vworld


def vworld_response(status="OK", items=None):
    response = Mock()
    response.json.return_value = {"response": {"status": status, "result": items or []}}
    return response


class ReverseAddressTests(unittest.TestCase):
    def setUp(self):
        self.original = os.environ.get("VWORLD_API_KEY")
        os.environ.pop("VWORLD_API_KEY", None)
        _cached_vworld.cache_clear()

    def tearDown(self):
        if self.original is None:
            os.environ.pop("VWORLD_API_KEY", None)
        else:
            os.environ["VWORLD_API_KEY"] = self.original

    def test_missing_key_returns_null_without_external_request(self):
        with patch("address_lookup.requests.get") as get:
            self.assertEqual(reverse_address(37.50, 127.02), {"address": None, "source": "unconfigured"})
            get.assert_not_called()

    def test_invalid_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            reverse_address(float("nan"), 127.02)

    def test_road_address_first_lng_lat_order_and_cache(self):
        os.environ["VWORLD_API_KEY"] = "dummy"
        items = [{"type": "parcel", "text": "서울특별시 강남구 역삼동 1"},
                 {"type": "road", "text": "서울특별시 강남구 테헤란로 1"}]
        with patch("address_lookup.requests.get", return_value=vworld_response(items=items)) as get:
            a = reverse_address(37.5, 127.02)
            b = reverse_address(37.5, 127.02)
        self.assertEqual(a, {"address": "서울특별시 강남구 테헤란로 1", "source": "vworld-road"})
        self.assertEqual(a, b)
        self.assertEqual(get.call_count, 1)
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["point"], "127.02,37.5")
        self.assertEqual(params["request"], "getaddress")

    def test_parcel_when_no_road_address(self):
        os.environ["VWORLD_API_KEY"] = "dummy"
        items = [{"type": "parcel", "text": "서울특별시 강남구 역삼동 1"}]
        with patch("address_lookup.requests.get", return_value=vworld_response(items=items)):
            self.assertEqual(reverse_address(37.5, 127.02),
                             {"address": "서울특별시 강남구 역삼동 1", "source": "vworld-parcel"})

    def test_not_found_returns_null(self):
        os.environ["VWORLD_API_KEY"] = "dummy"
        with patch("address_lookup.requests.get", return_value=vworld_response("NOT_FOUND")):
            self.assertEqual(reverse_address(37.5, 127.02), {"address": None, "source": "vworld-empty"})

    def test_error_status_raises_request_exception(self):
        os.environ["VWORLD_API_KEY"] = "dummy"
        with patch("address_lookup.requests.get", return_value=vworld_response("ERROR")):
            with self.assertRaises(requests.RequestException):
                reverse_address(37.5, 127.02)


if __name__ == "__main__":
    unittest.main()
