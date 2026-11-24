"""Kakao Local API adapter for the existing Soom address endpoints.

Keep the existing frontend payload and endpoint contracts. Credentials are only
sent from the backend; never persist returned address/coordinate data to disk.
"""
from functools import lru_cache
import logging
import math
import os

import requests

BASE = "https://dapi.kakao.com/v2/local"
LOG = logging.getLogger("soom.kakao")


class KakaoAuthError(requests.RequestException):
    """Kakao REST API authentication/permission failure (no credentials in message)."""


def _call(path: str, params: dict) -> dict:
    key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    if not key:
        raise RuntimeError("주소 검색을 사용하려면 서버에 KAKAO_REST_API_KEY 설정이 필요합니다.")
    response = requests.get(
        f"{BASE}/{path}",
        headers={"Authorization": f"KakaoAK {key}"},
        params=params,
        timeout=7,
    )
    if response.status_code in (401, 403):
        raise KakaoAuthError("카카오 로컬 API 인증 또는 접근 권한을 확인하세요.")
    response.raise_for_status()
    return response.json()


def _valid_coordinates(lat, lng) -> bool:
    return math.isfinite(lat) and math.isfinite(lng) and 37 <= lat <= 38 and 126 <= lng <= 128


def _point(item: dict):
    try:
        lat, lng = float(item["y"]), float(item["x"])
    except (KeyError, TypeError, ValueError):
        return None
    if not _valid_coordinates(lat, lng):
        return None
    return lat, lng


def search_addresses(query: str) -> list[dict]:
    """Search both place names and road/parcel addresses."""
    query = query.strip()
    if len(query) < 2:
        return []
    if len(query) > 120:
        raise ValueError("검색어는 최대 120자입니다.")

    suggestions = []
    seen = set()
    for path, kind in (("search/keyword.json", "장소"), ("search/address.json", "주소")):
        response = _call(path, {"query": query, "size": 10})
        for item in response.get("documents", []):
            point = _point(item)
            if point is None:
                continue
            lat, lng = point
            if kind == "장소":
                title = str(item.get("place_name") or "").strip()
                address = str(item.get("road_address_name") or item.get("address_name") or title).strip()
            else:
                title = str(item.get("address_name") or "").strip()
                address = title
            if not title or not address:
                continue
            signature = (round(lat, 6), round(lng, 6), address)
            if signature in seen:
                continue
            seen.add(signature)
            suggestions.append({
                "id": str(len(suggestions) + 1),
                "title": title,
                "address": address,
                "lat": lat,
                "lng": lng,
                "kind": kind,
            })
            if len(suggestions) >= 10:
                return suggestions
    return suggestions


def forward_address(address: str) -> dict:
    """Resolve address or common place name to WGS84 lat/lng."""
    address = address.strip()
    if not (2 <= len(address) <= 200):
        raise ValueError("주소는 2~200자로 입력하세요.")
    # Prefer address search; keyword lookup is the fallback for places such as 강남역.
    for path in ("search/address.json", "search/keyword.json"):
        result = _call(path, {"query": address, "size": 10})
        for item in result.get("documents", []):
            point = _point(item)
            if point is None:
                continue
            lat, lng = point
            label = item.get("road_address_name") or item.get("address_name") or address
            return {"lat": lat, "lng": lng, "address": label}
    raise LookupError("일치하는 주소나 장소를 찾지 못했습니다. 연관검색어 또는 지도를 사용하세요.")


def reverse_address(lat: float, lng: float) -> dict:
    """Prefer road-name address; fall back to parcel address."""
    if not all(math.isfinite(v) for v in (lat, lng)) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("위도·경도 값이 올바르지 않습니다.")
    if not os.environ.get("KAKAO_REST_API_KEY", "").strip():
        return {"address": None, "source": "unconfigured"}
    return _cached_reverse(round(lat, 6), round(lng, 6))


@lru_cache(maxsize=2048)
def _cached_reverse(lat: float, lng: float) -> dict:
    data = _call("geo/coord2address.json", {"x": lng, "y": lat})
    for item in data.get("documents", []):
        road = item.get("road_address") or {}
        parcel = item.get("address") or {}
        if road.get("address_name"):
            return {"address": road["address_name"], "source": "kakao-road"}
        if parcel.get("address_name"):
            return {"address": parcel["address_name"], "source": "kakao-parcel"}
    return {"address": None, "source": "kakao-empty"}
