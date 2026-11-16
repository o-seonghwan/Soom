"""강남 공간 5-Fold의 검증 예측으로 F2가 최대인 단일 임계값을 찾는다."""
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_curve

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C


def main():
    tuning = runpy.run_path(str(Path(__file__).with_name("1_XGBoost_LightGBM_튜닝.py")))
    classifier, defaults, candidates = tuning["MODELS"]["XGBoost"]
    params = {**tuning["SHARED"], **defaults, **candidates[0]}
    data = pd.read_csv(C.TRAINING_DATA_PATH, float_precision="round_trip")
    roles = pd.read_csv(C.EDA_OUT_DIR / "1_강남_공간5Fold_분할.csv")
    keys = ["노드 ID", "블록", "정답"]
    folds = [f"Fold_{i}" for i in range(1, 6)]
    if not data[keys].equals(roles[keys]) or not roles[folds].eq("검증").sum(axis=1).eq(1).all():
        raise ValueError("0_공간5Fold_분할.py를 실행해 현재 데이터의 분할표를 준비하세요.")

    X, y = data[C.model_features(data)], data["정답"]
    scores = np.full(len(data), np.nan)
    for fold in folds:
        train = roles[fold].eq("학습")
        valid = roles[fold].eq("검증")
        model = C.prepare_classifier(classifier(**params)).fit(X.loc[train], y[train])
        scores[valid] = model.predict_proba(X.loc[valid])[:, 1]

    precision, recall, thresholds = precision_recall_curve(y, scores)
    precision, recall = precision[:-1], recall[:-1]
    denominator = 4 * precision + recall
    f2 = np.divide(5 * precision * recall, denominator,
                   out=np.zeros_like(denominator), where=denominator > 0)
    # 동점일 때는 더 높은 임계값을 선택한다.
    best = np.flatnonzero(f2 == f2.max())[-1]
    threshold = thresholds[best]
    tn, fp, fn, tp = confusion_matrix(y, scores >= threshold, labels=[0, 1]).ravel()
    result = pd.DataFrame([{
        "임계값": threshold, "F2": f2[best], "정밀도": precision[best], "재현율": recall[best],
        "선택노드": tp + fp, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
    }])
    C.OUT_DIR = str(C.EDA_OUT_DIR)
    C.save(result, "1_F2_최대_임계값.csv")
    print(result.to_string(index=False))
    print("이 임계값과 지표는 같은 폴드별 검증 예측에서 계산한 탐색 결과입니다.")


if __name__ == "__main__":
    main()
