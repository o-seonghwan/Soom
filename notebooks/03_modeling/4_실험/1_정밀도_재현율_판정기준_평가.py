"""공간 검증에서 XGBoost의 F1·F2 임계값을 비교한다."""
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.metrics import confusion_matrix, precision_recall_curve
from sklearn.model_selection import StratifiedGroupKFold

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
    if not data[keys].equals(roles[keys]):
        raise ValueError("학습 CSV와 분할표가 다릅니다. 0_공간5Fold_분할.py를 다시 실행하세요.")
    X, y = data[C.model_features(data)], data["정답"]
    xy = C.xy_m(data["위도"], data["경도"])
    rows = []
    for number in range(1, 6):
        fold = f"Fold_{number}"
        outer_train = np.flatnonzero(roles[fold].eq("학습"))
        test = np.flatnonzero(roles[fold].eq("검증"))
        splitter = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=100)
        train_idx, calibration_idx = next(splitter.split(
            X.iloc[outer_train], y.iloc[outer_train], groups=data["블록"].iloc[outer_train]
        ))
        train, calibration = outer_train[train_idx], outer_train[calibration_idx]
        distance, _ = cKDTree(xy[calibration]).query(xy[train])
        train = train[distance > 2 * C.LABEL_R]
        if any(set(y.iloc[idx]) != {0, 1} for idx in (train, calibration, test)):
            raise ValueError(f"{fold}의 학습·임계값 선택·평가에 정답 0과 1이 모두 필요합니다.")

        model = C.prepare_classifier(classifier(**params)).fit(X.iloc[train], y.iloc[train])
        cal_scores = model.predict_proba(X.iloc[calibration])[:, 1]
        precision, recall, thresholds = precision_recall_curve(y.iloc[calibration], cal_scores)
        precision, recall = precision[:-1], recall[:-1]
        rules = {"기본 0.5": 0.5}
        for beta in (1, 2):
            denominator = beta**2 * precision + recall
            metric = np.divide((1 + beta**2) * precision * recall, denominator,
                               out=np.zeros_like(denominator), where=denominator > 0)
            rules[f"F{beta} 기준"] = thresholds[np.argmax(metric)]

        scores = model.predict_proba(X.iloc[test])[:, 1]
        for rule, threshold in rules.items():
            tn, fp, fn, tp = confusion_matrix(y.iloc[test], scores >= threshold, labels=[0, 1]).ravel()
            rows.append({"폴드": fold, "방법": rule, "임계값": threshold, "TP": tp, "FP": fp, "FN": fn, "TN": tn})

    detail = pd.DataFrame(rows)
    summary = detail.groupby("방법", sort=False, as_index=False).agg(
        임계값_최소=("임계값", "min"), 임계값_최대=("임계값", "max"),
        TP=("TP", "sum"), FP=("FP", "sum"), FN=("FN", "sum"), TN=("TN", "sum"),
    )
    for frame in (detail, summary):
        tp, fp, fn = frame["TP"], frame["FP"], frame["FN"]
        frame["선택노드"] = tp + fp
        frame["정밀도"] = tp.div((tp + fp).replace(0, np.nan)).fillna(0)
        frame["재현율"] = tp / (tp + fn)
        frame["F1"] = 2 * tp / (2 * tp + fp + fn)
        frame["F2"] = 5 * tp / (5 * tp + fp + 4 * fn)
    C.OUT_DIR = str(C.EDA_OUT_DIR)
    C.save(detail.round(8), "1_판정기준_비교_폴드별.csv")
    C.save(summary.round(8), "1_판정기준_비교_요약.csv")
    print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
