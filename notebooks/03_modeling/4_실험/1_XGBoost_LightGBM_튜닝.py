"""강남구 공간 5-Fold로 XGBoost와 LightGBM의 후보 설정을 비교한다."""
import argparse
import json
from pathlib import Path

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

DEPTHS = tuple(range(1, 9))


def evaluate_folds(name, classifier, params, label, X, y, roles, folds):
    rows = []
    for fold in folds:
        train = roles[fold].eq("학습")
        test = roles[fold].eq("검증")
        if set(y[train]) != {0, 1} or set(y[test]) != {0, 1}:
            raise ValueError(f"{fold}의 학습·검증 데이터에 정답 0과 1이 모두 필요합니다.")
        model = C.prepare_classifier(classifier(**params))
        model.fit(X.loc[train], y[train])
        scores = model.predict_proba(X.loc[test])[:, 1]
        rows.append({
            "모델": name,
            "설정": label,
            "파라미터": json.dumps(params, sort_keys=True),
            "폴드": fold,
            "AP": average_precision_score(y[test], scores),
            "AUC": roc_auc_score(y[test], scores),
            "상위10%_정답포착률": C.top_capture(y[test], scores),
        })
    return rows


def save_depth_chart(summary, output_dir, font_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    if font_path:
        font_manager.fontManager.addfont(font_path)
        family = font_manager.FontProperties(fname=font_path).get_name()
    else:
        available = {font.name for font in font_manager.fontManager.ttflist}
        family = next((name for name in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans KR",
                                        "AppleGothic", "NanumGothic") if name in available), None)
        if family is None:
            raise RuntimeError("한글 글꼴을 설치하거나 --font로 글꼴 파일을 지정하세요.")
    with plt.rc_context({"font.family": family, "axes.unicode_minus": False}):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True, layout="constrained")
        for ax, (name, group), color in zip(axes, summary.groupby("모델", sort=False),
                                             ("#4f8a35", "#386857")):
            depth = group["max_depth"]
            ap = group["평균_AP"]
            ax.plot(depth, ap, marker="o", linewidth=2.5, markersize=7, color=color)
            for x, value in zip(depth, ap):
                ax.annotate(f"{value:.4f}", (x, value), xytext=(0, 9),
                            textcoords="offset points", ha="center", color=color)
            ax.set(title=name, xlabel="최대 트리 깊이 (max_depth)", xticks=DEPTHS)
            ax.margins(x=.13, y=.25)
            ax.grid(axis="y", alpha=.22)
            ax.spines[["top", "right"]].set_visible(False)
        axes[0].set_ylabel("공간 5-Fold 평균 AP")
        fig.savefig(output_dir / "1_최대깊이별_AP.png", dpi=210)
        plt.close(fig)


def depth_sweep(X, y, roles, folds, output_dir, font_path):
    rows = []
    for name, (classifier, defaults, _) in MODELS.items():
        for depth in DEPTHS:
            params = {**SHARED, **defaults, "max_depth": depth}
            fold_rows = evaluate_folds(name, classifier, params, f"깊이 {depth}", X, y, roles, folds)
            rows.extend({**row, "max_depth": depth} for row in fold_rows)
            print(f"{name} | 깊이 {depth} | 평균 AP {sum(r['AP'] for r in fold_rows) / len(folds):.4f}",
                  flush=True)
    folds_table = pd.DataFrame(rows)
    summary = folds_table.groupby(["모델", "max_depth"], sort=False, as_index=False).agg(
        평균_AP=("AP", "mean"), AP_표준편차=("AP", "std"), 폴드수=("AP", "size")
    )
    C.save(folds_table.round(6), "1_최대깊이별_AP_폴드별.csv")
    C.save(summary.round(6), "1_최대깊이별_AP_요약.csv")
    save_depth_chart(summary, output_dir, font_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=C.EDA_OUT_DIR)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--depth-only", action="store_true")
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or args.input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    C.OUT_DIR = str(output_dir)
    data = pd.read_csv(args.input_dir / C.TRAINING_DATA_PATH.name, float_precision="round_trip")
    split_path = args.input_dir / "1_강남_공간5Fold_분할.csv"
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
    if args.depth_only:
        depth_sweep(X, y, roles, folds, output_dir, args.font)
        return
    rows = []
    for name, (classifier, defaults, candidates) in MODELS.items():
        print(f"<{name} 하이퍼파라미터 튜닝>", flush=True)
        print("######################################################################")
        for index, changes in enumerate([{}, *candidates]):
            label = "기존 설정" if index == 0 else f"후보 {index}"
            params = {**SHARED, **defaults, **changes}
            fold_results = evaluate_folds(name, classifier, params, label, X, y, roles, folds)
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
    C.save(results.round(6), "1_부스팅_튜닝_폴드별.csv")
    C.save(summary.round(6), "1_부스팅_튜닝_요약.csv")
    print(summary.drop(columns="파라미터").round(4).to_string(index=False))
    depth_sweep(X, y, roles, folds, output_dir, args.font)


if __name__ == "__main__":
    main()
