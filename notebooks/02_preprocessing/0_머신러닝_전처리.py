"""
1번 간접흡연 위험지도 학습용 데이터 전처리.

실행: python 0_머신러닝_전처리.py
결과: 결과/전처리기반/1_학습데이터.joblib
"""
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

import joblib
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "03_modeling"))
import 공통 as C

VALIDATE_OTHER_GU = None   # 마포 검증 데이터를 준비하려면 ("마포구", "11440")로 변경
N_FOLDS = 5
SEED = 100
end = "\n"


def prepare_inputs(X_train, X_test=None):
    # 결측값 대체와 표준화 모두 학습셋에서만 기준을 계산한다.
    imputer = SimpleImputer(strategy="median", keep_empty_features=True).set_output(transform="pandas")
    X_train_plain = imputer.fit_transform(X_train)

    scaler = StandardScaler().set_output(transform="pandas")
    X_train_scaled = scaler.fit_transform(X_train_plain)
    if X_test is None:
        return X_train_plain, X_train_scaled, imputer, scaler

    X_test_plain = imputer.transform(X_test)
    X_test_scaled = scaler.transform(X_test_plain)
    return X_train_plain, X_test_plain, X_train_scaled, X_test_scaled


def spatial_folds(df, X, y):
    from scipy.spatial import cKDTree

    n_splits = min(N_FOLDS, df["블록"].nunique())
    if n_splits < 2 or np.unique(y).size != 2:
        raise ValueError("공간 교차검증에는 두 개 이상의 블록과 0·1 정답이 모두 필요합니다.")

    xy = C.xy_m(df["위도"], df["경도"])
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    folds = []
    for train, test in splitter.split(X, y, df["블록"]):
        # 하나의 적발 장소가 학습·시험 지점에 동시에 50m 라벨을 붙이지 않도록 분리
        distance, _ = cKDTree(xy[test]).query(xy[train])
        train = train[distance > 2 * C.LABEL_R]
        if np.unique(y[train]).size != 2 or np.unique(y[test]).size != 2:
            raise ValueError("학습·시험에 0과 1이 모두 들어가도록 N_FOLDS를 줄이거나 정답 좌표를 확인하세요.")
        folds.append((train, test))
    return folds


def prepare_other(X, imputer, scaler, gu, code):
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
    # 강남 전체 학습 데이터로 계산한 전처리 기준을 마포 데이터에 적용한다.
    other_X = d[X.columns].fillna(X.median())
    other_plain = imputer.transform(other_X)
    other_scaled = scaler.transform(other_plain)
    return hot, d, other_plain, other_scaled


def main():
    # 데이터 불러와서 변수에 저장하고 정답 붙이기
    print("<데이터 불러오기와 정답 붙이기>")
    print("######################################################################")
    C.use_preprocessed_data()
    nodes, hourly = C.build_features()
    df = nodes[nodes["분석대상"] == 1].reset_index(drop=True)
    places = C.butt_places().dropna(subset=["위도", "경도"])
    df["정답"], df["적발건수_50m"] = C.label_nodes(df, places)
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

    # 학습셋·시험셋 만들기
    print("<학습셋·시험셋 만들기>")
    print("######################################################################")
    X = data.drop("정답", axis=1)
    y = data["정답"].to_numpy()
    folds = spatial_folds(df, X, y)
    for i, (train, test) in enumerate(folds, start=1):
        print(f"{i}번째 분할 | 학습 {len(train):,}개 | 시험 {len(test):,}개 | 시험 양성 비율 {y[test].mean():.1%}")
    print("######################################################################", end)

    print("<분할별 결측값 처리와 표준화>")
    print("######################################################################")
    prepared_folds = []
    for train, test in folds:
        X_train, X_test = X.iloc[train], X.iloc[test]
        X_train_plain, X_test_plain, X_train_scaled, X_test_scaled = prepare_inputs(X_train, X_test)
        prepared_folds.append({
            "test_idx": test,
            "y_train": y[train],
            "X_train": X_train_plain,
            "X_test": X_test_plain,
            "X_train_scaled": X_train_scaled,
            "X_test_scaled": X_test_scaled,
        })

    # 전체 재학습용 데이터는 교차검증용 데이터와 별도로 준비한다.
    X_full, X_full_scaled, imputer, scaler = prepare_inputs(X)
    other = prepare_other(X, imputer, scaler, *VALIDATE_OTHER_GU) if VALIDATE_OTHER_GU else None
    prepared = {
        "sites": df,
        "hourly": hourly,
        "features": FE,
        "y": y,
        "folds": prepared_folds,
        "X_full": X_full,
        "X_full_scaled": X_full_scaled,
        "other": other,
    }
    # 저장 도중 중단되면 직전 학습데이터를 그대로 사용할 수 있도록 마지막에 교체한다.
    path = C.TRAINING_DATA_PATH
    with NamedTemporaryFile(dir=path.parent, suffix=".joblib", delete=False) as handle:
        temporary_path = Path(handle.name)
    try:
        joblib.dump(prepared, temporary_path, compress=3)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    print(f"학습데이터 저장 완료 {path}")
    print("######################################################################", end)


if __name__ == "__main__":
    main()
