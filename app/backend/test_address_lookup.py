"""Kakao Local address API adapter tests; all requests are mocked."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from address_lookup import (
    _cached_reverse,
    forward_address,
    reverse_address,
    search_addresses,
    KakaoAuthError,
)


def mock_response(documents, status=200):
    result = Mock()
    result.status_code = status
    result.json.return_value = {"documents": documents}
    return result


class AddressLookupTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("KAKAO_REST_API_KEY")
        os.environ.pop("KAKAO_REST_API_KEY", None)
        _cached_reverse.cache_clear()

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("KAKAO_REST_API_KEY", None)
        else:
            os.environ["KAKAO_REST_API_KEY"] = self.previous
        _cached_reverse.cache_clear()

    def test_no_key_reverse_graceful(self):
        with patch("address_lookup.requests.get") as get:
            self.assertEqual(reverse_address(37.5, 127.02), {"address": None, "source": "unconfigured"})
            get.assert_not_called()

    def test_no_key_search_error(self):
        with self.assertRaises(RuntimeError):
            search_addresses("강남역")

    def test_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            reverse_address(float("nan"), 127.02)

    def test_reverse_prefers_road_caches_and_authorizes(self):
        os.environ["KAKAO_REST_API_KEY"] = "dummy"
        docs = [{"road_address": {"address_name": "도로명주소"}, "address": {"address_name": "지번주소"}}]
        with patch("address_lookup.requests.get", return_value=mock_response(docs)) as get:
            self.assertEqual(reverse_address(37.5, 127.02),
                             {"address": "도로명주소", "source": "kakao-road"})
            self.assertEqual(reverse_address(37.5, 127.02),
                             {"address": "도로명주소", "source": "kakao-road"})
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["params"], {"x": 127.02, "y": 37.5})
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "KakaoAK dummy")

    def test_parcel_fallback(self):
        os.environ["KAKAO_REST_API_KEY"] = "dummy"
        with patch("address_lookup.requests.get",
                   return_value=mock_response([{"road_address": None, "address": {"address_name": "지번주소"}}])):
            self.assertEqual(reverse_address(37.5, 127.02)["address"], "지번주소")

    def test_empty_reverse(self):
        os.environ["KAKAO_REST_API_KEY"] = "dummy"
        with patch("address_lookup.requests.get", return_value=mock_response([])):
            self.assertEqual(reverse_address(37.5, 127.02)["source"], "kakao-empty")

    def test_search_place_and_address_contract(self):
        os.environ["KAKAO_REST_API_KEY"] = "dummy"
        place = {"id": "123", "place_name": "강남역", "road_address_name": "서울 강남구",
                 "address_name": "역삼동", "x": "127.02", "y": "37.50"}
        address = {"address_name": "서울 강남구 테헤란로", "x": "127.03", "y": "37.51"}
        with patch("address_lookup.requests.get",
                   side_effect=[mock_response([place]), mock_response([address])]):
            result = search_addresses("강남")
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result[0]), {"id", "title", "address", "lat", "lng", "kind"})
        self.assertEqual(result[0]["kind"], "장소")
        self.assertEqual(result[1]["kind"], "주소")

    def test_forward_address_and_keyword_fallback(self):
        os.environ["KAKAO_REST_API_KEY"] = "dummy"
        place = {"place_name": "강남역", "address_name": "역삼동", "x": "127.02", "y": "37.50"}
        with patch("address_lookup.requests.get",
                   side_effect=[mock_response([]), mock_response([place])]):
            self.assertEqual(forward_address("강남역")["lat"], 37.5)

    def test_http_auth_error(self):
        os.environ["KAKAO_REST_API_KEY"] = "dummy"
        with patch("address_lookup.requests.get", return_value=mock_response([], status=403)):
            with self.assertRaises(KakaoAuthError):
                forward_address("서울 강남구 테헤란로")


if __name__ == "__main__":
    unittest.main()
