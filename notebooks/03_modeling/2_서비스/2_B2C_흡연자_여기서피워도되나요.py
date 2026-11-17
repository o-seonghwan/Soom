"""
[문해솔 2] B2C · 흡연자 — "여기서 피워도 되나요?"
해결방법: 공간 버퍼(금지 반경) + KD-tree 최근접 탐색. 머신러닝 없음(규칙 기반)
         + 1번 결과(위험점수)를 써서 "사람 많은 곳 21m 안"이면 배려 권고
정답 데이터: 없음 (법·조례로 정해진 금연 반경을 그대로 적용)

판정 3단계
  ① 금지: 금연구역 반경 안 (어린이집 30m, 버스정류소 10m, 지하철 출입구 10m, 그 밖의 금연구역 지점 10m)
  ② 배려 권고: 금지는 아니지만 21m 안에 어린이집·버스정류소·위험 상위10% 지점이 있음 (연기 21m 도달, Kim & Lee 2024)
  ③ 가능: 위 두 조건에 걸리지 않음
  → ①② 이면 걸어서 가까운 '가능' 지점을 추천

실행:
  python 2_B2C_흡연자_여기서피워도되나요.py                  # 강남구 모든 지점 판정표 만들기
  python 2_B2C_흡연자_여기서피워도되나요.py 37.4979 127.0276  # 한 위치 판정 (위도 경도)
결과: 결과/2_흡연가능판정_지점.csv
주의: 금연구역·어린이집은 '점' 좌표라서 실제 경계와 몇 m 차이가 날 수 있음. 서비스에는 "참고용" 표시 필요.
"""
import sys, os
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C

# 금지 반경(m). 근거를 바꾸면 여기만 고치면 됨
BAN_R = {
    "어린이집": 30,        # 국민건강증진법: 어린이집·유치원 시설 경계 30m 이내 금연구역 (2024.8.17 시행)
    "버스정류소": 10,      # 서울특별시 간접흡연 피해방지 조례: 버스정류소 10m 이내
    "지하철출입구": 10,    # 금연구역 자료의 범위 '출입구 10M이내'
    "기타금연구역": 10,    # 공원·학교 등 지점 좌표. 실제 구역은 더 넓을 수 있음 → 점 좌표 근사
}
CARE_R = C.SMOKE_REACH_M   # 배려 권고 반경 21m
SEARCH_R = 300             # 대안 지점 찾는 반경(m)


def load_targets():
    """금지·배려 대상 위치를 위경도 표로"""
    nz = C.load_nosmoke(C.GU_NAME).to_crs(4326)
    sub = nz["금연구역구분"].fillna("").str.contains("지하철")
    care = C.load_daycare().to_crs(4326); care = care[care["시군구"] == C.GU_NAME]
    bus = C.load_bus().to_crs(4326)
    def tb(g, kind, name):
        return pd.DataFrame({"종류": kind, "이름": g[name].astype(str).values, "위도": g.geometry.y.values, "경도": g.geometry.x.values})
    T = pd.concat([tb(care, "어린이집", "어린이집명"), tb(bus, "버스정류소", "정류소명"),
                   tb(nz[sub], "지하철출입구", "금연구역명"), tb(nz[~sub], "기타금연구역", "금연구역명")], ignore_index=True)
    return T


def judge_points(lat, lon, T, risk=None):
    """여러 위치를 한 번에 판정. risk: 1번 결과(위도·경도·위험점수) 있으면 배려 판정에 씀"""
    P = C.xy_m(lat, lon)
    res = pd.DataFrame({"위도": lat, "경도": lon})
    # 사유는 파이썬 문자열(object)로 둔다. pandas 3 + pyarrow 문자열이면 빈 목록을 더할 때 오류가 난다
    res["판정"] = "가능"; res["사유"] = pd.Series([""] * len(res), index=res.index, dtype=object)
    for kind, r in BAN_R.items():
        t = T[T["종류"] == kind]
        if t.empty: continue
        d, i = cKDTree(C.xy_m(t["위도"], t["경도"])).query(P)
        res[f"{kind}_거리m"] = d.round(1)
        ban = d <= r
        res.loc[ban, "판정"] = "금지"
        res.loc[ban, "사유"] += [f"{kind} '{t['이름'].values[j]}' {dd:.0f}m(기준 {r}m); " for j, dd in zip(i[ban], d[ban])]
        warn = (~ban) & (d <= CARE_R) & (kind in ("어린이집", "버스정류소")) & (res["판정"] != "금지")
        res.loc[warn, "판정"] = "배려 권고"
        res.loc[warn, "사유"] += [f"{kind} '{t['이름'].values[j]}' {dd:.0f}m(연기 {CARE_R}m 도달); " for j, dd in zip(i[warn], d[warn])]
    if risk is not None:
        hi = risk[risk["위험점수"] >= 90]
        if len(hi):
            d, _ = cKDTree(C.xy_m(hi["위도"], hi["경도"])).query(P)
            warn = (d <= CARE_R) & (res["판정"] == "가능")
            res.loc[warn, "판정"] = "배려 권고"; res.loc[warn, "사유"] += "간접흡연 위험 상위10% 지점 21m 안; "
    return res


def main():
    T = load_targets()
    risk_f = C.EDA_OUT_DIR / "1_위험지도_지점.csv"
    if not risk_f.is_file():
        risk_f = C.RAW_OUT_DIR / risk_f.name
    risk = pd.read_csv(risk_f) if os.path.exists(risk_f) else None
    if risk is None: C.log("1번 결과가 없어 '사람 많은 곳' 배려 판정은 빼고 진행합니다 (1번을 먼저 돌리면 들어감).")
    nodes, _ = C.build_features()
    nodes = nodes[nodes["분석대상"] == 1].reset_index(drop=True)
    allj = judge_points(nodes["위도"].values, nodes["경도"].values, T, risk)
    allj.insert(0, "노드 ID", nodes["노드 ID"].values)
    allj["사유"] = allj["사유"].str.rstrip("; ")

    if len(sys.argv) >= 3:      # 한 위치 판정
        lat, lon = float(sys.argv[1]), float(sys.argv[2])
        r = judge_points(np.array([lat]), np.array([lon]), T, risk).iloc[0]
        print(f"\n[{lat}, {lon}] 판정: {r['판정']}\n  사유: {r['사유'] or '없음'}")
        if r["판정"] != "가능":
            ok = allj[allj["판정"] == "가능"]
            d, i = cKDTree(C.xy_m(ok["위도"], ok["경도"])).query(C.xy_m([lat], [lon])[0], k=3, distance_upper_bound=SEARCH_R)
            print("  가까운 '가능' 지점(직선거리):")
            for dd, ii in zip(np.atleast_1d(d), np.atleast_1d(i)):
                if np.isfinite(dd): print(f"   - {ok['위도'].values[ii]:.6f}, {ok['경도'].values[ii]:.6f} ({dd:.0f}m)")
        return

    C.save(allj, "2_흡연가능판정_지점.csv")
    print("\n판정 비율 (강남구 분석 지점)\n" + allj["판정"].value_counts(normalize=True).mul(100).round(1).astype(str).add("%").to_string())


if __name__ == "__main__":
    main()
