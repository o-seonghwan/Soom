"""Kakao coordinate-to-address adapter. Server-only API key, cached results."""
from functools import lru_cache
import math
import os
import requests


def reverse_address(lat: float, lng: float) -> dict:
    if not all(math.isfinite(v) for v in (lat, lng)) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("위도·경도 값이 올바르지 않습니다.")
    key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    if not key:
        return {"address": None, "source": "unconfigured"}
    return _cached_kakao(round(lat, 6), round(lng, 6), key)


@lru_cache(maxsize=2048)
def _cached_kakao(lat: float, lng: float, key: str) -> dict:
    response = requests.get(
        "https://dapi.kakao.com/v2/local/geo/coord2address.json",
        params={"x": str(lng), "y": str(lat), "input_coord": "WGS84"},
        headers={"Authorization": f"KakaoAK {key}"},
        timeout=5,
    )
    response.raise_for_status()
    docs = response.json().get("documents", [])
    if not docs:
        return {"address": None, "source": "kakao-empty"}
    doc = docs[0]
    road = doc.get("road_address")
    land = doc.get("address")
    address = (road or {}).get("address_name") or (land or {}).get("address_name")
    return {"address": address, "source": "kakao"}
