"""
[문해솔 1] B2C · 비흡연자 — 간접흡연 위험 지도
해결방법: 보행 지점 특성에 분류 모델 7개를 적용하고 공간 블록 교차검증으로 비교
정답 데이터: 강남구 쓰레기무단투기적발내역 중 담배꽁초 적발 장소 (VWorld로 좌표) → 장소 50m 안 지점 = 1

하는 일
 1) 별도 전처리에서 만든 학습셋·시험셋 불러오기
 2) 분류 모델 7개와 기준 2개(생활인구 지수, 같은비중 지수)를
    1km 블록 단위 교차검증으로 비교. 시험 지점에서 100m 이내인 학습 지점은 제외
 3) 분할별 평균 AP가 가장 높은 모델로 모든 지점에 위험 순위(0~100) 매기기 + 시간대별 격자 위험
 4) (선택) 다른 구 검증: 강남에서 배운 모델로 마포구를 예측해 마포구 상습 투기지역과 맞춰 봄

실행:  python 1_B2C_비흡연자_간접흡연위험지도.py
입력: 0_머신러닝_전처리.py가 저장한 결과/전처리기반/1_학습데이터.joblib
결과(결과/전처리기반 폴더):
  1_모델성능.csv, 1_특성중요도.csv, 1_위험지도_지점.csv, 1_위험지도_격자시간대.csv, (1_다른구검증.csv)
정답 0은 좌표가 확인된 적발 장소의 50m 밖 지점이다. 적발 자료는 단속 위치와 강도에 영향을 받는다.
위험확률 열은 지도에 쓰는 모델 점수이며 현장에서 측정한 간접흡연 확률과는 다르다.
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier
import 공통 as C

SEED = 100
end = "\n"


def baselines(df):
    rk = lambda c, s=1: (s * df[c]).rank(pct=True).values
    return {"기준: 생활인구 지수": rk("생활인구_15_19"),
            "기준: 같은비중 지수": (rk("생활인구_15_19") + rk("길_중심성_log") + rk("상가_50m")
                              + rk("정류소_거리m", -1) + rk("지하철출입구_거리m", -1)) / 5}


def evaluate(y, s):
    return {"AUC": roc_auc_score(y, s), "AP": average_precision_score(y, s), "상위10%_정답포착률": C.top_capture(y, s)}


def evaluate_classifier(name, y, pred, proba, test_indices):
    fold_ap = [average_precision_score(y[idx], proba[idx]) for idx in test_indices]
    result = {
        "방법": name, "평균_AP": np.mean(fold_ap), "AP_표준편차": np.std(fold_ap),
        **evaluate(y, proba), "정확도": accuracy_score(y, pred), "F1": f1_score(y, pred, zero_division=0),
    }
    print("시험셋 예측 예시", pred[:10])
    print("시험셋 양성 확률 예시", proba[:5].round(3))
    print("정확도", round(result["정확도"], 4))
    print("F1", round(result["F1"], 4))
    print("분할별 평균 AP", round(result["평균_AP"], 4))
    print("전체 시험 예측 AUC", round(result["AUC"], 4))
    return result


def main():
    try:
        from xgboost import XGBClassifier
        from lightgbm import LGBMClassifier
    except ImportError as exc:
        raise SystemExit("현재 Python 환경에서 python -m pip install xgboost lightgbm을 실행하세요.") from exc

    # 별도 전처리 파일에서 준비한 학습셋과 시험셋 불러오기
    print("<전처리된 학습 데이터 불러오기>")
    print("######################################################################")
    path = C.TRAINING_DATA_PATH
    if not path.is_file():
        raise SystemExit("저장소 루트에서 먼저 python notebooks/02_preprocessing/0_머신러닝_전처리.py를 실행하세요.")
    prepared = joblib.load(path)
    C.OUT_DIR = str(path.parent)
    df, hourly = prepared["sites"], prepared["hourly"]
    FE, y = prepared["features"], prepared["y"]
    folds = prepared["folds"]
    test_indices = [fold["test_idx"] for fold in folds]
    X_full = prepared["X_full"]
    X_full_scaled = prepared["X_full_scaled"]
    print(f"분석 지점 {len(y):,}개 | 특성 {len(FE)}개 | 공간 분할 {len(folds)}개")
    print("######################################################################", end)

    classifiers = {}
    oof = {}
    rows = []

    ### 1. 로지스틱 회귀 (분류) ###
    print("<로지스틱 회귀 학습과 예측>")
    print("######################################################################")
    name = "로지스틱회귀"
    classifier = LogisticRegression(C=0.3, class_weight="balanced", max_iter=3000)
    classifiers[name] = classifier
    pred = np.empty(len(y), dtype=int)
    proba = np.empty(len(y))
    for fold in folds:
        X_train, X_test = fold["X_train_scaled"], fold["X_test_scaled"]
        y_train = fold["y_train"]
        test = fold["test_idx"]
        model = clone(classifiers[name])
        model.fit(X_train, y_train)
        pred[test] = model.predict(X_test)
        proba[test] = model.predict_proba(X_test)[:, 1]
    oof[name] = proba
    rows.append(evaluate_classifier(name, y, pred, proba, test_indices))
    print("######################################################################", end)

    ### 2. KNN (분류) ###
    print("<KNN 학습과 예측>")
    print("######################################################################")
    name = "KNN"
    n_neighbors = min(50, min(len(fold["y_train"]) for fold in folds))
    classifier = KNeighborsClassifier(n_neighbors=n_neighbors, weights="distance", n_jobs=4)
    classifiers[name] = classifier
    pred = np.empty(len(y), dtype=int)
    proba = np.empty(len(y))
    for fold in folds:
        X_train, X_test = fold["X_train_scaled"], fold["X_test_scaled"]
        y_train = fold["y_train"]
        test = fold["test_idx"]
        model = clone(classifiers[name])
        model.fit(X_train, y_train)
        pred[test] = model.predict(X_test)
        proba[test] = model.predict_proba(X_test)[:, 1]
    oof[name] = proba
    rows.append(evaluate_classifier(name, y, pred, proba, test_indices))
    print("######################################################################", end)

    ### 3. 나이브 베이즈 (분류) ###
    print("<나이브 베이즈 학습과 예측>")
    print("######################################################################")
    name = "나이브베이즈"
    classifier = GaussianNB()   # 거리와 비율처럼 연속적인 수치형 특성을 사용
    classifiers[name] = classifier
    pred = np.empty(len(y), dtype=int)
    proba = np.empty(len(y))
    for fold in folds:
        X_train, X_test = fold["X_train"], fold["X_test"]
        y_train = fold["y_train"]
        test = fold["test_idx"]
        model = clone(classifiers[name])
        model.fit(X_train, y_train)
        pred[test] = model.predict(X_test)
        proba[test] = model.predict_proba(X_test)[:, 1]
    oof[name] = proba
    rows.append(evaluate_classifier(name, y, pred, proba, test_indices))
    print("######################################################################", end)

    ### 4. 결정 트리 (분류) ###
    print("<결정 트리 학습과 예측>")
    print("######################################################################")
    name = "결정트리"
    classifier = DecisionTreeClassifier(
        max_depth=8, min_samples_leaf=20, class_weight="balanced", random_state=SEED,
    )
    classifiers[name] = classifier
    pred = np.empty(len(y), dtype=int)
    proba = np.empty(len(y))
    for fold in folds:
        X_train, X_test = fold["X_train"], fold["X_test"]
        y_train = fold["y_train"]
        test = fold["test_idx"]
        model = clone(classifiers[name])
        model.fit(X_train, y_train)
        pred[test] = model.predict(X_test)
        proba[test] = model.predict_proba(X_test)[:, 1]
    oof[name] = proba
    rows.append(evaluate_classifier(name, y, pred, proba, test_indices))
    print("######################################################################", end)

    ### 5. 랜덤 포레스트 (분류) ###
    print("<랜덤 포레스트 학습과 예측>")
    print("######################################################################")
    name = "랜덤포레스트"
    classifier = RandomForestClassifier(
        n_estimators=400, min_samples_leaf=5, max_features=0.5,
        class_weight="balanced_subsample", n_jobs=4, random_state=SEED,
    )
    classifiers[name] = classifier
    pred = np.empty(len(y), dtype=int)
    proba = np.empty(len(y))
    for fold in folds:
        X_train, X_test = fold["X_train"], fold["X_test"]
        y_train = fold["y_train"]
        test = fold["test_idx"]
        model = clone(classifiers[name])
        model.fit(X_train, y_train)
        pred[test] = model.predict(X_test)
        proba[test] = model.predict_proba(X_test)[:, 1]
    oof[name] = proba
    rows.append(evaluate_classifier(name, y, pred, proba, test_indices))
    print("######################################################################", end)

    ### 6. XGBoost (분류) ###
    print("<XGBoost 학습과 예측>")
    print("######################################################################")
    name = "XGBoost"
    classifier = XGBClassifier(
        n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8,
        colsample_bytree=0.8, n_jobs=4, random_state=SEED, verbosity=0,
    )
    classifiers[name] = classifier
    pred = np.empty(len(y), dtype=int)
    proba = np.empty(len(y))
    for fold in folds:
        X_train, X_test = fold["X_train"], fold["X_test"]
        y_train = fold["y_train"]
        test = fold["test_idx"]
        model = clone(classifiers[name])
        model.fit(X_train, y_train)
        pred[test] = model.predict(X_test)
        proba[test] = model.predict_proba(X_test)[:, 1]
    oof[name] = proba
    rows.append(evaluate_classifier(name, y, pred, proba, test_indices))
    print("######################################################################", end)

    ### 7. LightGBM (분류) ###
    print("<LightGBM 학습과 예측>")
    print("######################################################################")
    name = "LightGBM"
    classifier = LGBMClassifier(
        n_estimators=400, learning_rate=0.05, num_leaves=31, subsample=0.8,
        subsample_freq=1, colsample_bytree=0.8, n_jobs=4, random_state=SEED, verbose=-1,
    )
    classifiers[name] = classifier
    pred = np.empty(len(y), dtype=int)
    proba = np.empty(len(y))
    for fold in folds:
        X_train, X_test = fold["X_train"], fold["X_test"]
        y_train = fold["y_train"]
        test = fold["test_idx"]
        model = clone(classifiers[name])
        model.fit(X_train, y_train)
        pred[test] = model.predict(X_test)
        proba[test] = model.predict_proba(X_test)[:, 1]
    oof[name] = proba
    rows.append(evaluate_classifier(name, y, pred, proba, test_indices))
    print("######################################################################", end)

    print("<성능 비교와 최종 모델 선택>")
    print("######################################################################")
    ranked = pd.DataFrame(rows).sort_values(["평균_AP", "AUC"], ascending=False)
    best = ranked["방법"].iloc[0]
    for name, scores in baselines(df).items():
        fold_ap = [average_precision_score(y[idx], scores[idx]) for idx in test_indices]
        rows.append({"방법": name, "평균_AP": np.mean(fold_ap), "AP_표준편차": np.std(fold_ap), **evaluate(y, scores)})
    perf = pd.DataFrame(rows).sort_values(["평균_AP", "AUC"], ascending=False)
    perf["AP_무작위기준"] = y.mean()
    C.save(perf.round(6), "1_모델성능.csv")
    print(perf.round(4).to_string(index=False))
    C.log(f"가장 좋은 모델(AP 기준): {best}")
    print("######################################################################", end)

    print("\n<전체 데이터 학습과 위험지도 저장>")
    print("######################################################################")
    rf = clone(classifiers["랜덤포레스트"]).fit(X_full, y)
    lg = clone(classifiers["로지스틱회귀"]).fit(X_full_scaled, y)
    imp = pd.DataFrame({"특성": FE, "뜻": [C.FEATURES[c] for c in FE],
                        "RF_중요도": rf.feature_importances_.round(4),
                        "로지스틱_계수(표준화)": lg.coef_[0].round(3)}).sort_values("RF_중요도", ascending=False)
    C.save(imp, "1_특성중요도.csv")
    print("\n특성 중요도 상위 8\n" + imp.head(8).to_string(index=False))

    # ── 위험점수: 최종 모델을 전체로 학습해 모든 분석 지점에 점수 ──
    fitted = {"랜덤포레스트": rf, "로지스틱회귀": lg}
    use_scaled = best in {"로지스틱회귀", "KNN"}
    X_final = X_full_scaled if use_scaled else X_full
    final = fitted[best] if best in fitted else clone(classifiers[best]).fit(X_final, y)
    p = final.predict_proba(X_final)[:, 1]
    C.save_risk_maps(df, hourly, FE, p, oof[best])
    print("######################################################################", end)

    if prepared["other"] is not None:
        hot, other_sites, other_X, other_X_scaled = prepared["other"]
        validate_other(final, hot, other_sites, other_X_scaled if use_scaled else other_X)


def validate_other(model, hot, d, X):
    """전처리 파일에서 준비한 마포 지점에 강남 모델을 적용한다."""
    d["위험점수"] = (pd.Series(model.predict_proba(X)[:, 1]).rank(pct=True) * 100).values
    from scipy.spatial import cKDTree
    dist, idx = cKDTree(C.xy_m(d["위도"], d["경도"])).query(C.xy_m(hot["위도"], hot["경도"]))
    v = pd.DataFrame({"도로명주소": hot["도로명주소"].values, "세부위치": hot.get("세부위치", pd.Series([""] * len(hot))).values,
                      "가장가까운지점_거리m": dist.round(1), "가장가까운지점_위험점수": d["위험점수"].values[idx].round(1)})
    v.loc[v["가장가까운지점_거리m"] > C.LABEL_R, "가장가까운지점_위험점수"] = np.nan   # 50m 안에 분석 지점이 없으면 뺌
    C.save(v, "1_다른구검증.csv")
    s = v["가장가까운지점_위험점수"].dropna()
    C.log(f"[마포구 검증] 상습 투기지역 {len(s)}곳의 위험점수 중앙값 {s.median():.1f}점 (무작위면 약 50점) | "
          f"상위 10%(90점 이상)에 든 곳 {int((s >= 90).sum())}/{len(s)} (무작위면 약 10%)")


if __name__ == "__main__":
    main()
