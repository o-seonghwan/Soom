"""흡연 위험지도 개선 후보를 공간 5-Fold에서 비교한다."""
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.metrics import average_precision_score, roc_auc_score

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C


def compare(group, name, X, y, roles, params=None, sample=None, evaluation=None):
    test_X, test_y = (X, y) if evaluation is None else evaluation
    for fold in FOLDS:
        train = np.flatnonzero(roles[fold].eq("학습"))
        test = np.flatnonzero(roles[fold].eq("검증"))
        actual = test_y.iloc[test].to_numpy()
        if np.unique(actual).size != 2 or y.iloc[train].nunique() != 2:
            raise ValueError(f"{group} {name} {fold} 양성 또는 음성 부족")
        rng = np.random.default_rng(100 + int(fold[-1]))
        positive = train[y.iloc[train].to_numpy() == 1]
        zero = train[y.iloc[train].to_numpy() == 0]
        scores = []
        repeats = 5 if sample == "PU" else 1
        for _ in range(repeats):
            indices = train
            if sample is not None:
                ratio = 1 if sample == "PU" else sample
                size = min(len(zero), int(len(positive) * ratio))
                indices = np.sort(np.r_[positive, rng.choice(zero, size=size, replace=False)])
            model = C.prepare_classifier(CLASSIFIER(**{**PARAMS, **(params or {})}))
            model.fit(X.iloc[indices], y.iloc[indices])
            scores.append(model.predict_proba(test_X.iloc[test])[:, 1])
        score = np.mean(scores, axis=0)
        top = np.argsort(-score)[:max(1, int(len(test) * .1))]
        tp = int(actual[top].sum())
        ROWS.append({
            "실험군": group, "방법": name, "폴드": fold,
            "학습수": len(indices), "평가수": len(test), "양성수": int(actual.sum()),
            "AP": average_precision_score(actual, score), "AUC": roc_auc_score(actual, score),
            "상위10%_정밀도": tp / len(top), "상위10%_재현율": tp / actual.sum(),
            "기본_재현율": actual[score > .5].sum() / actual.sum(),
        })
    print(group, name, "완료", flush=True)


def add_facilities(d, X):
    pts = C.to_gdf(d, "경도", "위도")
    stores = C.load_stores(pts.geometry.union_all().convex_hull.buffer(150))
    detail = stores["상권업종소분류명"].fillna("")
    middle = stores["상권업종중분류명"].fillna("")
    result = X.copy()
    for name, pattern in {"PC방": "PC방|피시방|피씨방|컴퓨터 게임방", "노래방": "노래", "카페": "카페|커피"}.items():
        target = stores[detail.str.contains(pattern, case=False) | middle.str.contains(pattern, case=False)]
        print(name, len(target), flush=True)
        if target.empty:
            raise ValueError(f"{name} 시설 분류를 확인하세요.")
        result[f"{name}_50m"] = C.count_within(pts, target, 50)
        result[f"{name}_100m"] = C.count_within(pts, target, 100)
    result["주점_거리m"] = C.nearest_dist(pts, stores[middle.str.contains("주점")])
    result["편의점_거리m"] = C.nearest_dist(pts, stores[detail.str.contains("편의점")])
    return result


def nearby_label(xy, events):
    if events.empty:
        raise ValueError("라벨 생성에 쓸 적발 기록이 없습니다.")
    tree = cKDTree(C.xy_m(events["위도"], events["경도"]))
    return pd.Series((tree.query(xy)[0] <= C.LABEL_R).astype(int))


def history_counts(xy, events, radius):
    grouped = events.groupby(["위도", "경도"]).size().reset_index(name="건수")
    tree = cKDTree(C.xy_m(grouped["위도"], grouped["경도"]))
    return np.array([grouped["건수"].to_numpy()[idx].sum() for idx in tree.query_ball_point(xy, radius)])


def time_bucket(hour):
    return np.select([hour < 12, hour < 17, hour < 21], [0, 1, 2], default=3)


def dated_experiments(d, X, roles):
    C.use_preprocessed_data()
    locations = pd.read_csv(C.EDA_OUT_DIR / "정답_꽁초적발_장소좌표.csv").dropna(subset=["위도", "경도"])
    events = C.load_butt_records().dropna(subset=["일시"]).merge(
        locations[["장소", "위도", "경도"]], on="장소", validate="many_to_one"
    )
    days = np.sort(events["일시"].dt.normalize().unique())
    cutoff = pd.Timestamp(days[int(len(days) * .7)])
    past = events[events["일시"] < cutoff].copy()
    future = events[events["일시"] >= cutoff].copy()
    print("시간 분리", past["일시"].min(), cutoff, future["일시"].max(), len(past), len(future), flush=True)
    xy = C.xy_m(d["위도"], d["경도"])
    y_future = nearby_label(xy, future)
    past_X = X.assign(과거적발_50m=history_counts(xy, past, 50), 과거적발_100m=history_counts(xy, past, 100))
    compare("미래 적발 노드", "기존 특성", X, y_future, roles)
    compare("미래 적발 노드", "과거 적발 50m·100m", past_X, y_future, roles)

    # 평가 기간과 길이가 같은 직전 기간으로 학습 정답을 따로 구성한다.
    end = future["일시"].max().normalize() + pd.Timedelta(days=1)
    middle_start = cutoff - (end - cutoff)
    early = past[past["일시"] < middle_start]
    middle = past[past["일시"] >= middle_start]
    y_middle = nearby_label(xy, middle)
    earlier_X = X.assign(
        과거적발_50m=history_counts(xy, early, 50),
        과거적발_100m=history_counts(xy, early, 100),
    )
    print("순차 평가", middle_start, cutoff, end, len(early), len(middle), len(future), flush=True)
    compare("기간·공간 분리 노드", "기존 특성", X, y_middle, roles, evaluation=(X, y_future))
    compare("기간·공간 분리 노드", "과거 적발 50m·100m", earlier_X, y_middle, roles,
            evaluation=(past_X, y_future))

    for frame in (past, future):
        frame["주말"] = frame["일시"].dt.dayofweek.ge(5)
        frame["시간대"] = time_bucket(frame["일시"].dt.hour)
    # 주중·주말 × 4개 시간대를 각각 독립된 예측 행으로 구성한다.
    hour_groups = ([*range(12)], [*range(12,17)], [*range(17,21)], [*range(21,24)])
    hourly = pd.read_csv(C.TRAINING_HOURLY_PATH, index_col=0)
    chunks, targets, temporal, historical = [], [], [], []
    for weekend in (False, True):
        for bucket, hours in enumerate(hour_groups):
            same = future[future["주말"].eq(weekend) & future["시간대"].eq(bucket)]
            print(f"미래 적발 주말={weekend} 시간대={bucket}: {len(same)}건", flush=True)
            if len(same) < 20:
                continue  # 적발 관측이 부족한 시간대에는 실험 라벨을 만들지 않는다.
            past_same = past[past["주말"].eq(weekend) & past["시간대"].eq(bucket)]
            pop = d["격자ID"].map(hourly[[str(h) for h in hours]].mean(axis=1))
            extra = {"주말": int(weekend), "시간대": bucket, "해당시간_생활인구": pop}
            chunks.append(X)
            targets.append(nearby_label(xy, same))
            temporal.append(X.assign(**extra))
            historical.append(past_X.assign(**extra, 같은시간_과거적발_100m=history_counts(xy, past_same, 100)))
    if not chunks:
        raise ValueError("시간대 실험에 쓸 적발 기록이 부족합니다.")
    tiled_roles = pd.concat([roles] * len(chunks), ignore_index=True)
    yy = pd.concat(targets, ignore_index=True)
    for name, frames in [("기존 특성", chunks), ("시간대·주말·생활인구", temporal), ("시간대·과거 적발 결합", historical)]:
        compare("미래 적발 노드×시간", name, pd.concat(frames, ignore_index=True), yy, tiled_roles)


def aggregated_experiments(d, X, y, roles):
    # 격자에는 구성 노드 평균 특성을 붙이고, 적발 근접 노드가 하나라도 있으면 1로 둔다.
    grid = d["격자ID"]
    grid_x = X.groupby(grid).mean()
    grid_y = y.groupby(grid).max()
    grid_roles = {}
    for fold in FOLDS:
        counts = roles[fold].groupby(grid).agg(lambda g: g.iloc[0] if g.nunique() == 1 else "제외")
        grid_roles[fold] = counts.reindex(grid_x.index)
    compare("250m 격자", "격자 단위 XGBoost", grid_x.reset_index(drop=True), grid_y.reset_index(drop=True),
            pd.DataFrame(grid_roles).reset_index(drop=True))

    # 보행 링크는 두 끝점의 평균 특성을 사용하고, 어느 한 끝점이 양성이면 링크 라벨을 1로 둔다.
    links = pd.read_csv(C.TRAINING_HOURLY_PATH.with_name("보행링크.csv"))
    idx = pd.Series(d.index, index=d["노드 ID"])
    a = links["시작노드 ID"].map(idx)
    b = links["종료노드 ID"].map(idx)
    keep = a.notna() & b.notna()
    a, b = a[keep].to_numpy(int), b[keep].to_numpy(int)
    lx = pd.DataFrame((X.to_numpy()[a] + X.to_numpy()[b]) / 2, columns=X.columns)
    lx["길이_m"] = links.loc[keep, "길이_m"].to_numpy()
    ly = pd.Series(np.maximum(y.to_numpy()[a], y.to_numpy()[b]))
    lr = {}
    for fold in FOLDS:
        left, right = roles[fold].to_numpy()[a], roles[fold].to_numpy()[b]
        lr[fold] = np.where(left == right, left, "제외")
    compare("보행 링크", "링크 단위 XGBoost", lx, ly, pd.DataFrame(lr))


if __name__ == "__main__":
    tuning = runpy.run_path(str(Path(__file__).with_name("1_XGBoost_LightGBM_튜닝.py")))
    CLASSIFIER, defaults, candidates = tuning["MODELS"]["XGBoost"]
    PARAMS = {**tuning["SHARED"], **defaults, **candidates[0]}
    FOLDS = [f"Fold_{i}" for i in range(1, 6)]
    ROWS = []
    d = pd.read_csv(C.TRAINING_DATA_PATH, float_precision="round_trip")
    roles = pd.read_csv(C.EDA_OUT_DIR / "1_강남_공간5Fold_분할.csv")
    keys = ["노드 ID", "블록", "정답"]
    if not d[keys].equals(roles[keys]):
        raise ValueError("학습 CSV와 폴드 분할표가 다릅니다.")
    X, y = d[C.model_features(d)], d["정답"]
    for weight in (1, 2, 3, 6):
        compare("기존 노드", f"양성 가중치 {weight}", X, y, roles, params={"scale_pos_weight": weight})
    for ratio in (3, 6):
        compare("기존 노드", f"정답 0 언더샘플링 {ratio}:1", X, y, roles, sample=ratio)
    compare("기존 노드", "PU 배깅 5개", X, y, roles, sample="PU")
    compare("기존 노드", "시설 특성 8개 추가", add_facilities(d, X), y, roles)
    aggregated_experiments(d, X, y, roles)
    dated_experiments(d, X, roles)
    detail = pd.DataFrame(ROWS)
    summary = detail.groupby(["실험군", "방법"], sort=False, as_index=False).agg({
        "평가수": "sum", "양성수": "sum", "AP": "mean", "AUC": "mean",
        "상위10%_정밀도": "mean", "상위10%_재현율": "mean", "기본_재현율": "mean",
    })
    C.OUT_DIR = str(C.EDA_OUT_DIR)
    C.save(detail.round(6), "1_위험모델_개선실험_폴드별.csv")
    C.save(summary.round(6), "1_위험모델_개선실험_요약.csv")
    print(summary.round(4).to_string(index=False))
