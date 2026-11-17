"""강남구 1km 공간 블록 5-Fold 분할과 경계 제외 지점 저장."""
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.model_selection import StratifiedGroupKFold

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C


def main():
    data = pd.read_csv(C.TRAINING_DATA_PATH, encoding="utf-8-sig", float_precision="round_trip")
    y = data["정답"]
    blocks = data["블록"]
    xy = C.xy_m(data["위도"], data["경도"])
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=100)
    roles = data[["노드 ID", "블록", "정답"]].copy()
    summary = []
    for fold, (train, test) in enumerate(splitter.split(xy, y, groups=blocks), 1):
        distance, _ = cKDTree(xy[test]).query(xy[train])
        excluded = train[distance <= 2 * C.LABEL_R]
        train = train[distance > 2 * C.LABEL_R]
        if set(y.iloc[train]) != {0, 1} or set(y.iloc[test]) != {0, 1}:
            raise ValueError(f"{fold}번 폴드의 학습·검증 데이터에 정답 0과 1이 필요합니다.")

        role = np.full(len(data), "학습", dtype=object)
        role[test] = "검증"
        role[excluded] = "경계제외"
        roles[f"Fold_{fold}"] = role
        summary.append({
            "Fold": fold, "학습_블록": blocks.iloc[train].nunique(),
            "검증_블록": blocks.iloc[test].nunique(), "학습_노드": len(train),
            "검증_노드": len(test), "경계제외_노드": len(excluded),
            "학습_정답1": int(y.iloc[train].sum()), "검증_정답1": int(y.iloc[test].sum()),
        })

    C.OUT_DIR = str(C.EDA_OUT_DIR)
    C.save(roles, "1_강남_공간5Fold_분할.csv")
    report = pd.DataFrame(summary)
    C.save(report, "1_강남_공간5Fold_요약.csv")
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
