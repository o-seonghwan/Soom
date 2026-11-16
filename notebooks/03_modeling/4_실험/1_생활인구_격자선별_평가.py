"""생활인구 기준으로 학습 격자를 선별했을 때의 성능을 비교한다."""
import runpy
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C


MIN_POPULATION = 1000


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
    if len(X.columns) != len(C.FEATURES):
        raise ValueError("학습 CSV에 모델 입력 특성이 빠져 있습니다.")
    busy = data["생활인구_15_19"].ge(MIN_POPULATION)
    rows = []
    for number in range(1, 6):
        fold = f"Fold_{number}"
        eligible = roles[fold].eq("학습")
        test = roles[fold].eq("검증")
        for name, train in (("전체 격자", eligible), ("생활인구 기준 적용", eligible & busy)):
            if set(y[train]) != {0, 1}:
                raise ValueError(f"{fold} {name} 학습셋에 정답 0과 1이 모두 필요합니다.")
            model = C.prepare_classifier(classifier(**params)).fit(X.loc[train], y[train])
            scores = pd.Series(model.predict_proba(X.loc[test])[:, 1], index=data.index[test])
            for area, evaluation in (("전체 검증 노드", test), ("생활인구 기준 이상", test & busy)):
                actual = y[evaluation]
                if set(actual) != {0, 1}:
                    raise ValueError(f"{fold} {area} 검증셋에 정답 0과 1이 모두 필요합니다.")
                predicted = scores.loc[actual.index]
                rows.append({
                    "폴드": fold, "학습방식": name, "평가범위": area,
                    "생활인구기준": MIN_POPULATION,
                    "학습격자수": data.loc[train, "격자ID"].nunique(),
                    "학습노드수": int(train.sum()), "학습_정답1": int(y[train].sum()),
                    "학습_정답1비율": y[train].mean(),
                    "검증노드수": len(actual), "검증_정답1": int(actual.sum()),
                    "AP_무작위기준": actual.mean(),
                    "AP": average_precision_score(actual, predicted),
                    "AUC": roc_auc_score(actual, predicted),
                    "상위10%_정답포착률": C.top_capture(actual, predicted),
                })

    results = pd.DataFrame(rows)
    summary = results.groupby(["생활인구기준", "평가범위", "학습방식"], as_index=False, sort=False).agg(
        평균_학습노드수=("학습노드수", "mean"),
        평균_학습_정답1비율=("학습_정답1비율", "mean"),
        평균_AP_무작위기준=("AP_무작위기준", "mean"),
        평균_AP=("AP", "mean"),
        AP_표준편차=("AP", "std"),
        평균_AUC=("AUC", "mean"),
        **{"평균_상위10%_정답포착률": ("상위10%_정답포착률", "mean")},
    )
    C.OUT_DIR = str(C.EDA_OUT_DIR)
    C.save(results.round(6), "1_생활인구_격자선별_폴드별.csv")
    C.save(summary.round(6), "1_생활인구_격자선별_요약.csv")
    print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
