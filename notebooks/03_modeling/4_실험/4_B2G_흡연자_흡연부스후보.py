"""
[문해솔 4] B2G · 흡연자 — 흡연부스(흡연 가능 구역) 설치 후보
해결방법: DBSCAN(비지도학습)으로 꽁초 적발이 몰린 '흡연 집중지'를 찾고,
         주변 보행 지점에 프로젝트의 거리 기준을 적용해 현장 검토 후보를 추림
정답 데이터: 없음(비지도). 입력은 강남구 꽁초 적발 기록(좌표·시각)

규칙
  - 프로젝트 기준은 어린이집 30m, 정류소·지하철 출입구·기타 금연구역 지점 10m에 검토 여유 거리 21m를 더함
  - 집중지 중심에서 직선 150m 이내의 보행 지점 중 가장 가까운 후보
  - 집중지 중심이 어린이집 지점에서 51m 이내이면 단속 우선 검토로 표시
  - 설치 판단에는 실제 시설 경계, 보행 접근성, 현장 여건 확인이 필요

실행: python 4_B2G_흡연자_흡연부스후보.py
입력: 전처리결과의 적발표와 기존 주소별 좌표표, 전처리 기반 보행 지점 및 원본 보호 대상 위치
결과(결과/전처리기반 폴더): 4_흡연집중지_DBSCAN.csv, 4_흡연부스_후보.csv
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.cluster import DBSCAN
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C

EPS_M = 30               # DBSCAN 반경(m). 50m로 하면 강남대로가 반경 480m 한 덩어리로 이어져 30m로 둠
MIN_RECORDS = 30         # 집중지로 볼 최소 적발 건수
BOOTH_SEARCH_M = 150     # 집중지 중심에서 부스 후보를 찾는 반경(m)
BAN_R = {"어린이집": 30, "버스정류소": 10, "지하철출입구": 10, "기타금연구역": 10}   # 2번 코드와 같은 기준
SEPARATOR = "=" * 61
end = "\n"
HOTSPOT_COLUMNS = ["집중지", "적발건수", "장소수", "중심_위도", "중심_경도", "대표장소", "가장많은시간", "반경_m"]
BOOTH_COLUMNS = ["가까운어린이집", "어린이집까지_m", "판단", "부스후보_위도", "부스후보_경도", "집중지에서_m"]


def group_locations(rec):
    # 같은 장소 기록은 좌표가 같으므로 장소별로 묶고 건수를 가중치로 씀
    return rec.groupby(["위도", "경도"]).agg(건수=("장소", "size"), 대표장소=("장소", lambda s: s.value_counts().index[0])).reset_index()


def cluster_locations(locations, rec, eps_m, min_records):
    pl = locations.copy()
    X = C.xy_m(pl["위도"], pl["경도"])
    model = DBSCAN(eps=eps_m, min_samples=min_records)
    model.fit(X, sample_weight=pl["건수"])
    pl["집중지"] = model.labels_
    rec = rec.merge(pl[["위도", "경도", "집중지"]], on=["위도", "경도"])
    rec["시"] = rec["일시"].dt.hour
    rows = []
    for k, g in pl[pl["집중지"] >= 0].groupby("집중지"):
        weights = g["건수"].to_numpy()
        lat = np.average(g["위도"], weights=weights)
        lon = np.average(g["경도"], weights=weights)
        center = C.xy_m([lat], [lon])[0]
        radius = np.linalg.norm(C.xy_m(g["위도"], g["경도"]) - center, axis=1).max()
        peak_hour = rec.loc[rec["집중지"] == k, "시"].mode()
        rows.append({
            "집중지": k, "적발건수": int(weights.sum()), "장소수": len(g),
            "중심_위도": lat, "중심_경도": lon,
            "대표장소": g.loc[g["건수"].idxmax(), "대표장소"],
            "가장많은시간": int(peak_hour.iloc[0]) if not peak_hour.empty else np.nan,
            "반경_m": round(radius, 1),
        })
    H = pd.DataFrame(rows, columns=HOTSPOT_COLUMNS).sort_values("적발건수", ascending=False)
    return pl, H


def prepare_booth_search():
    target_script = Path(__file__).resolve().parents[1] / "2_서비스" / "2_B2C_흡연자_여기서피워도되나요.py"
    spec = importlib.util.spec_from_file_location("smoking_targets", target_script)
    q2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q2)
    T = q2.load_targets().dropna(subset=["위도", "경도"])
    nodes, _ = C.build_features()
    N = nodes[nodes["분석대상"] == 1].dropna(subset=["위도", "경도"]).reset_index(drop=True)
    NP = C.xy_m(N["위도"], N["경도"])
    missing = sorted(set(BAN_R) - set(T["종류"]))
    if missing:
        print("보호 대상 자료 미확인:", ", ".join(missing))
    ok = np.ones(len(N), bool)
    for kind, r in BAN_R.items():
        t = T[T["종류"] == kind]
        if t.empty:
            continue
        d, _ = cKDTree(C.xy_m(t["위도"], t["경도"])).query(NP)
        ok &= d > r + C.SMOKE_REACH_M
    print(f"보호 대상과의 거리 기준을 통과한 지점 {ok.sum():,}/{len(N):,}개")

    care = T[T["종류"] == "어린이집"].reset_index(drop=True)
    ct = cKDTree(C.xy_m(care["위도"], care["경도"]))
    nt = cKDTree(NP[ok])
    Nok = N[ok].reset_index(drop=True)
    return missing, care, ct, nt, Nok


def find_booth_candidates(H, search):
    missing, care, ct, nt, Nok = search
    out = []
    for _, h in H.iterrows():
        c = C.xy_m([h["중심_위도"]], [h["중심_경도"]])[0]
        dcare, icare = ct.query(c)
        d, i = nt.query(c, distance_upper_bound=BOOTH_SEARCH_M)
        rowo = {
            **h.to_dict(), "가까운어린이집": care.loc[icare, "이름"] if np.isfinite(dcare) else None,
            "어린이집까지_m": round(dcare, 1) if np.isfinite(dcare) else np.nan,
            "부스후보_위도": np.nan, "부스후보_경도": np.nan, "집중지에서_m": np.nan,
        }
        if missing:
            rowo["판단"] = "보호 대상 자료 미확인"
        elif dcare <= BAN_R["어린이집"] + C.SMOKE_REACH_M:
            rowo["판단"] = "어린이집 인근 단속 우선 검토"
        elif np.isfinite(d):
            rowo.update(판단="현장 검토 후보", 부스후보_위도=Nok.loc[i, "위도"],
                        부스후보_경도=Nok.loc[i, "경도"], 집중지에서_m=round(d, 1))
        else:
            rowo["판단"] = f"직선 {BOOTH_SEARCH_M}m 이내 검토 후보 없음"
        out.append(rowo)
    B = pd.DataFrame(out, columns=HOTSPOT_COLUMNS + BOOTH_COLUMNS)
    return B


def main():
    print("<꽁초 적발 데이터 불러오기>")
    print(SEPARATOR)
    C.use_preprocessed_data()
    rec = C.butt_records_with_xy().dropna(subset=["위도", "경도"]).copy()
    if rec.empty:
        raise ValueError("군집 분석에 사용할 강남구 꽁초 적발 좌표가 없습니다.")
    print(rec[["위도", "경도", "일시"]].head())
    print(f"좌표 있는 꽁초 적발 기록 {len(rec):,}건")
    print(SEPARATOR, end=end)

    print("\n<DBSCAN으로 꽁초 적발 집중지 찾기>")
    print(SEPARATOR)
    pl, H = cluster_locations(group_locations(rec), rec, EPS_M, MIN_RECORDS)
    noise = pl["집중지"] == -1
    n_clusters = pl.loc[~noise, "집중지"].nunique()
    n_noise = pl.loc[noise, "건수"].sum()
    print(f"반경 {EPS_M}m | 최소 {MIN_RECORDS}건 | 집중지 {n_clusters}곳")
    print(f"집중지 밖 기록 {n_noise:,}건")
    print(SEPARATOR, end=end)

    print("\n<집중지별 적발 건수와 중심 좌표>")
    print(SEPARATOR)
    C.save(pl, "4_흡연집중지_DBSCAN.csv")
    print(H.head(5).to_string(index=False))
    print(SEPARATOR, end=end)
    if H.empty:
        C.save(pd.DataFrame(columns=HOTSPOT_COLUMNS + BOOTH_COLUMNS), "4_흡연부스_후보.csv")
        print("설정한 기준에서 집중지가 없어 부스 후보를 탐색하지 않았습니다.")
        return

    # 금지·배려 대상 (2번 코드와 같은 자료)
    print("\n<보행 지점에서 흡연부스 검토 후보 찾기>")
    print(SEPARATOR)
    B = find_booth_candidates(H, prepare_booth_search())
    C.save(B, "4_흡연부스_후보.csv")
    print("\n" + B["판단"].value_counts().to_string())
    print("\n적발 많은 집중지 상위 10\n" + B.head(10)[["대표장소", "적발건수", "가장많은시간", "판단", "집중지에서_m", "어린이집까지_m"]].to_string(index=False))
    print("설치 검토 시 실제 시설 경계, 보행 접근성, 현장 여건을 확인하세요.")
    print(SEPARATOR, end=end)


if __name__ == "__main__":
    main()
