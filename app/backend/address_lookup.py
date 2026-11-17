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


def reverse_address(lat: float, lng: float) -> dict:
    if not all(math.isfinite(v) for v in (lat, lng)) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("위도·경도 값이 올바르지 않습니다.")
    key = os.environ.get("VWORLD_API_KEY", "").strip()
    if not key:
        return {"address": None, "source": "unconfigured"}
    return _cached_vworld(round(lat, 6), round(lng, 6), key)


@lru_cache(maxsize=2048)
def _cached_vworld(lat: float, lng: float, key: str) -> dict:
    response = requests.get(
        VWORLD_URL,
        params={
            "service": "address", "request": "getaddress", "version": "2.0",
            "crs": "EPSG:4326", "point": f"{lng},{lat}",   # VWorld는 경도,위도 순서
            "type": "both", "format": "json", "key": key,
        },
        timeout=5,
    )
    response.raise_for_status()
    body = response.json().get("response", {})
    status = body.get("status")
    if status == "NOT_FOUND":
        return {"address": None, "source": "vworld-empty"}
    if status != "OK":
        # 키 오류·호출 한도 초과 등 → main.py가 503으로 안내. 키가 섞인 URL은 내보내지 않는다.
        raise requests.RequestException(f"VWorld 응답 상태 {status}")
    items = body.get("result") or []
    road = next((i.get("text") for i in items if i.get("type") == "road" and i.get("text")), None)
    parcel = next((i.get("text") for i in items if i.get("type") == "parcel" and i.get("text")), None)
    if road:
        return {"address": road, "source": "vworld-road"}
    if parcel:
        return {"address": parcel, "source": "vworld-parcel"}
    return {"address": None, "source": "vworld-empty"}
