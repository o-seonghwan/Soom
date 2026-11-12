
import json
from pathlib import Path
from urllib.request import Request, urlopen

# 프로젝트 경로
BASE_DIR = Path(__file__).resolve().parents[2]

OUTPUT_PATH = (
    BASE_DIR
    / "app"
    / "frontend"
    / "public"
    / "gangnam_boundary.geojson"
)

# 공개 행정경계 GeoJSON 데이터
SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "KnellBalm/kr-admin-geojson/"
    "main/sig.geojson"
)

GANGNAM_CODE = "11680"


def main():
    print("강남구 행정경계 다운로드 시작")

    request = Request(
        SOURCE_URL,
        headers={
            "User-Agent": "GangnamWalkingRouteProject/1.0"
        },
    )

    with urlopen(request, timeout=60) as response:
        data = json.load(response)

    # 강남구 경계 추출
    features = [
        feature
        for feature in data["features"]
        if str(
            feature.get("properties", {}).get("SIG_CD")
        ) == GANGNAM_CODE
    ]

    if len(features) != 1:
        raise ValueError(
            f"강남구 경계를 찾지 못했습니다: {len(features)}개"
        )

    boundary = {
        "type": "FeatureCollection",
        "features": features,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            boundary,
            file,
            ensure_ascii=False,
        )

    print("강남구 경계 저장 완료")
    print(f"저장 위치: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
