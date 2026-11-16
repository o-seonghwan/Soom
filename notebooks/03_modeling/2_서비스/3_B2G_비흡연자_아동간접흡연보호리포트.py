"""
[문해솔 3] B2G · 비흡연자(보건소·어린이집) — AI 아동 간접흡연 보호 리포트
해결방법:
  ① 어린이집 노출 순위: 1번 모델의 위험점수를 어린이집 주변(등하원 동선 100m)에 공간결합 → 원아 수와 함께 순위
  ② 연기 영향 면적: 위험 상위10% 지점마다 21m 원(Kim & Lee 2024)을 그려 합친 면적(ha), 어린이집 주변과 겹친 곳
  ③ 단속 공백: 모델이 (학습에 안 쓴 블록 예측으로) 위험 상위10%로 본 곳 중 200m 안에 꽁초 적발·흡연 단속 기록이 없는 곳 → 순찰 후보
  ④ 단속 시간: 흡연 단속 시각 분포 (하원 시간 15시 이후 비율)
  ⑤ 확대 구 선정: 국민건강보험공단 0~9세 천식 진료인원 × 어린이집 현원으로 다음 적용 구 순위
정답 데이터: 1번과 같음(강남구 꽁초 적발) + 흡연단속내역(단속 위치·시각)
사회보장 데이터: 어린이집 기본정보(보육), 시군구별 천식 진료인원(국민건강보험공단)

실행: python 3_B2G_비흡연자_아동간접흡연보호리포트.py   (1번을 먼저 실행해야 함)
결과: 결과/3_어린이집_노출순위.csv, 3_단속공백_후보.csv, 3_단속_시간대.csv, 3_확대구_순위.csv, 3_요약.txt
"""
import os, sys
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C

CARE_ROUTE_R = 100       # 어린이집 등하원 동선 반경(m)
TOP = 90                 # 위험 상위 10% = 위험점수 90 이상
GAP_R = 200              # 이 반경 안에 단속·적발 기록이 없으면 '단속 공백'
GAP_MERGE_R = 100        # 공백 지점끼리 이 거리 안이면 한 곳으로 묶음
AFTER_SCHOOL_HOUR = 15   # 하원 시간 시작


def main():
    rf = C.EDA_OUT_DIR / "1_위험지도_지점.csv"
    if not rf.is_file():
        rf = C.RAW_OUT_DIR / rf.name
    if not rf.is_file():
        sys.exit("위험지도 CSV를 만들려면 1번 코드를 먼저 실행하세요.")
    R = pd.read_csv(rf)
    P = C.xy_m(R["위도"], R["경도"]); tree = cKDTree(P)
    hi = R["위험점수"] >= TOP
    lines = []

    # ① 어린이집 노출 순위
    care = C.load_daycare().to_crs(4326); care = care[care["시군구"] == C.GU_NAME].reset_index(drop=True)
    cP = C.xy_m(care.geometry.y, care.geometry.x)
    near = tree.query_ball_point(cP, CARE_ROUTE_R)
    care_t = pd.DataFrame({
        "어린이집명": care["어린이집명"], "유형": care["어린이집유형구분"], "주소": care["주소"], "현원": care["현원수"],
        "위도": care.geometry.y.round(6), "경도": care.geometry.x.round(6),
        "주변지점수": [len(i) for i in near],
        "주변_최고위험점수": [R["위험점수"].values[i].max() if i else np.nan for i in near],
        "주변_평균위험점수": [R["위험점수"].values[i].mean().round(1) if i else np.nan for i in near],
        "주변_상위10%지점수": [int(hi.values[i].sum()) if i else 0 for i in near],
    })
    care_t["노출점수"] = (0.5 * care_t["주변_최고위험점수"].fillna(0) + 0.5 * care_t["주변_평균위험점수"].fillna(0)).round(1)
    care_t["우선순위"] = care_t["노출점수"].rank(ascending=False, method="min").astype(int)
    care_t = care_t.sort_values(["우선순위", "현원"], ascending=[True, False])
    C.save(care_t, "3_어린이집_노출순위.csv")
    exposed = care_t[care_t["주변_상위10%지점수"] > 0]
    lines.append(f"① 어린이집 {len(care_t)}곳 중 등하원 동선({CARE_ROUTE_R}m) 안에 위험 상위10% 지점이 있는 곳: "
                 f"{len(exposed)}곳 (원아 {int(exposed['현원'].sum()):,}명)")

    # ② 연기 영향 면적 (21m 원의 합집합)
    import geopandas as gpd
    hp = gpd.GeoSeries(gpd.points_from_xy(R.loc[hi, "경도"], R.loc[hi, "위도"]), crs=4326).to_crs(C.CRS_M)
    smoke = hp.buffer(C.SMOKE_REACH_M).unary_union
    cz = gpd.GeoSeries(gpd.points_from_xy(care["geometry"].x, care["geometry"].y), crs=4326).to_crs(C.CRS_M).buffer(CARE_ROUTE_R)
    over = cz.intersects(smoke)
    lines.append(f"② 위험 상위10% 지점 {int(hi.sum()):,}곳의 연기 영향 면적({C.SMOKE_REACH_M}m 원 합): {smoke.area / 1e4:.1f} ha | "
                 f"어린이집 동선과 겹친 어린이집 {int(over.sum())}곳")
    gpd.GeoDataFrame({"구분": ["연기영향(21m)"]}, geometry=[smoke], crs=C.CRS_M).to_crs(4326) \
        .to_file(C.out_path("3_연기영향면적.geojson"), driver="GeoJSON")

    # ③ 단속 공백
    places = C.butt_places().dropna(subset=["위도"])
    fines = C.load_fines()
    fp = fines.dropna(subset=["위도"]).groupby(["위치이름", "위도", "경도"]).size().reset_index(name="건수")
    enf = np.vstack([C.xy_m(places["위도"], places["경도"]), C.xy_m(fp["위도"], fp["경도"])])
    d_enf, _ = cKDTree(enf).query(P)
    # 모델이 학습에 쓰지 않은 지점의 예측으로 순찰 후보를 찾는다.
    prediction_column = "시험셋_예측" if "시험셋_예측" in R else "교차검증_예측"
    high_test_risk = R[prediction_column].rank(pct=True) >= TOP / 100
    m = (high_test_risk & (d_enf > GAP_R)).values
    gap = R[m].copy()
    gap["단속기록까지_m"] = d_enf[m].round(0)
    if len(gap):     # 가까운 공백 지점 묶기
        gt = cKDTree(C.xy_m(gap["위도"], gap["경도"]))
        lab = -np.ones(len(gap), int); k = 0
        for i in np.argsort(-gap["위험점수"].values):
            if lab[i] >= 0: continue
            for j in gt.query_ball_point(C.xy_m([gap["위도"].values[i]], [gap["경도"].values[i]])[0], GAP_MERGE_R):
                if lab[j] < 0: lab[j] = k
            k += 1
        gap["묶음"] = lab
        dc, ic = cKDTree(cP).query(C.xy_m(gap["위도"], gap["경도"]))
        gap["가까운어린이집"] = care["어린이집명"].values[ic]; gap["어린이집거리m"] = dc.round(0)
        G = gap.sort_values("위험점수", ascending=False).groupby("묶음").agg(
            위도=("위도", "first"), 경도=("경도", "first"), 지점수=("노드 ID", "size"), 최고위험점수=("위험점수", "max"),
            단속기록까지_m=("단속기록까지_m", "min"), 가까운어린이집=("가까운어린이집", "first"), 어린이집거리m=("어린이집거리m", "min"))
        G = G.sort_values(["최고위험점수", "지점수"], ascending=False).reset_index(drop=True)
        G.index += 1; G.index.name = "순찰후보"
        C.save(G.reset_index(), "3_단속공백_후보.csv")
        lines.append(f"③ 단속 공백(학습에 쓰지 않은 지점 중 위험 상위10%, {GAP_R}m 안 기록 없음): {len(G)}곳 "
                     f"(그중 어린이집 {CARE_ROUTE_R}m 안 {int((G['어린이집거리m'] <= CARE_ROUTE_R).sum())}곳)")
    else:
        columns = ["순찰후보", "위도", "경도", "지점수", "최고위험점수", "단속기록까지_m", "가까운어린이집", "어린이집거리m"]
        C.save(pd.DataFrame(columns=columns), "3_단속공백_후보.csv")
        lines.append("③ 단속 공백 후보: 0곳")

    # ④ 단속 시간대
    hr = fines["시"].value_counts().sort_index().rename_axis("시").reset_index(name="단속건수")
    C.save(hr, "3_단속_시간대.csv")
    after = (fines["시"] >= AFTER_SCHOOL_HOUR).mean()
    care_f = fines[fines["장소유형"] == "어린이집"]
    lines.append(f"④ 흡연 단속 {len(fines):,}건 중 {AFTER_SCHOOL_HOUR}시 이후 {after:.1%} | 어린이집 관련 단속 {len(care_f):,}건 중 "
                 f"{AFTER_SCHOOL_HOUR}시 이후 {int((care_f['시'] >= AFTER_SCHOOL_HOUR).sum()):,}건")
    if "일시" in care_f:
        lines.append("   어린이집 관련 단속 연도별: " + care_f["일시"].dt.year.value_counts().sort_index().to_dict().__str__())

    # ⑤ 확대 구 선정 (천식 × 어린이집 현원)
    a = C.read_csv_any(C.find(C.F["asthma"]))
    a = a[a["시도"].astype(str).str.contains("서울")]
    y = a["진료개시년도"].max(); a = a[a["진료개시년도"] == y].copy()
    a["구"] = a["시도시군구"].astype(str).str.split().str[-1]
    a["천식_0_9세"] = pd.to_numeric(a["0-4세"], errors="coerce") + pd.to_numeric(a["5-9세"], errors="coerce")
    allcare = pd.DataFrame(C.load_daycare().drop(columns="geometry")).groupby("시군구").agg(어린이집수=("어린이집명", "size"), 원아수=("현원수", "sum"))
    ex = a[["구", "천식_0_9세"]].merge(allcare, left_on="구", right_index=True, how="left")
    ex["천식_순위"] = ex["천식_0_9세"].rank(ascending=False, method="min").astype(int)
    ex["원아_순위"] = ex["원아수"].rank(ascending=False, method="min")
    ex["확대우선점수"] = (ex["천식_0_9세"].rank(pct=True) * 0.6 + ex["원아수"].rank(pct=True) * 0.4).round(3)
    ex = ex.sort_values("확대우선점수", ascending=False).reset_index(drop=True)
    ex["비고"] = np.where(ex["구"] == C.GU_NAME, "현재 적용 구", "")
    ex.index += 1; ex.index.name = "확대순위"
    C.save(ex.reset_index(), "3_확대구_순위.csv")
    me = ex[ex["구"] == C.GU_NAME]
    lines.append(f"⑤ {y}년 0~9세 천식 진료인원: {C.GU_NAME} {int(me['천식_0_9세'].iloc[0]):,}명 (서울 {int(me['천식_순위'].iloc[0])}위) | "
                 f"다음 확대 우선 구: {', '.join(ex.loc[ex['구'] != C.GU_NAME, '구'].head(3))}")

    txt = "\n".join(lines)
    open(C.out_path("3_요약.txt"), "w", encoding="utf-8").write(txt + "\n")
    print("\n" + txt)


if __name__ == "__main__":
    main()
