"""좌표 → 도로명주소 변환(역지오코딩). VWorld(국토교통부 브이월드) 주소 API를 쓴다.

- 키: 환경변수 VWORLD_API_KEY. 서버에서만 쓰고 브라우저로 보내지 않는다.
- 도로명주소를 먼저 쓰고, 도로명주소가 없는 곳(길 한가운데 등)은 지번주소로 대신한다.
- 키가 없으면 {"address": None, "source": "unconfigured"} → 화면은 좌표를 그대로 보여 준다.
- VWorld 이용약관상 조회 결과를 별도 저장장치·데이터베이스에 저장하면 안 된다.
  그래서 파일·DB에는 쓰지 않고, 서버가 켜져 있는 동안만 메모리에 기억한다(같은 좌표 반복 조회 방지).
"""
from functools import lru_cache
import math
import os
import requests

VWORLD_URL = "https://api.vworld.kr/req/address"

def _key_context():
    """VWorld domain-restricted keys can require both domain and Referer."""
    domain = os.environ.get("VWORLD_DOMAIN", "").strip()
    if not domain:
        return {}, {}
    host = domain if domain.startswith(("https://", "http://")) else "https://" + domain
    return {"domain": host}, {"Referer": host.rstrip("/") + "/"}


class VWorldAuthError(requests.RequestException):
    """A domain/key error; no credential is included in the exception."""


def _validated_response(response):
    if response.status_code in (401, 403):
        raise VWorldAuthError("VWorld 인증이 거부됐습니다. VWORLD_API_KEY 및 VWORLD_DOMAIN을 확인하세요.")
    response.raise_for_status()
    body = response.json().get("response", {})
    status = body.get("status")
    if status in ("OK", "NOT_FOUND"):
        return body
    error = body.get("error") or {}
    code = str(error.get("code") or "").upper()
    if code in {"INVALID_KEY", "EXPIRE_KEY", "INVALID_DOMAIN", "INVALID_ACCESS"}:
        raise VWorldAuthError(
            "VWorld API 인증 실패 (" + code + "). 키의 주소/검색 API 사용 권한과 VWORLD_DOMAIN 등록 도메인을 확인하세요."
        )
    raise requests.RequestException(
        "VWorld API 요청 실패. 주소 API 인증키, 등록 도메인 및 서비스 상태를 확인하세요."
    )



def reverse_address(lat: float, lng: float) -> dict:
    if not all(math.isfinite(v) for v in (lat, lng)) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("위도·경도 값이 올바르지 않습니다.")
    key = os.environ.get("VWORLD_API_KEY", "").strip()
    if not key:
        return {"address": None, "source": "unconfigured"}
    return _cached_vworld(round(lat, 6), round(lng, 6), key)


@lru_cache(maxsize=2048)
def _cached_vworld(lat: float, lng: float, key: str) -> dict:
    domain_params, headers = _key_context()
    response = requests.get(
        VWORLD_URL,
        headers=headers,
        params={
            **domain_params,
            "service": "address", "request": "getaddress", "version": "2.0",
            "crs": "EPSG:4326", "point": f"{lng},{lat}",   # VWorld는 경도,위도 순서
            "type": "both", "format": "json", "key": key,
        },
        timeout=5,
    )
    body = _validated_response(response)
    status = body.get("status")
    if status == "NOT_FOUND":
        return {"address": None, "source": "vworld-empty"}
    items = body.get("result") or []
    road = next((i.get("text") for i in items if i.get("type") == "road" and i.get("text")), None)
    parcel = next((i.get("text") for i in items if i.get("type") == "parcel" and i.get("text")), None)
    if road:
        return {"address": road, "source": "vworld-road"}
    if parcel:
        return {"address": parcel, "source": "vworld-parcel"}
    return {"address": None, "source": "vworld-empty"}


VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"


def search_addresses(query: str) -> list[dict]:
    """Suggest matching addresses and places using VWorld Search 2.0."""
    query = query.strip()
    if len(query) < 2:
        return []
    if len(query) > 120:
        raise ValueError("검색어는 최대 120자입니다.")
    key = os.environ.get("VWORLD_API_KEY", "").strip()
    if not key:
        raise RuntimeError("주소 검색을 사용하려면 서버의 VWORLD_API_KEY 설정이 필요합니다.")

    domain_params, headers = _key_context()
    suggestions = []
    seen = set()
    for search_type, category in (("address", "road"), ("address", "parcel"), ("place", None)):
        params = {
            **domain_params,
            "service": "search", "request": "search", "version": "2.0",
            "crs": "EPSG:4326", "type": search_type, "query": query,
            "format": "json", "size": 8, "page": 1, "key": key,
        }
        if category:
            params["category"] = category
        response = requests.get(VWORLD_SEARCH_URL, params=params, headers=headers, timeout=6)
        body = _validated_response(response)
        status = body.get("status")
        if status == "NOT_FOUND":
            continue
        for item in (body.get("result") or {}).get("items") or []:
            point = item.get("point") or {}
            try:
                lat, lng = float(point["y"]), float(point["x"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (math.isfinite(lat) and math.isfinite(lng) and 37 <= lat <= 38 and 126 <= lng <= 128):
                continue
            address = item.get("address") or {}
            road = address.get("road") or ""
            parcel = address.get("parcel") or ""
            title = (item.get("title") or road or parcel or "").strip()
            label = road or parcel or title
            dedup = (round(lat, 6), round(lng, 6), label)
            if not label or dedup in seen:
                continue
            seen.add(dedup)
            suggestions.append({
                "id": str(len(suggestions) + 1),
                "title": title,
                "address": label,
                "lat": lat, "lng": lng,
                "kind": "장소" if search_type == "place" else "도로명" if category == "road" else "지번",
            })
            if len(suggestions) >= 10:
                return suggestions
    return suggestions


def forward_address(address: str) -> dict:
    """Resolve an exact road/parcel address, without exposing VWorld API key."""
    address = address.strip()
    if not (2 <= len(address) <= 200):
        raise ValueError("주소는 2~200자로 입력하세요.")
    key = os.environ.get("VWORLD_API_KEY", "").strip()
    if not key:
        raise RuntimeError("주소 검색을 사용하려면 서버의 VWORLD_API_KEY 설정이 필요합니다.")
    domain_params, headers = _key_context()
    for kind in ("ROAD", "PARCEL"):
        response = requests.get(
            VWORLD_URL,
            headers=headers,
            params={**domain_params, "service": "address", "request": "getcoord", "version": "2.0",
                    "crs": "EPSG:4326", "address": address, "type": kind,
                    "format": "json", "key": key},
            timeout=6,
        )
        body = _validated_response(response)
        if body.get("status") == "NOT_FOUND":
            continue
        point = (body.get("result") or {}).get("point") or {}
        try:
            lat, lng = float(point["y"]), float(point["x"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("주소 좌표 변환에 실패했습니다.") from exc
        if not (math.isfinite(lat) and math.isfinite(lng) and 37 <= lat <= 38 and 126 <= lng <= 128):
            raise ValueError("입력한 주소가 현재 서비스 지역인 서울권 밖에 있습니다.")
        return {"lat": lat, "lng": lng, "address": address}
    raise LookupError("일치하는 도로명·지번 주소를 찾지 못했습니다. 연관검색어 또는 지도를 사용하세요.")
