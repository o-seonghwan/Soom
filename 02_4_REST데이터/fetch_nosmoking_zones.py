"""
전국금연구역표준데이터 Open API → 서울 금연구역 CSV 저장

필요 패키지:  pip install requests pandas python-dotenv
실행:        python fetch_nosmoking_zones.py

.env 예시 (변수 이름은 아래 ENV_KEY_NAME과 맞춰주세요)
    DATA_GO_KR_SERVICE_KEY=발급받은_일반인증키(Decoding)
"""

import os
import sys
import time
import json
from urllib.parse import unquote

import requests
import pandas as pd
from dotenv import load_dotenv

# ───────── 설정 ─────────
ENV_KEY_NAME = "API_KEY"   # .env에 저장한 변수 이름으로 바꿔주세요
ENDPOINT = "https://api.data.go.kr/openapi/tn_pubr_public_prhsmk_zn_api"
TARGET_SIDO = "서울특별시"
SIDO_PARAM = "ctprvnNm"                   # 시도명 필터 파라미터(추정) → 아래에서 실제로 먹히는지 검사함
ROWS_PER_PAGE = 1000
OUT_RAW = "nosmoking_zones_raw.csv"       # 받은 원본(필터 실패 시 전국)
OUT_SEOUL = "nosmoking_zones_seoul.csv"   # 서울만

# API 영문 필드 → 표준데이터 한글 컬럼명 (실제 응답으로 확인함)
COL_KR = {
    "prhsmkNm": "금연구역명", "prhsmkScopeDesc": "금연구역범위상세",
    "ctprvnNm": "시도명", "signguNm": "시군구명", "prhsmkSe": "금연구역구분",
    "prhsmkAppnBasis": "금연구역지정근거명", "prhsmkAr": "금연구역면적",
    "ffnlg": "위반과태료", "phoneNumber": "위반신고전화번호",
    "rdnmadr": "소재지도로명주소", "lnmadr": "소재지지번주소",
    "institutionNm": "관리기관명", "latitude": "위도", "longitude": "경도",
    "referenceDate": "데이터기준일자", "insttCode": "제공기관코드", "insttNm": "제공기관명",
}
# ────────────────────────


def get_service_key() -> str:
    load_dotenv()
    key = os.getenv(ENV_KEY_NAME)
    if not key:
        sys.exit(f"[에러] .env에서 '{ENV_KEY_NAME}'를 찾지 못했습니다. 변수 이름을 확인하세요.")
    # Encoding 키(%2B 등 포함)를 넣었으면 Decoding 키로 바꿔서 이중 인코딩을 막음
    return unquote(key.strip())


def call_api(key: str, page: int, rows: int, extra: dict | None = None, retries: int = 3) -> dict:
    params = {"serviceKey": key, "pageNo": page, "numOfRows": rows, "type": "json"}
    if extra:
        params.update(extra)
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(ENDPOINT, params=params, timeout=30)
            r.raise_for_status()
            try:
                data = r.json()
            except json.JSONDecodeError:
                # 인증 오류 등은 type=json이어도 XML로 오는 경우가 많음
                sys.exit(f"[에러] JSON이 아닌 응답이 왔습니다(인증키/활용신청 확인):\n{r.text[:500]}")
            root = data.get("response", data)   # 이 API는 'response' 껍데기 없이 header/body가 바로 옴
            header = root.get("header", {})
            code = str(header.get("resultCode", ""))
            if not header:
                # 예상과 다른 구조 → 원문을 보여주고 멈춤 (인증키 값은 가림)
                safe_url = r.url.split("serviceKey=")[0] + "serviceKey=***&" + \
                    "&".join(x for x in r.url.split("&") if not x.startswith(("serviceKey=", "http")))
                sys.exit("[에러] 예상과 다른 응답 구조입니다. 아래 내용을 그대로 공유해주세요.\n"
                         f"요청 URL: {safe_url}\nHTTP {r.status_code}\n응답 원문: {r.text[:800]}")
            if code not in ("00", "0"):
                # 03 = 데이터 없음
                if code == "03":
                    return {"totalCount": 0, "items": []}
                sys.exit(f"[에러] API 오류 {code}: {header.get('resultMsg')}")
            body = root["body"]
            items = body.get("items", [])
            if isinstance(items, dict):          # {"item": [...]} 형태 대응
                items = items.get("item", [])
            if isinstance(items, dict):          # 1건이면 dict로 오는 경우
                items = [items]
            return {"totalCount": int(body.get("totalCount", 0)), "items": items}
        except requests.RequestException as e:
            print(f"  요청 실패({attempt}/{retries}): {e}")
            time.sleep(2 * attempt)
    sys.exit("[에러] 재시도 후에도 요청에 실패했습니다.")


def fetch_all(key: str, extra: dict | None, total: int) -> list[dict]:
    pages = (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
    rows = []
    for p in range(1, pages + 1):
        res = call_api(key, p, ROWS_PER_PAGE, extra)
        rows.extend(res["items"])
        print(f"  {p}/{pages} 페이지, 누적 {len(rows):,}건")
        time.sleep(0.2)
    return rows


def filter_seoul(df: pd.DataFrame) -> pd.DataFrame:
    # 시도명 컬럼을 이름이 아니라 값으로 찾음(영문 컬럼명을 몰라도 동작)
    for col in df.columns:
        if df[col].astype(str).eq(TARGET_SIDO).any():
            print(f"  시도명 컬럼으로 '{col}' 사용")
            return df[df[col].astype(str).eq(TARGET_SIDO)]
    # 없으면 주소 문자열로 판별
    mask = df.apply(lambda r: r.astype(str).str.startswith(TARGET_SIDO).any(), axis=1)
    print("  시도명 컬럼을 못 찾아 주소 문자열로 걸렀습니다.")
    return df[mask]


def main():
    key = get_service_key()

    # 1) 전체 건수와 필드 이름 확인
    probe_all = call_api(key, 1, 1)
    print(f"[확인] 전국 totalCount = {probe_all['totalCount']:,}")
    if probe_all["items"]:
        print("[확인] 응답 필드 이름:", list(probe_all["items"][0].keys()))

    # 2) 시도 필터 파라미터가 실제로 먹히는지 검사
    probe_seoul = call_api(key, 1, 1, {SIDO_PARAM: TARGET_SIDO})
    filter_works = 0 < probe_seoul["totalCount"] < probe_all["totalCount"]
    print(f"[확인] '{SIDO_PARAM}={TARGET_SIDO}' 필터 결과 = {probe_seoul['totalCount']:,}건 "
          f"→ {'필터 작동' if filter_works else '필터 미작동, 전국을 받아서 거름'}")

    # 3) 수집
    if filter_works:
        rows = fetch_all(key, {SIDO_PARAM: TARGET_SIDO}, probe_seoul["totalCount"])
    else:
        rows = fetch_all(key, None, probe_all["totalCount"])

    df = pd.DataFrame(rows).rename(columns=COL_KR)
    df.to_csv(OUT_RAW, index=False, encoding="utf-8-sig")
    print(f"[저장] {OUT_RAW} ({len(df):,}건)")

    seoul = filter_seoul(df)
    seoul.to_csv(OUT_SEOUL, index=False, encoding="utf-8-sig")
    print(f"[저장] {OUT_SEOUL} ({len(seoul):,}건)")

    # 4) 간단 점검
    if "위도" in seoul.columns:
        miss = seoul["위도"].isna() | seoul["위도"].astype(str).str.strip().eq("")
        print(f"[점검] 위도 결측 {miss.sum():,}건")
    if "금연구역구분" in seoul.columns:
        print("[점검] 금연구역구분 상위 15개:")
        print(seoul["금연구역구분"].value_counts().head(15).to_string())


if __name__ == "__main__":
    main()
