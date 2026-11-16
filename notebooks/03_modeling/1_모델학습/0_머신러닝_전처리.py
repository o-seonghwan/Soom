"""
1번 간접흡연 위험지도 학습용 데이터 전처리.

실행: python 0_머신러닝_전처리.py
결과: 결과/전처리기반/1_학습용_지점_21m.csv
"""
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C

end = "\n"


def prepare_other(features, gu, code):
    path = C.eda_tables("*마포구_담배꽁초*", "clean.csv")[0]
    hot = C.read_csv_any(path, dtype=str)
    hot = hot.dropna(subset=["도로명주소"])
    q = [(a.strip(), "road") for a in hot["도로명주소"]]
    hit = C.geocode_many(q, f"vworld_캐시_{gu}.csv", (37.52, 37.60, 126.85, 126.97))
    hot["위도"] = [hit.get(k, (None, None))[0] for k in q]; hot["경도"] = [hit.get(k, (None, None))[1] for k in q]
    hot = hot.dropna(subset=["위도"])
    if hot.empty:
        C.log("다른 구 상습 투기지역 좌표를 찾지 못해(VWorld 키 필요) 검증을 건너뜁니다.")
        return None
    nodes, _ = C.build_features(gu, code)
    d = nodes[nodes["분석대상"] == 1].reset_index(drop=True)
    sites = d[["위도", "경도"] + features].replace([np.inf, -np.inf], np.nan)
    C.save(hot, "1_마포_상습지역_좌표.csv")
    C.save(sites, "1_마포_검증지점.csv")


def main():
    # 데이터 불러와서 변수에 저장하고 정답 붙이기
    print("<데이터 불러오기와 정답 붙이기>")
    print("######################################################################")
    C.use_preprocessed_data()
    nodes, _ = C.build_features()
    df = nodes[nodes["분석대상"] == 1].reset_index(drop=True)
    places = C.butt_places().dropna(subset=["위도", "경도"])
    df = df.join(C.label_nodes(df, places))
    df["블록"] = C.spatial_blocks(df)
    FE = C.model_features(df)
    data = df[FE + ["정답"]].replace([np.inf, -np.inf], np.nan)
    n_blocks = df["블록"].nunique()
    positive_rate = data["정답"].mean()
    C.log(f"지점 {len(df):,}개 | 정답(=1) 비율 {positive_rate:.1%} | 특성 {len(FE)}개 | 블록 {n_blocks}개")
    print("######################################################################", end)

    # 기본 정보 확인
    print("<head>")
    print("######################################################################")
    print(data.head().to_string(index=False))
    print("######################################################################", end)

    print("<tail>")
    print("######################################################################")
    print(data.tail().to_string(index=False))
    print("######################################################################", end)

    print("<info>")
    print("######################################################################")
    data.info()
    print("######################################################################", end)

    print("<describe>")
    print("######################################################################")
    print(data.describe().round(2).T.to_string())
    print("######################################################################", end)

    print("<정답과 각 특성의 상관계수>")
    print("######################################################################")
    print(data.corr(numeric_only=True)["정답"].drop("정답").sort_values(ascending=False).round(2))
    print("######################################################################", end)

    print("<학습용 CSV 저장>")
    print("######################################################################")
    if C.VALIDATE_OTHER_GU:
        prepare_other(FE, *C.VALIDATE_OTHER_GU)

    # 블록과 좌표는 시험셋 분할 및 지도 출력에 사용한다.
    metadata = ["노드 ID", "격자ID", "위도", "경도", "블록"] + C.LABEL_DETAIL_COLUMNS
    training_table = df[metadata].join(data)
    path = C.TRAINING_DATA_PATH
    with NamedTemporaryFile(dir=path.parent, suffix=".csv", delete=False) as handle:
        temporary_path = Path(handle.name)
    try:
        training_table.to_csv(temporary_path, index=False, encoding="utf-8-sig")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    print(f"학습용 CSV 저장 완료 {path}")
    summary = C.summarize_distance_risk(training_table)
    C.save(summary, "1_적발거리_위험등급_요약_21m.csv")
    print(summary.to_string(index=False))
    print("######################################################################", end)


if __name__ == "__main__":
    main()
