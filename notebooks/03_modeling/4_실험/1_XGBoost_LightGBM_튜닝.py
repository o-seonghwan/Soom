"""강남구 공간 5-Fold로 XGBoost와 LightGBM의 후보 설정을 비교한다."""
import json

import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from xgboost import XGBClassifier

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C


SHARED = {
    "n_estimators": 400,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "n_jobs": 4,
    "random_state": 100,
}
MODELS = {
    "XGBoost": (
        XGBClassifier,
        {"max_depth": 6, "verbosity": 0},
        [
            {"max_depth": 3},
            {"max_depth": 4},
            {"max_depth": 8},
            {"n_estimators": 200, "learning_rate": 0.1},
            {"n_estimators": 650, "learning_rate": 0.03, "max_depth": 4},
            {"max_depth": 4, "scale_pos_weight": 3},
            {"max_depth": 4, "scale_pos_weight": 6},
        ],
    ),
    "LightGBM": (
        LGBMClassifier,
        {"num_leaves": 31, "subsample_freq": 1, "verbose": -1},
        [
            {"num_leaves": 15},
            {"num_leaves": 63},
            {"num_leaves": 15, "min_child_samples": 50},
            {"n_estimators": 200, "learning_rate": 0.1},
            {"n_estimators": 650, "learning_rate": 0.03, "num_leaves": 15},
            {"num_leaves": 15, "scale_pos_weight": 3},
            {"num_leaves": 15, "scale_pos_weight": 6},
        ],
    ),
}


def main():
    data = pd.read_csv(C.TRAINING_DATA_PATH, float_precision="round_trip")
    split_path = C.EDA_OUT_DIR / "1_강남_공간5Fold_분할.csv"
    if not split_path.is_file():
        raise SystemExit("먼저 0_공간5Fold_분할.py를 실행하세요.")
    roles = pd.read_csv(split_path)
    keys = ["노드 ID", "블록", "정답"]
    folds = [f"Fold_{number}" for number in range(1, 6)]
    if not data[keys].equals(roles[keys]):
        raise ValueError("현재 학습 CSV와 분할표가 다릅니다. 0_공간5Fold_분할.py를 다시 실행하세요.")
    if not roles[folds].eq("검증").sum(axis=1).eq(1).all():
        raise ValueError("각 노드는 정확히 한 번 검증에 포함되어야 합니다.")

    features = C.model_features(data)
    if len(features) != len(C.FEATURES):
        raise ValueError("학습 CSV에 필요한 모델 특성이 빠져 있습니다.")
    X, y = data[features], data["정답"]
    rows = []
    for name, (classifier, defaults, candidates) in MODELS.items():
        print(f"<{name} 하이퍼파라미터 튜닝>", flush=True)
        print("######################################################################")
        for index, changes in enumerate([{}, *candidates]):
            label = "기존 설정" if index == 0 else f"후보 {index}"
            params = {**SHARED, **defaults, **changes}
            fold_results = []
            for fold in folds:
                train = roles[fold].eq("학습")
                test = roles[fold].eq("검증")
                if set(y[train]) != {0, 1} or set(y[test]) != {0, 1}:
                    raise ValueError(f"{fold}의 학습·검증 데이터에 정답 0과 1이 모두 필요합니다.")
                model = C.prepare_classifier(classifier(**params))
                model.fit(X.loc[train], y[train])
                scores = model.predict_proba(X.loc[test])[:, 1]
                fold_results.append({
                    "모델": name,
                    "설정": label,
                    "파라미터": json.dumps(params, sort_keys=True),
                    "폴드": fold,
                    "AP": average_precision_score(y[test], scores),
                    "AUC": roc_auc_score(y[test], scores),
                    "상위10%_정답포착률": C.top_capture(y[test], scores),
                })
            rows.extend(fold_results)
            mean_ap = sum(row["AP"] for row in fold_results) / len(folds)
            print(f"{label} | 평균 AP {mean_ap:.4f}", flush=True)
        print("######################################################################")

    results = pd.DataFrame(rows)
    summary = results.groupby(["모델", "설정", "파라미터"], sort=False, as_index=False).agg(
        평균_AP=("AP", "mean"),
        AP_표준편차=("AP", "std"),
        평균_AUC=("AUC", "mean"),
        **{"평균_상위10%_정답포착률": ("상위10%_정답포착률", "mean")},
    )
    baseline = summary.loc[summary["설정"].eq("기존 설정")].set_index("모델")["평균_AP"]
    summary["기존대비_AP차이"] = summary["평균_AP"] - summary["모델"].map(baseline)
    summary = summary.sort_values("평균_AP", ascending=False)
    C.OUT_DIR = str(C.EDA_OUT_DIR)
    C.save(results.round(6), "1_부스팅_튜닝_폴드별.csv")
    C.save(summary.round(6), "1_부스팅_튜닝_요약.csv")
    print(summary.drop(columns="파라미터").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
