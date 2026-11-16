"""저장된 강남 모델로 마포구 상습 투기지역 주변의 위험 순위를 평가한다."""
import joblib
import pandas as pd
from scipy.spatial import cKDTree

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C


def main():
    output = C.EDA_OUT_DIR
    model_path = output / "1_강남_최종모델.joblib"
    if not model_path.is_file():\
        raise SystemExit("먼저 1_B2C_비흡연자_간접흡연위험지도.py를 실행해 강남 모델을 저장하세요.")

    bundle = joblib.load(model_path)
    sites = pd.read_csv(output / "특성_마포구" / "지점특성.csv")
    hot = pd.read_csv(output / "1_마포_상습지역_좌표.csv")
    sites = sites.loc[sites["분석대상"].eq(1)].reset_index(drop=True)
    if sites.empty or hot.empty:
        raise ValueError("마포 분석 대상 보행 노드와 상습지역 좌표가 필요합니다.")

    columns = ["위도", "경도"]
    if sites[columns].isna().any().any() or hot[columns].isna().any().any():
        raise ValueError("마포 검증 데이터에 누락된 좌표가 있습니다.")

    scores = bundle["모델"].predict_proba(sites[bundle["특성"]])[:, 1]
    predictions = sites[["노드 ID", "격자ID", *columns]].copy()
    predictions["위험확률"] = scores
    predictions["위험점수"] = predictions["위험확률"].rank(pct=True) * 100
    predictions["상위10%"] = predictions["위험점수"] > 90

    print("<마포 상습지역과 가장 가까운 검증 노드 연결>")
    print("######################################################################")
    tree = cKDTree(C.xy_m(sites["위도"], sites["경도"]))
    distance, nearest = tree.query(C.xy_m(hot["위도"], hot["경도"]))
    matched = predictions.iloc[nearest].reset_index(drop=True)

    result = hot[["도로명주소", "세부위치", *columns]].copy()
    result["최근접_노드_ID"] = matched["노드 ID"]
    result["최근접_노드_거리m"] = distance.round(2)
    result["최근접_노드_위험확률"] = matched["위험확률"].round(6)
    result["최근접_노드_위험점수"] = matched["위험점수"].round(2)
    result["상위10%"] = matched["상위10%"]
    result[f"{C.LABEL_R}m_이내"] = distance <= C.LABEL_R
    C.OUT_DIR = str(output)
    C.save(predictions.round({"위험확률": 6, "위험점수": 2}), "1_마포_보행노드_예측.csv")
    C.save(result, "1_마포_상습지역_검증결과.csv")

    top_count = int(matched["상위10%"].sum())
    within = distance <= C.LABEL_R
    print(f"강남 모델 {bundle['모델명']} | 마포 검증 노드 {len(sites):,}개")
    print(f"상습지역 {len(hot)}곳 중 상위 10% 연결 {top_count}곳 ({top_count / len(hot):.1%})")
    print(f"연결 노드 위험점수 중앙값 {matched['위험점수'].median():.1f}점")
    print(f"최근접 노드 거리 {distance.min():.1f}~{distance.max():.1f}m")
    print(f"{C.LABEL_R}m 이내 연결 {within.sum()}곳, 그중 상위 10% {matched.loc[within, '상위10%'].sum()}곳")
    print("######################################################################")


if __name__ == "__main__":
    main()
