"""
4번(B2G) 흡연구역·흡연부스 입지 후보 제시 — 근거가 붙은 후보 목록

실행: python 4_B2G_흡연구역_입지후보.py
결과: 결과/4_입지후보/ 아래 CSV 3개
  4_입지후보_군집.csv   : 꽁초 적발 집중지(DBSCAN)별 현재 상태와 판정
  4_입지후보_후보지.csv : 집중지마다 근거 점수가 붙은 후보 지점(최대 3곳)
  4_입지후보_제외사유.csv : 집중지 200m 안 지점 중 제외된 지점과 이유

※ 이 결과는 "설치 확정"이 아니라 현장 확인 전 후보입니다.
※ pyproj·geopandas 없이 pandas·scipy·scikit-learn·xgboost만 씁니다. (학원 PC에서 실행 가능)

판단 순서 (근거)
 1) 수요   : 꽁초 적발 장소를 DBSCAN(30m, 30건, 적발 건수 가중)으로 묶은 집중지
             (흡연자가 실제로 피우는 곳에 둔다 — 싱가포르 NEA 흡연구역 지침 4번, Ickes 외 2015)
 2) 제외   : 금연구역 안, 학교 주변, 어린이집 30m 이내, 금연거리(큰길 보도) 구간
             (국민건강증진법 제9조 제6항 30m, 서울시 금연구역 자료의 범위 설명)
 3) 접근   : 집중지에서 보행 경로로 200m 이내 (후나바시시 실증: 역에서 약 200m 이내)
 4) 노출   : 후보 지점 21m 안을 지나는 보행 흐름(통행 경로 길이 합)
             (Kim & Lee 2024: 21m까지 실외 담배연기 검출. 田村 외 2023: 비흡연자 회피거리 최소화)
 5) 형태   : 보행 흐름이 많은 곳은 밀폐형, 적은 곳은 개방형 + 버퍼 (서울연구원 2018)
 6) 근거   : 연도 반복, 위험 모델 OOF 확률, 생활인구, 지하철 출입구 거리, 가까운 금연구역(풍선효과 흡수)
"""
import os, glob, re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parents[1]   # code 폴더 (결과\ 와 공통 데이터 위치 기준)
RESULT = Path(os.environ.get("RESULT_DIR", HERE / "결과"))
EDA = RESULT / "전처리기반"
OUT = Path(os.environ.get("OUT_DIR", RESULT / "4_입지후보"))
DRIVE_ROOT = os.environ.get("LUNG_DRIVE_ROOT", "")
DATA_ROOTS = [os.environ.get("LUNG_DATA_ROOT", ""), str(Path(DRIVE_ROOT) / "raw_data") if DRIVE_ROOT else "",
              str(HERE.parent / "02_1_분석데이터"),
              *[str(p / sub) for p in (HERE, *list(HERE.parents)[:3]) for sub in ("raw_data", os.path.join("data", "raw"))
                if (p / sub).is_dir()],
              str(HERE), str(HERE.parent)]

# ── 설정 ──────────────────────────────────────────────
EPS_M, MIN_REC = 30, 30          # DBSCAN (팀 기존 설정)
ACCESS_M = 200                   # 흡연자 접근 한계 (보행 경로 거리)
SMOKE_R = 21                     # 연기 영향 반경 (Kim & Lee 2024)
CARE_M = 30                      # 어린이집 이격 (국민건강증진법 제9조 제6항)
SCHOOL_M = 50                    # 학교정화구역 (금연구역 자료: 출입문에서 50m)
POINT_ZONE_M = 10                # 지하철역·출입구·택시승강장 (자료: 10m까지). 모든 지하철 출입구 노드에도 적용
STATION_ZONE_M = 15              # 주유소·가스충전소 (자료에 면적 없음 → 근사값)
MAIN_ROAD_M = 15                 # 금연거리 판정: 큰길까지 15m 이내 지점만
N_OD, OD_SEEDS = 5000, (7, 8, 9) # 보행 흐름 추정용 출발·도착 쌍 (생활인구 비례)
TOP_K = 3
BOOTHS = {  # 강남구 기존 분리형 흡연부스 (강남구 소식지 vol.367). 좌표는 같은 주소 적발 장소 좌표로 근사
    "테헤란로 424 부스": "테헤란로424", "테헤란로 124 부스": "테헤란로124"}


def precomputed(name):
    """VWorld로 미리 만든 좌표 파일: 결과/ 폴더 → 전처리본 폴더(processed_data, data/processed) 순서로 찾는다."""
    if (RESULT / name).is_file():
        return RESULT / name
    folders = [os.environ.get("LUNG_EDA_ROOT", ""), str(Path(DRIVE_ROOT) / "processed_data") if DRIVE_ROOT else "",
               *[str(p / sub) for p in (HERE, *list(HERE.parents)[:3]) for sub in ("processed_data", os.path.join("data", "processed"))]]
    for folder in [Path(f) for f in folders if f and os.path.isdir(f)]:
        hits = [folder / name] if (folder / name).is_file() else sorted(folder.rglob(name))
        if hits:
            return hits[0]
    raise FileNotFoundError(f"{name}이 없습니다. 드라이브 processed_data에서 받아 두세요.")


def find(pattern):
    for root in [r for r in DATA_ROOTS if r and os.path.isdir(r)]:
        hits = sorted(glob.glob(os.path.join(root, "**", pattern), recursive=True))
        if hits:
            return hits[0]
    raise FileNotFoundError(f"{pattern} 파일을 찾지 못했습니다. LUNG_DATA_ROOT를 지정하세요.")


def read_any(p, **kw):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(p, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue


def xy(lat, lon):  # 강남 부근 미터 근사 (pyproj 없이)
    return np.c_[(np.asarray(lon, float) - 127) * 88200, (np.asarray(lat, float) - 37.5) * 111000]


# ── 1. 데이터 ─────────────────────────────────────────
def load():
    nodes = pd.read_csv(EDA / "1_학습용_지점_21m.csv", encoding="utf-8-sig")
    links = pd.read_csv(EDA / "특성_강남구" / "보행링크.csv", encoding="utf-8-sig")
    places = pd.read_csv(EDA / "정답_꽁초적발_장소좌표.csv", encoding="utf-8-sig").dropna(subset=["위도"])
    recs = read_any(precomputed("강남_꽁초적발_전체기록_좌표.csv"))
    recs = recs[recs["좌표있음"] == 1].copy()
    recs["연도"] = pd.to_datetime(recs["위반일시"], errors="coerce").dt.year
    zones = read_any(find("nosmoking_zones_seoul.csv"), dtype=str)
    zones = zones[zones["시군구명"].str.contains("강남구", na=False)].drop_duplicates(["금연구역명", "위도", "경도"]).copy()
    for c in ("위도", "경도", "금연구역면적"):
        zones[c] = pd.to_numeric(zones[c], errors="coerce")
    care = read_any(find("어린이집기본정보_서울*.csv"), dtype=str)
    care = care[care["운영현황"].isin(["정상", "재개"])].copy()
    care[["위도", "경도"]] = care[["위도", "경도"]].apply(pd.to_numeric, errors="coerce")
    care = care.dropna(subset=["위도"])
    return nodes, links, places, recs, zones, care


def oof_risk(nodes):
    """공간 5-Fold로 학습하지 않은 구역의 위험 확률(OOF). 최종 설정: XGBoost 깊이 3"""
    from xgboost import XGBClassifier
    fe = ["주점_50m", "주점_100m", "편의점_50m", "음식점_50m", "상가_50m", "정류소_거리m", "지하철출입구_거리m",
          "생활인구_15_19", "길_중심성_log", "붙은길_큰길", "붙은길_골목", "큰길_거리m", "골목입구_거리m",
          "건물연면적_50m", "상업업무비율_50m", "격자_상업업무비율", "격자_주거비율", "어린이집_거리m"]
    folds = pd.read_csv(EDA / "1_강남_공간5Fold_분할.csv", encoding="utf-8-sig")
    assert (folds["노드 ID"].values == nodes["노드 ID"].values).all()
    X = nodes[fe].replace([np.inf, -np.inf], np.nan).fillna(nodes[fe].median()).values
    y = nodes["정답"].values
    p = np.full(len(nodes), np.nan)
    for k in range(1, 6):
        tr, te = folds[f"Fold_{k}"].eq("학습").values, folds[f"Fold_{k}"].eq("검증").values
        m = XGBClassifier(n_estimators=400, learning_rate=0.05, max_depth=3, subsample=0.8,
                          colsample_bytree=0.8, random_state=100, verbosity=0).fit(X[tr], y[tr])
        p[te] = m.predict_proba(X[te])[:, 1]
    return p


# ── 2. 보행망과 보행 흐름 ─────────────────────────────
class Walk:
    def __init__(self, nodes, links):
        idx = {n: i for i, n in enumerate(nodes["노드 ID"])}
        L = links[links["시작노드 ID"].isin(idx) & links["종료노드 ID"].isin(idx)].copy()
        L["a"] = L["시작노드 ID"].map(idx).astype(int); L["b"] = L["종료노드 ID"].map(idx).astype(int)
        L = L[L["a"] != L["b"]]
        u, v = np.minimum(L["a"], L["b"]), np.maximum(L["a"], L["b"])
        L = L.assign(u=u, v=v).sort_values("길이_m").drop_duplicates(["u", "v"])   # 양방향 중복 제거
        n = len(nodes)
        A = csr_matrix((np.ones(len(L)), (L["u"], L["v"])), shape=(n, n))
        _, lab = connected_components(A, directed=False)
        self.keep = lab == np.bincount(lab).argmax()
        L = L[self.keep[L["u"].values] & self.keep[L["v"].values]].reset_index(drop=True)
        self.n, self.u, self.v = n, L["u"].values, L["v"].values
        self.len = np.maximum(L["길이_m"].values, 0.1)
        self.G = csr_matrix((np.r_[self.len, self.len], (np.r_[self.u, self.v], np.r_[self.v, self.u])), shape=(n, n))
        self.P = xy(nodes["위도"], nodes["경도"])
        k = np.maximum(1, np.round(self.len / 5).astype(int))           # 링크를 5m 간격 점으로
        self.seg = np.repeat(np.arange(len(L)), k)
        t = (np.concatenate([np.arange(m) for m in k]) + 0.5) / np.repeat(k, k)
        self.pts = self.P[self.u][self.seg] * (1 - t[:, None]) + self.P[self.v][self.seg] * t[:, None]
        self.step = (self.len / k)[self.seg]                             # 점 하나가 대표하는 길이
        self.tree = cKDTree(self.pts)

    def flow(self, n_od, seed, weight, subway, lo=200, hi=1500, chunk=800):
        """보행 흐름 대리값: 출발·도착 쌍의 최단 경로가 링크를 지나는 비율
        가정) 통행의 절반은 지하철 출입구(30m 이내 노드)에서 출발, 나머지는 생활인구 비례 지점에서 출발.
              도착은 생활인구 비례. 서울 도심 보행이 지하철 출입구에 몰리는 점을 반영하기 위한 단순 가정."""
        rng = np.random.default_rng(seed)
        ids = np.where(self.keep)[0]
        w = np.nan_to_num(np.asarray(weight, float)[ids]); pr = w / w.sum()
        sub = ids[np.asarray(subway)[ids]]
        od = []
        while len(od) < n_od:
            s = rng.choice(sub) if rng.random() < 0.5 and len(sub) else rng.choice(ids, p=pr)
            t = rng.choice(ids, p=pr)
            if s != t and lo <= np.hypot(*(self.P[s] - self.P[t])) <= hi:
                od.append((s, t))
        od = np.array(od)
        eid = {}
        for i, (a, b) in enumerate(zip(self.u, self.v)):
            eid[(a, b)] = i; eid[(b, a)] = i
        cnt = np.zeros(len(self.len))
        src_all = np.unique(od[:, 0])
        for k in range(0, len(src_all), chunk):
            src = src_all[k:k + chunk]
            _, pred = dijkstra(self.G, directed=False, indices=src, return_predecessors=True)
            row = {s: i for i, s in enumerate(src)}
            for s, t in od[np.isin(od[:, 0], src)]:
                p, cur = pred[row[s]], t
                while cur != s and cur >= 0:
                    pv = p[cur]
                    if pv < 0:
                        break
                    cnt[eid[(pv, cur)]] += 1; cur = pv
        return cnt / len(od)

    def exposure(self, pxy, flow, r=SMOKE_R):
        """지점마다 반경 r 안을 지나는 '흐름 × 길이' 합 (통행 1회당 평균 m)"""
        w = flow[self.seg] * self.step
        out = np.zeros(len(pxy))
        for i, hits in enumerate(self.tree.query_ball_point(pxy, r)):
            out[i] = w[hits].sum()
        return out


# ── 3. 제외 조건 ─────────────────────────────────────
def exclusion(pxy, zones, care, nodes):
    """지점별 제외 사유 문자열 ('' 이면 통과)"""
    reasons = [[] for _ in range(len(pxy))]
    z = zones.dropna(subset=["위도"])
    zxy = xy(z["위도"], z["경도"])
    kind = z["금연구역구분"].fillna("").values
    for j, (k, (zx, zy)) in enumerate(zip(kind, zxy)):
        name = z["금연구역명"].values[j]
        if k in ("공원", "마을마당", "지방자치단체청사"):
            area = z["금연구역면적"].values[j]
            r = np.sqrt(area / np.pi) if area == area and area > 0 else 30
            label = f"금연구역({k}) 안"
        elif k == "학교정화구역":
            r, label = SCHOOL_M, "학교정화구역 50m"
        elif k in ("지하철역", "지하철 출입구", "택시승강장"):
            r, label = POINT_ZONE_M, f"{k} 10m"
        elif k in ("주유소", "가스충전소"):
            r, label = STATION_ZONE_M, f"{k} 주변(근사)"
        elif k == "거리":
            m = re.findall(r"(\d+)\s*m", z["금연구역범위상세"].fillna("").values[j])
            r = (max(map(int, m)) / 2) if m else 100
            label = "금연거리 구간(근사)"
        else:
            continue
        d = np.hypot(pxy[:, 0] - zx, pxy[:, 1] - zy)
        hit = d <= r
        if k == "거리":   # 금연거리는 큰길 보도 지점만 해당한다고 보고 판정
            hit &= nodes["큰길_거리m"].values <= MAIN_ROAD_M
        for i in np.where(hit)[0]:
            reasons[i].append(f"{label}: {name}")
    for i in np.where(nodes["지하철출입구_거리m"].values <= POINT_ZONE_M)[0]:
        reasons[i].append("지하철 출입구 10m (서울시 실외 금연구역)")
    cd, _ = cKDTree(xy(care["위도"], care["경도"])).query(pxy)
    for i in np.where(cd <= CARE_M)[0]:
        reasons[i].append(f"어린이집 {CARE_M}m 이내")
    return np.array([" / ".join(dict.fromkeys(r)) for r in reasons], dtype=object), cd


# ── 4. 메인 ──────────────────────────────────────────
def main():
    from sklearn.cluster import DBSCAN
    OUT.mkdir(parents=True, exist_ok=True)
    nodes, links, places, recs, zones, care = load()
    print(f"노드 {len(nodes):,} · 적발 장소 {len(places):,} · 금연구역(강남) {len(zones)} · 어린이집 {len(care):,}")

    # 1) 수요: DBSCAN 집중지
    pxy = xy(places["위도"], places["경도"])
    lab = DBSCAN(eps=EPS_M, min_samples=MIN_REC).fit(pxy, sample_weight=places["적발건수"].values).labels_
    places = places.assign(군집=lab)
    rec_xy = xy(recs["위도"], recs["경도"])
    _, ri = cKDTree(pxy).query(rec_xy)
    recs["군집"] = lab[ri]
    cl = []
    for c in sorted(set(lab) - {-1}):
        g = places[places["군집"] == c]
        w = g["적발건수"].values
        cxy = (pxy[lab == c] * w[:, None]).sum(0) / w.sum()
        yr = recs.loc[recs["군집"] == c, "연도"].value_counts()
        cl.append({"군집": c, "적발건수": int(w.sum()), "장소수": len(g),
                   "대표장소": g.sort_values("적발건수", ascending=False)["장소"].iloc[0],
                   "x": cxy[0], "y": cxy[1],
                   "위도": cxy[1] / 111000 + 37.5, "경도": cxy[0] / 88200 + 127,
                   "2022건": int(yr.get(2022, 0)), "2023건": int(yr.get(2023, 0)),
                   "반경m": float(np.hypot(*(pxy[lab == c] - cxy).T).max())})
    cl = pd.DataFrame(cl)
    print(f"집중지 {len(cl)}곳 (적발 {cl['적발건수'].sum():,}건)")

    # 2) 보행망·흐름·위험
    net = Walk(nodes, links)
    flow = np.mean([net.flow(N_OD, s, nodes["생활인구_15_19"].values, nodes["지하철출입구_거리m"].values <= 30) for s in OD_SEEDS], axis=0)
    print(f"보행 흐름: 통행 {N_OD * len(OD_SEEDS):,}회 · 흐름 0인 링크 {(flow == 0).mean():.1%}")
    risk = oof_risk(nodes)
    node_expo = net.exposure(net.P, flow)
    reason, care_d = exclusion(net.P, zones, care, nodes)
    expo_pct = pd.Series(node_expo[net.keep]).rank(pct=True)
    pct_of = lambda v: float((node_expo[net.keep] <= v).mean() * 100)
    zxy = xy(zones["위도"], zones["경도"])
    ztree = cKDTree(zxy)
    booth_xy = {}
    for name, key in BOOTHS.items():
        m = places[places["장소"].str.replace(" ", "").str.contains(key)]
        if len(m):
            booth_xy[name] = xy(m["위도"].iloc[:1], m["경도"].iloc[:1])[0]

    # 3) 집중지별 후보
    ntree = cKDTree(net.P)
    rows_c, rows_k, rows_x = [], [], []
    for _, c in cl.iterrows():
        cxy = np.array([c["x"], c["y"]])
        g = places[places["군집"] == c["군집"]]
        gxy = xy(g["위도"], g["경도"])
        gd, _ = net.tree.query(gxy)
        inside = gd <= SMOKE_R                       # 보행망 21m 밖 장소는 노출을 잴 수 없음
        cur_expo = (np.average(net.exposure(gxy[inside], flow), weights=g["적발건수"].values[inside])
                    if inside.any() else np.nan)
        measured = g["적발건수"].values[inside].sum() / g["적발건수"].sum()
        _, src = ntree.query(cxy)
        dist = dijkstra(net.G, directed=False, indices=src, limit=ACCESS_M)
        near = np.where(np.isfinite(dist) & net.keep)[0]
        cur_reason, = exclusion(cxy[None], zones, care, nodes.iloc[[src]].reset_index(drop=True))[0]
        care_c = cKDTree(xy(care["위도"], care["경도"])).query(cxy)[0]
        ok = [j for j in near if reason[j] == ""]
        for j in near:
            if reason[j]:
                rows_x.append({"군집": c["군집"], "노드 ID": nodes["노드 ID"].iloc[j], "접근거리m": round(dist[j], 1),
                               "제외사유": reason[j]})
        cand = pd.DataFrame({"j": ok})
        if len(cand):
            cand["접근거리m"] = dist[cand["j"]]
            cand["노출"] = node_expo[cand["j"]]
            # 같은 자리 주변 중복을 피하려 30m 안에서는 노출이 가장 낮은 지점 하나만
            cand = cand.sort_values(["노출", "접근거리m"])
            pick = []
            for j in cand["j"].astype(int):
                if all(np.hypot(*(net.P[j] - net.P[q])) > EPS_M for q in pick):
                    pick.append(j)
                if len(pick) == TOP_K:
                    break
        else:
            pick = []
        if care_c <= CARE_M or "학교" in cur_reason:
            verdict = "단속·계도 우선 (민감 시설 인접 집중지)"
        elif not pick:
            verdict = "200m 안 적합 지점 없음 → 단속·계도"
        else:
            verdict = "후보 검토"
        rows_c.append({"군집": c["군집"], "대표장소": c["대표장소"], "적발건수": c["적발건수"], "장소수": c["장소수"],
                       "2022건": c["2022건"], "2023건": c["2023건"],
                       "연도 반복": "예" if c["2022건"] and c["2023건"] else "아니오",
                       "군집반경m": round(c["반경m"], 1), "위도": round(c["위도"], 6), "경도": round(c["경도"], 6),
                       "현재위치 노출(m/통행)": round(cur_expo, 3) if cur_expo == cur_expo else np.nan,
                       "현재위치 노출 백분위": round(pct_of(cur_expo), 1) if cur_expo == cur_expo else np.nan,
                       "노출 측정 가능 적발 비율": round(measured, 3),
                       "현재위치 제외조건": cur_reason, "어린이집 거리m": round(care_c, 1),
                       "200m 안 지점": len(near), "제외 지점": len(near) - len(ok), "판정": verdict})
        if verdict != "후보 검토":
            continue
        for rank, j in enumerate(pick, 1):
            e = node_expo[j]
            zd, zi = ztree.query(net.P[j])
            bd = min(((np.hypot(*(net.P[j] - b)), n) for n, b in booth_xy.items()), default=(np.nan, ""))
            ep = pct_of(e)
            rows_k.append({
                "군집": c["군집"], "대표장소": c["대표장소"], "순위": rank, "노드 ID": nodes["노드 ID"].iloc[j],
                "위도": nodes["위도"].iloc[j], "경도": nodes["경도"].iloc[j],
                "접근거리m(보행)": round(dist[j], 1),
                "후보 노출(m/통행)": round(e, 3),
                "노출 변화율(현재 대비)": (round(1 - e / cur_expo, 3) if measured >= 0.5 and cur_expo > 0
                                       else "측정 불가(적발 장소 절반 이상이 보행망 밖)"),
                "보행흐름 백분위": round(ep, 1),
                "권장 형태": "밀폐형(흐름 상위 25%)" if ep >= 75 else "개방형 + 버퍼",
                "위험확률 OOF": round(risk[j], 3),
                "생활인구 15-18시": nodes["생활인구_15_19"].iloc[j],
                "지하철출입구 거리m": nodes["지하철출입구_거리m"].iloc[j],
                "어린이집 거리m": round(care_d[j], 1),
                "가까운 금연구역": zones["금연구역명"].iloc[zi], "금연구역 거리m": round(zd, 1),
                "기존 부스": bd[1], "기존 부스 거리m": round(bd[0], 1),
                "현장 확인": "보도 폭·건물 출입구 10m·사유지 여부·민원",
            })
    C = pd.DataFrame(rows_c); K = pd.DataFrame(rows_k); X = pd.DataFrame(rows_x)
    C.to_csv(OUT / "4_입지후보_군집.csv", index=False, encoding="utf-8-sig")
    K.to_csv(OUT / "4_입지후보_후보지.csv", index=False, encoding="utf-8-sig")
    X.to_csv(OUT / "4_입지후보_제외사유.csv", index=False, encoding="utf-8-sig")
    print(C["판정"].value_counts().to_string())
    if len(K):
        top = K[K["순위"] == 1]
        print(f"1순위 후보 {len(top)}곳 · 노출 변화율 중앙값 {pd.to_numeric(top['노출 변화율(현재 대비)'], errors='coerce').median():.1%} · "
              f"접근거리 중앙값 {top['접근거리m(보행)'].median():.0f}m")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
