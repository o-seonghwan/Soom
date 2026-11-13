"""
[문해솔 1] B2C · 비흡연자 — 간접흡연 위험 지도
해결방법: 보행 지점 특성에 분류 모델 7개를 적용하고 공간 블록 시험셋으로 비교
정답 데이터: 강남구 담배꽁초 적발 장소 좌표에서 21m 이내인 보행 지점 = 1

하는 일
 1) 별도 전처리에서 만든 보행 지점 CSV 불러오기
 2) 분류 모델 7개와 기준 2개(생활인구 지수, 같은비중 지수)를
    1km 블록을 8:2로 한 번 분할해 비교. 시험 지점에서 정답 반경의 두 배 이내인 학습 지점은 제외
 3) 공간 5-Fold 튜닝에서 선정한 XGBoost(깊이 3)로 모든 지점에 위험 순위(0~100) 매기기 + 시간대별 격자 위험
 4) (선택) 다른 구 검증: 강남에서 배운 모델로 마포구를 예측해 마포구 상습 투기지역과 맞춰 봄

실행:  python 1_B2C_비흡연자_간접흡연위험지도.py
입력: 0_머신러닝_전처리.py가 저장한 결과/전처리기반/1_학습용_지점_21m.csv
결과(결과/전처리기반 폴더):
  1_모델성능.csv, 1_특성중요도.csv, 1_위험지도_지점.csv, 1_위험지도_격자시간대.csv, (1_다른구검증.csv)
정답 0은 좌표가 확인된 적발 장소의 21m 밖 지점이다. 적발 자료는 단속 위치와 강도에 영향을 받는다.
위험확률 열은 지도에 쓰는 모델 점수이며 현장에서 측정한 간접흡연 확률과는 다르다.
"""
import joblib
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
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


def evaluate_classifier(name, y_test, pred, proba):
    result = {
        "방법": name, **evaluate(y_test, proba),
        "정확도": accuracy_score(y_test, pred), "F1": f1_score(y_test, pred, zero_division=0),
    }
    print("시험셋 예측 예시", pred[:10])
    print("시험셋 양성 확률 예시", proba[:5].round(3))
    print("정확도", round(result["정확도"], 4))
    print("F1", round(result["F1"], 4))
    print("시험셋 AP", round(result["AP"], 4))
    print("시험셋 AUC", round(result["AUC"], 4))
    return result


def main():
    try:
        from xgboost import XGBClassifier
        from lightgbm import LGBMClassifier
    except ImportError as exc:
        raise SystemExit("현재 Python 환경에서 python -m pip install xgboost lightgbm을 실행하세요.") from exc

    # 전처리에서 만든 보행 지점별 CSV 한 장을 불러온다.
    print("<학습용 CSV 불러오기>")
    print("######################################################################")
    path = C.TRAINING_DATA_PATH
    if not path.is_file() or not C.TRAINING_HOURLY_PATH.is_file():
        raise SystemExit("먼저 같은 폴더의 0_머신러닝_전처리.py를 실행하세요.")
    data = pd.read_csv(path, encoding="utf-8-sig", float_precision="round_trip")
    if not set(C.LABEL_DETAIL_COLUMNS).issubset(data.columns):
        raise ValueError("21m 정답과 거리 등급을 만들려면 0번 전처리를 다시 실행하세요.")
    hourly = pd.read_csv(C.TRAINING_HOURLY_PATH, index_col=0)
    C.OUT_DIR = str(path.parent)

    # 좌표·ID·블록은 분할 및 지도용이다. 7개 모델에는 동일한 18개 특성을 넣는다.
    FE = C.model_features(data)
    if len(FE) != len(C.FEATURES):
        raise ValueError("학습용 CSV의 특성 열이 부족합니다. 0번 전처리를 다시 실행하세요.")
    X = data[FE]
    y = data["정답"]
    print(f"분석 지점 {len(data):,}개 | 특성 {len(FE)}개")
    print("######################################################################", end)

    # 학습셋·시험셋 만들기
    print("<train_test_split으로 1km 공간 블록 나누기>")
    print("######################################################################")
    blocks = data["블록"].drop_duplicates().to_numpy()
    if len(blocks) < 2:
        raise ValueError("학습과 시험에 서로 다른 공간 블록이 필요합니다.")
    train_blocks, test_blocks = train_test_split(blocks, test_size=0.2, random_state=SEED)
    train_idx = data.index[data["블록"].isin(train_blocks)]
    test_idx = data.index[data["블록"].isin(test_blocks)]

    # 하나의 적발 장소를 공유한 지점이 양쪽에 들어가지 않도록 정답 반경의 두 배를 비운다.
    xy = C.xy_m(data["위도"], data["경도"])
    distance, _ = cKDTree(xy[test_idx]).query(xy[train_idx])
    keep_train = distance > 2 * C.LABEL_R
    excluded = int((~keep_train).sum())
    train_idx = train_idx[keep_train]

    X_train, X_test = X.loc[train_idx], X.loc[test_idx]
    y_train, y_test = y.loc[train_idx], y.loc[test_idx]
    if set(y_train) != {0, 1} or set(y_test) != {0, 1}:
        raise ValueError("학습셋·시험셋에 정답 0과 1이 모두 필요합니다. 분할과 정답을 확인하세요.")
    print(f"학습 블록 {len(train_blocks)}개 | 시험 블록 {len(test_blocks)}개")
    print(f"학습 {len(X_train):,}행 | 시험 {len(X_test):,}행 | 경계 제외 {excluded:,}행")
    print(f"학습 양성 {y_train.mean():.1%} | 시험 양성 {y_test.mean():.1%}")
    print("######################################################################", end)

    classifiers = {}
    test_probabilities = {}
    rows = []

    ### 1. 로지스틱 회귀 (분류) ###
    print("<로지스틱 회귀 학습과 예측>")
    print("######################################################################")
    name = "로지스틱회귀"
    classifier = LogisticRegression(C=0.3, class_weight="balanced", max_iter=3000)
    model = C.prepare_classifier(classifier, scale=True)
    classifiers[name] = model
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    test_probabilities[name] = proba
    rows.append(evaluate_classifier(name, y_test, pred, proba))
    print("######################################################################", end)

    ### 2. KNN (분류) ###
    print("<KNN 학습과 예측>")
    print("######################################################################")
    name = "KNN"
    n_neighbors = min(50, len(X_train))
    classifier = KNeighborsClassifier(n_neighbors=n_neighbors, weights="distance", n_jobs=4)
    model = C.prepare_classifier(classifier, scale=True)
    classifiers[name] = model
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    test_probabilities[name] = proba
    rows.append(evaluate_classifier(name, y_test, pred, proba))
    print("######################################################################", end)

    ### 3. 나이브 베이즈 (분류) ###
    print("<나이브 베이즈 학습과 예측>")
    print("######################################################################")
    name = "나이브베이즈"
    classifier = GaussianNB()   # 거리와 비율처럼 연속적인 수치형 특성을 사용
    model = C.prepare_classifier(classifier)
    classifiers[name] = model
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    test_probabilities[name] = proba
    rows.append(evaluate_classifier(name, y_test, pred, proba))
    print("######################################################################", end)

    ### 4. 결정 트리 (분류) ###
    print("<결정 트리 학습과 예측>")
    print("######################################################################")
    name = "결정트리"
    classifier = DecisionTreeClassifier(
        max_depth=8, min_samples_leaf=20, class_weight="balanced", random_state=SEED,
    )
    model = C.prepare_classifier(classifier)
    classifiers[name] = model
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    test_probabilities[name] = proba
    rows.append(evaluate_classifier(name, y_test, pred, proba))
    print("######################################################################", end)

    ### 5. 랜덤 포레스트 (분류) ###
    print("<랜덤 포레스트 학습과 예측>")
    print("######################################################################")
    name = "랜덤포레스트"
    classifier = RandomForestClassifier(
        n_estimators=400, min_samples_leaf=5, max_features=0.5,
        class_weight="balanced_subsample", n_jobs=4, random_state=SEED,
    )
    model = C.prepare_classifier(classifier)
    classifiers[name] = model
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    test_probabilities[name] = proba
    rows.append(evaluate_classifier(name, y_test, pred, proba))
    print("######################################################################", end)

    ### 6. XGBoost (분류) ###
    print("<XGBoost 학습과 예측>")
    print("######################################################################")
    name = "XGBoost"
    classifier = XGBClassifier(
        n_estimators=400, learning_rate=0.05, max_depth=3, subsample=0.8,
        colsample_bytree=0.8, n_jobs=4, random_state=SEED, verbosity=0,
    )
    model = C.prepare_classifier(classifier)
    classifiers[name] = model
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    test_probabilities[name] = proba
    rows.append(evaluate_classifier(name, y_test, pred, proba))
    print("######################################################################", end)

    ### 7. LightGBM (분류) ###
    print("<LightGBM 학습과 예측>")
    print("######################################################################")
    name = "LightGBM"
    classifier = LGBMClassifier(
        n_estimators=400, learning_rate=0.05, num_leaves=31, subsample=0.8,
        subsample_freq=1, colsample_bytree=0.8, n_jobs=4, random_state=SEED, verbose=-1,
    )
    model = C.prepare_classifier(classifier)
    classifiers[name] = model
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    test_probabilities[name] = proba
    rows.append(evaluate_classifier(name, y_test, pred, proba))
    print("######################################################################", end)

    print("<성능 비교와 최종 모델 선택>")
    print("######################################################################")
    ranked = pd.DataFrame(rows).sort_values(["AP", "AUC"], ascending=False)
    best = "XGBoost"  # 공간 5-Fold 튜닝에서 선정한 최종 모델
    for name, scores in baselines(data.loc[test_idx]).items():
        rows.append({"방법": name, **evaluate(y_test, scores)})
    zero_pred = np.zeros_like(y_test)
    rows.append({
        "방법": "기준: 전부 0 예측",
        "AUC": roc_auc_score(y_test, zero_pred),
        "AP": average_precision_score(y_test, zero_pred),
        # 점수가 모두 같아 상위 10% 순위를 정할 수 없다.
        "상위10%_정답포착률": np.nan,
        "정확도": accuracy_score(y_test, zero_pred),
        "F1": f1_score(y_test, zero_pred, zero_division=0),
    })
    perf = pd.DataFrame(rows).sort_values(["AP", "AUC"], ascending=False)
    perf["AP_무작위기준"] = y_test.mean()
    C.save(perf.round(6), "1_모델성능.csv")
    print(perf.round(4).to_string(index=False))
    C.log(f"단일 시험셋 AP 1위: {ranked.iloc[0]['방법']}")
    C.log(f"공간 5-Fold 튜닝으로 선정한 최종 모델: {best} (최대 깊이 3)")
    print("######################################################################", end)

    print("\n<전체 데이터 학습과 위험지도 저장>")
    print("######################################################################")
    rf = clone(classifiers["랜덤포레스트"]).fit(X, y)
    lg = clone(classifiers["로지스틱회귀"]).fit(X, y)
    imp = pd.DataFrame({"특성": FE, "뜻": [C.FEATURES[c] for c in FE],
                        "RF_중요도": rf[-1].feature_importances_.round(4),
                        "로지스틱_계수(표준화)": lg[-1].coef_[0].round(3)}).sort_values("RF_중요도", ascending=False)
    C.save(imp, "1_특성중요도.csv")
    print("\n특성 중요도 상위 8\n" + imp.head(8).to_string(index=False))

    # ── 위험점수: 최종 모델을 전체로 학습해 모든 분석 지점에 점수 ──
    fitted = {"랜덤포레스트": rf, "로지스틱회귀": lg}
    final = fitted[best] if best in fitted else clone(classifiers[best]).fit(X, y)
    p = final.predict_proba(X)[:, 1]
    test_predictions = np.full(len(data), np.nan)
    test_predictions[test_idx] = test_probabilities[best]
    C.save_risk_maps(data, hourly, FE, p, test_predictions)
    joblib.dump({"모델명": best, "모델": final, "특성": FE}, C.out_path("1_강남_최종모델.joblib"))
    print("######################################################################", end)

    if C.VALIDATE_OTHER_GU:
        validate_other(final, FE)


def validate_other(model, features):
    """전처리에서 저장한 마포 지점에 전체 강남구로 재학습한 모델을 적용한다."""
    hot_path = C.EDA_OUT_DIR / "1_마포_상습지역_좌표.csv"
    sites_path = C.EDA_OUT_DIR / "1_마포_검증지점.csv"
    if not hot_path.is_file() or not sites_path.is_file():
        C.log("마포 검증 CSV를 찾지 못해 건너뜁니다. 0번 전처리 결과를 확인하세요.")
        return
    hot = pd.read_csv(hot_path)
    d = pd.read_csv(sites_path)
    scores = model.predict_proba(d[features])[:, 1]
    d["위험점수"] = (pd.Series(scores).rank(pct=True) * 100).values
    dist, idx = cKDTree(C.xy_m(d["위도"], d["경도"])).query(C.xy_m(hot["위도"], hot["경도"]))
    v = pd.DataFrame({"도로명주소": hot["도로명주소"].values, "세부위치": hot.get("세부위치", pd.Series([""] * len(hot))).values,
                      "가장가까운지점_거리m": dist.round(1), "가장가까운지점_위험점수": d["위험점수"].values[idx].round(1)})
    v.loc[v["가장가까운지점_거리m"] > C.LABEL_R, "가장가까운지점_위험점수"] = np.nan
    C.save(v, "1_다른구검증.csv")
    s = v["가장가까운지점_위험점수"].dropna()
    C.log(f"[마포구 검증] 상습 투기지역 {len(s)}곳의 위험점수 중앙값 {s.median():.1f}점 (무작위면 약 50점) | "
          f"상위 10%(90점 이상)에 든 곳 {int((s >= 90).sum())}/{len(s)} (무작위면 약 10%)")


if __name__ == "__main__":
    main()
