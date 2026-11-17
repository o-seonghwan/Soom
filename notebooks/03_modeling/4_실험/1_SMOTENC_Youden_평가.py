"""공간 5-Fold에서 SMOTENC와 Youden 지수를 함께 평가한다."""
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTENC
from scipy.spatial import cKDTree
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

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
    categorical = ["붙은길_큰길", "붙은길_골목"]
    continuous = X.columns.difference(categorical, sort=False)
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
            raise ValueError(f"{fold}의 학습·기준선택·평가에 정답 0과 1이 모두 필요합니다.")

        imputer = SimpleImputer(strategy="median", keep_empty_features=True).set_output(transform="pandas")
        x_train = imputer.fit_transform(X.iloc[train])
        x_calibration = imputer.transform(X.iloc[calibration])
        x_test = imputer.transform(X.iloc[test])
        scaler = StandardScaler()
        scaled = x_train.astype(float)
        scaled[continuous] = scaler.fit_transform(x_train[continuous])

        for ratio in (0.10, 0.25):
            sampler = SMOTENC(categorical_features=categorical, sampling_strategy=ratio, random_state=100)
            sampled, target = sampler.fit_resample(scaled, y.iloc[train])
            sampled[continuous] = scaler.inverse_transform(sampled[continuous])
            model = classifier(**params).fit(sampled, target)
            calibration_scores = model.predict_proba(x_calibration)[:, 1]
            fpr, tpr, thresholds = roc_curve(y.iloc[calibration], calibration_scores, drop_intermediate=False)
            youden_threshold = float(thresholds[1 + np.argmax((tpr - fpr)[1:])])
            scores = model.predict_proba(x_test)[:, 1]
            actual = y.iloc[test]

            for method, threshold in (("기본 0.5", 0.5), ("Youden", youden_threshold)):
                tn, fp, fn, tp = confusion_matrix(actual, scores >= threshold, labels=[0, 1]).ravel()
                recall = tp / (tp + fn)
                specificity = tn / (tn + fp)
                rows.append({
                    "폴드": fold, "SMOTENC_1대0_비율": ratio, "판정방법": method,
                    "임계값": threshold, "합성_추가건수": len(target) - len(train),
                    "학습_원본수": len(train), "임계값_선택수": len(calibration), "평가수": len(test),
                    "AP": average_precision_score(actual, scores), "AUC": roc_auc_score(actual, scores),
                    "정밀도": tp / (tp + fp) if tp + fp else 0.0,
                    "재현율": recall, "특이도": specificity, "Youden_J": recall + specificity - 1,
                    "정확도": (tp + tn) / len(test), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                })

    results = pd.DataFrame(rows)
    summary = results.groupby(["SMOTENC_1대0_비율", "판정방법"], sort=False, as_index=False).agg(
        평균_AP=("AP", "mean"), 평균_AUC=("AUC", "mean"),
        임계값_최솟값=("임계값", "min"), 임계값_최댓값=("임계값", "max"),
        TP=("TP", "sum"), FP=("FP", "sum"), FN=("FN", "sum"), TN=("TN", "sum"),
    )
    summary["정밀도"] = summary["TP"].div((summary["TP"] + summary["FP"]).replace(0, np.nan)).fillna(0)
    summary["재현율"] = summary["TP"] / (summary["TP"] + summary["FN"])
    summary["특이도"] = summary["TN"] / (summary["TN"] + summary["FP"])
    summary["Youden_J"] = summary["재현율"] + summary["특이도"] - 1
    summary["정확도"] = (summary["TP"] + summary["TN"]) / summary[["TP", "FP", "FN", "TN"]].sum(axis=1)
    C.OUT_DIR = str(C.EDA_OUT_DIR)
    C.save(results.round(8), "1_SMOTENC_Youden_폴드별.csv")
    C.save(summary.round(8), "1_SMOTENC_Youden_요약.csv")
    print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
