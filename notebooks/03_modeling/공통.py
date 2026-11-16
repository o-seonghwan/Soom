"""
공통 모듈: 데이터 찾기·읽기, 걷는 길 지점 특성 만들기, 정답(꽁초 적발 장소) 좌표 붙이기
- 1~4번 코드가 모두 이 파일을 불러 씁니다. 같은 폴더에 두세요.
- 직접 실행하지 않아도 됩니다. (1번 코드를 처음 실행하면 특성표를 만들어 저장해 두고, 다음부터는 저장본을 씀)

데이터 위치
- 기본 데이터 폴더는 상위의 02_1_분석데이터입니다. 다른 폴더는 LUNG_DATA_ROOT로 지정하세요.
- 구글 드라이브 구조(processed_data/, raw_data/)와 깃허브 저장소 구조(data/processed/, data/raw/)도 읽습니다.
  LUNG_DRIVE_ROOT에 두 폴더가 들어 있는 최상위 폴더를 지정하면 raw_data를 원본, processed_data를 전처리본으로 씁니다.
  지정하지 않아도 기본 폴더(02_1_분석데이터, 전처리결과)가 없으면 코드 폴더와 그 상위 세 단계에서 자동으로 찾습니다.
- 우선순위: LUNG_DATA_ROOT·LUNG_EDA_ROOT > LUNG_DRIVE_ROOT > 기본 폴더 > 자동으로 찾은 드라이브 폴더
- 같은 이름 파일이 여러 곳에 있으면 'eda 완료' 폴더 안의 파일을 먼저 씁니다.
- VWorld 키는 .env 의 VWORLD_API_KEY 를 읽습니다. 키는 화면·파일 어디에도 출력하지 않습니다.
"""
import os, re, sys, glob, time, zipfile, fnmatch, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ═════════════════════════ 설정 ═════════════════════════
_HERE = Path(os.path.abspath(__file__)).parent


# 지원하는 폴더 구조: (전처리본 폴더, 원본 폴더)
#  - 구글 드라이브: processed_data/, raw_data/
#  - 깃허브 저장소: data/processed/, data/raw/
_LAYOUTS = (("processed_data", "raw_data"), (os.path.join("data", "processed"), os.path.join("data", "raw")))


def _layout_dirs():
    """(전처리본, 원본) 폴더. LUNG_DRIVE_ROOT가 있으면 그 아래에서, 없으면 코드 폴더와 상위 세 단계에서 찾는다."""
    configured = os.environ.get("LUNG_DRIVE_ROOT")
    folders = [Path(configured).resolve()] if configured else [_HERE, *list(_HERE.parents)[:3]]
    for folder in folders:
        for processed, raw in _LAYOUTS:
            if (folder / processed).is_dir() and (folder / raw).is_dir():
                return folder / processed, folder / raw
    if configured:
        return Path(configured).resolve() / "processed_data", Path(configured).resolve() / "raw_data"
    return None


def _default_data_root():
    if os.environ.get("LUNG_DRIVE_ROOT"):
        return str(_layout_dirs()[1])
    legacy = _HERE.parent / "02_1_분석데이터"
    if legacy.is_dir():
        return str(legacy)
    found = _layout_dirs()
    return str(found[1]) if found else str(legacy)


DATA_ROOT = os.environ.get("LUNG_DATA_ROOT", _default_data_root())
GU_NAME, GU_CODE = "강남구", "11680"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "결과")
RAW_OUT_DIR = Path(OUT_DIR)
EDA_OUT_DIR = RAW_OUT_DIR / "전처리기반"
TRAINING_DATA_PATH = EDA_OUT_DIR / "1_학습용_지점_21m.csv"
TRAINING_HOURLY_PATH = EDA_OUT_DIR / "특성_강남구" / "격자_시간대별_생활인구.csv"
VALIDATE_OTHER_GU = None   # 마포 외부 검증을 실행하려면 ("마포구", "11440")로 변경
EDA_ROOT = None
CRS_M = 5179               # 미터 단위 좌표계 (생활인구 250m 격자 기준)
SEED = 42

USE_VWORLD = True          # .env 에 키가 있으면 VWorld로 꽁초 적발 장소 좌표를 찾음 (없으면 로컬 방식만)
LIVEPOP_HOURS = [15, 16, 17, 18]   # 특성용 생활인구 시간대 평균 (15~19시)
R_NEAR, R_MID = 50, 100    # 개수를 셀 반경(m)
LABEL_R = 21               # 정답: 꽁초 적발 장소 21m 이내의 보행 지점 = 1
HIGH_R, MEDIUM_R = 10, 15
DISTANCE_RISK_LEVELS = ["고위험", "중위험", "저위험", "범위 밖"]
LABEL_COUNT_COLUMN = f"적발건수_{LABEL_R}m"
LABEL_DETAIL_COLUMNS = ["최근접_적발거리_m", "적발거리_위험등급", LABEL_COUNT_COLUMN]
MIN_WALK_M, MIN_GU_SHARE = 400, 0.5   # 분석 대상 격자: 보행로 400m 이상, 구 보행로 비율 50% 이상
MAIN_ROAD_TOP, ALLEY_BOTTOM, ALLEY_INTO_M, BTW_SAMPLES = 0.15, 0.50, 10, 600
BIZ_USES = ["업무시설", "판매시설", "제1종근린생활시설", "제2종근린생활시설"]
RES_USES = ["단독주택", "공동주택"]
SMOKE_REACH_M = 21         # 담배 연기가 의미 있게 퍼지는 거리 (Kim & Lee 2024, NTR, doi:10.1093/ntr/ntad241)

# 파일 이름 패턴 (드라이브 파일 이름 기준)
F = dict(
    pop_csv="250_LOCAL_RESD_*.csv", pop_zip="서울생활인구_250_LOCAL_RESD_*.zip",
    store_csv="*상가(상권)정보_서울_*.csv", store_zip="*상가(상권)정보_*.zip",
    bus="서울시버스정류소위치정보*.xlsx",
    nosmoke="nosmoking_zones_seoul.csv",
    walk="서울시 자치구별 도보 네트워크 공간정보.csv",
    building="AL_D010*.zip",
    daycare="어린이집기본정보_서울*.csv",
    asthma="국민건강보험공단_연도별 시군구별 천식*진료인원*.csv",
    butt="*강남구_쓰레기무단투기적발내역*.csv",
    fines="*강남구_흡연단속내역*.csv",
    mapo_hot="*마포구_담배꽁초*.csv",
)


def log(*a): print("▶", *a, flush=True)


def use_preprocessed_data():
    """1·4번에서 전처리본을 우선 사용하고 원본 기반 결과와 캐시를 분리한다."""
    global EDA_ROOT, OUT_DIR
    here = Path(__file__).resolve().parent
    configured = os.environ.get("LUNG_EDA_ROOT")
    found = _layout_dirs()
    if configured:
        EDA_ROOT = Path(configured).resolve()
    elif os.environ.get("LUNG_DRIVE_ROOT"):
        EDA_ROOT = found[0]
    else:
        legacy = next((here / name for name in ("전처리결과", "EDA결과") if (here / name).is_dir()), None)
        if legacy is not None:
            EDA_ROOT = legacy
        elif found is not None:
            EDA_ROOT = found[0]
        else:
            EDA_ROOT = here / "전처리결과"
    if not EDA_ROOT.is_dir():
        raise FileNotFoundError(f"전처리 결과 폴더를 찾을 수 없습니다. LUNG_EDA_ROOT를 확인하세요: {EDA_ROOT}")
    OUT_DIR = str(RAW_OUT_DIR / "전처리기반")
    log(f"전처리 입력: {EDA_ROOT}")
    log(f"원본 입력: {DATA_ROOT}")
    log("강남구 전처리본이 없는 상가·버스정류소·금연구역·어린이집·건물은 기존 자료 사용")


# 같은 데이터셋이 저장 위치에 따라 다른 폴더 이름을 쓴다.
# 예: PC 전처리결과는 250_LOCAL_RESD_20261027, 드라이브 processed_data는 local_resd_250m(_20261028)
EDA_FOLDER_ALIASES = {
    "250_LOCAL_RESD_*": ["250_LOCAL_RESD_*", "local_resd_250m*"],
}


def eda_tables(dataset, filename, multiple=False):
    patterns = EDA_FOLDER_ALIASES.get(dataset, [dataset])
    paths = sorted(p for p in EDA_ROOT.rglob(filename) if any(p.parent.match(pattern) for pattern in patterns))
    if not paths:
        raise FileNotFoundError(f"{EDA_ROOT}에 {dataset}/{filename}이 없습니다. 전처리 ZIP을 먼저 풀어 주세요.")
    if len({p.parent.name for p in paths}) != len(paths) or (not multiple and len(paths) != 1):
        raise ValueError(f"{dataset}/{filename}이 여러 곳에 있습니다. LUNG_EDA_ROOT에 사용할 배치 하나를 지정하세요.")
    return paths


# ═════════════════════════ 파일 찾기·읽기 ═════════════════════════
def roots():
    if DATA_ROOT:
        if not os.path.isdir(DATA_ROOT): sys.exit(f"DATA_ROOT 폴더가 없습니다: {DATA_ROOT}")
        return [DATA_ROOT]
    here = os.path.dirname(os.path.abspath(__file__))
    return [here, os.path.dirname(here)]


_INDEX = None
def _index():
    global _INDEX
    if _INDEX is None:
        _INDEX, seen = [], set()
        for r in roots():
            for d, _, files in os.walk(r):
                if "결과" in d.split(os.sep): continue
                for f in files:
                    p = os.path.abspath(os.path.join(d, f))
                    if p not in seen: seen.add(p); _INDEX.append(p)
    return _INDEX


def find_all(pattern):
    hits = [p for p in _index() if fnmatch.fnmatch(os.path.basename(p), pattern)]
    # 같은 파일이 여러 곳에 있으면 EDA 폴더('eda 완료', 'EDA결과' 등 경로에 eda가 들어간 폴더) 안의 파일을 먼저 씀
    return sorted(hits, key=lambda p: (0 if "eda" in p.lower().replace(os.sep, "/").rsplit("/", 1)[0] else 1, p))


def find(pattern, required=True):
    h = find_all(pattern)
    if h: return h[0]
    if required:
        sys.exit(f"데이터 파일을 찾지 못했습니다: {pattern}\n찾아본 폴더: {' | '.join(roots())}\n"
                 "→ LUNG_DATA_ROOT에 분석 데이터 폴더 경로를 지정해 주세요.")
    return None


def read_csv_any(src, **kw):
    """utf-8 → cp949 순서로 시도. src는 경로 또는 (zip, 이름)"""
    last = None
    for enc in ["utf-8-sig", "cp949"]:
        try:
            if isinstance(src, tuple):
                z, m = src
                return pd.read_csv(z.open(m), encoding=enc, **kw)
            return pd.read_csv(src, encoding=enc, **kw)
        except UnicodeDecodeError as e:
            last = e
    raise last


def zip_member(zpath, keyword):
    z = zipfile.ZipFile(zpath)
    for info in z.infolist():
        name = info.filename
        if not (info.flag_bits & 0x800):
            try: name = name.encode("cp437").decode("cp949")
            except Exception: pass
        if keyword in name and name.endswith(".csv"):
            return z, info.filename
    sys.exit(f"{zpath} 안에서 '{keyword}' csv를 찾지 못했습니다.")


def to_gdf(df, x, y, crs=4326):
    import geopandas as gpd
    df = df.copy()
    df[x] = pd.to_numeric(df[x], errors="coerce"); df[y] = pd.to_numeric(df[y], errors="coerce")
    df = df.dropna(subset=[x, y])
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x], df[y]), crs=crs).to_crs(CRS_M)


def xy_m(lat, lon):
    """위경도 → 미터 좌표(강남 부근 근사). KD-tree 거리 계산용"""
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    return np.c_[(lon - 127.0) * 88_200, (lat - 37.5) * 111_000]


def out_path(name):
    os.makedirs(OUT_DIR, exist_ok=True)
    return os.path.join(OUT_DIR, name)


def save(df, name):
    p = out_path(name); df.to_csv(p, index=False, encoding="utf-8-sig"); log(f"저장: {p} ({len(df):,}행)")
    return p


# ═════════════════════════ 데이터 읽기 ═════════════════════════
def load_livepop():
    """생활인구(여러 날) → [일자, 시간, 250M격자, 행정동코드, 생활인구합계]. '*'(비공개)는 공개된 최솟값으로 채움"""
    cols = ["일자", "시간", "250M격자", "행정동코드", "생활인구합계"]
    if EDA_ROOT is not None:
        paths = eda_tables("250_LOCAL_RESD_*", "features.csv", multiple=True)
        parts = [read_csv_any(p, dtype=str, usecols=cols) for p in paths]
        data = pd.concat(parts, ignore_index=True).drop_duplicates(cols[:4])
        data["시간"] = pd.to_numeric(data["시간"], errors="coerce")
        data["생활인구합계"] = pd.to_numeric(data["생활인구합계"], errors="coerce")
        days = ", ".join(sorted(data["일자"].dropna().unique()))
        log(f"전처리 생활인구: {days} | 비공개 값은 관측 평균 계산에서 제외")
        return data

    parts = [read_csv_any(p, dtype=str, usecols=cols) for p in find_all(F["pop_csv"])]
    if not parts:
        for zp in find_all(F["pop_zip"]):
            parts.append(read_csv_any(zip_member(zp, ".csv"), dtype=str, usecols=cols))
    if not parts: find(F["pop_csv"])
    df = pd.concat(parts, ignore_index=True).drop_duplicates(["일자", "시간", "250M격자", "행정동코드"])
    df["행정동코드"] = df["행정동코드"].str.strip()
    df["시간"] = pd.to_numeric(df["시간"], errors="coerce")
    masked = df["생활인구합계"].astype(str).str.strip().eq("*")
    df["생활인구합계"] = pd.to_numeric(df["생활인구합계"], errors="coerce")
    df.loc[masked, "생활인구합계"] = df.loc[df["생활인구합계"] > 0, "생활인구합계"].min()
    log(f"생활인구: {df['일자'].nunique()}일치 ({df['일자'].min()}~{df['일자'].max()}), 비공개 '*' {int(masked.sum()):,}칸 채움")
    return df


def grid_polygon(code):
    """250m 격자 코드(예: 다사44504525) → EPSG:5179 사각형"""
    from shapely.geometry import Polygon
    xl = "가나다라마바사아"
    e = (xl.index(code[0]) + 7) * 100000 + int(code[2:6]) * 10
    n = (xl.index(code[1]) + 13) * 100000 + int(code[6:10]) * 10
    return Polygon([(e, n), (e + 250, n), (e + 250, n + 250), (e, n + 250)])


def load_grids(pop, gu_code):
    import geopandas as gpd
    codes = sorted(pop.loc[pop["행정동코드"].str.startswith(gu_code), "250M격자"].unique())
    return gpd.GeoDataFrame({"격자ID": codes}, geometry=[grid_polygon(c) for c in codes], crs=CRS_M)


def grid_hourly(pop, grid_ids):
    """격자 × 시간(0~23) 평균 생활인구 (여러 날 평균)"""
    p = pop[pop["250M격자"].isin(grid_ids)]
    return p.groupby(["250M격자", "시간"])["생활인구합계"].mean().unstack().reindex(grid_ids)


def load_stores(area=None, cols=None):
    cols = cols or ["상호명", "시군구명", "상권업종대분류명", "상권업종중분류명", "상권업종소분류명", "경도", "위도"]
    p = find(F["store_csv"], required=False)
    src = p if p else zip_member(find(F["store_zip"]), "서울")
    s = read_csv_any(src, low_memory=False, usecols=cols)
    g = to_gdf(s, "경도", "위도")
    return g[g.within(area)].reset_index(drop=True) if area is not None else g


def load_bus():
    b = pd.read_excel(find(F["bus"]), dtype={"ARS_ID": str})
    b = b[b["정류소타입"] != "한강선착장"]
    return to_gdf(b, "X좌표", "Y좌표")


def load_nosmoke(gu=None):
    z = read_csv_any(find(F["nosmoke"]), dtype=str)
    if gu: z = z[z["시군구명"].str.replace("서울특별시 ", "", regex=False) == gu]
    z = z.drop_duplicates(["금연구역명", "위도", "경도"])
    return to_gdf(z, "경도", "위도")


def load_daycare(area=None):
    d = read_csv_any(find(F["daycare"]), dtype=str)
    d = d[d["운영현황"].astype(str).isin(["정상", "재개"])]
    d["현원수"] = pd.to_numeric(d["현원수"], errors="coerce").fillna(0).astype(int)
    g = to_gdf(d, "경도", "위도")
    return g[g.within(area)].reset_index(drop=True) if area is not None else g.reset_index(drop=True)


def load_walk(min_component=10, gu=GU_NAME):
    import geopandas as gpd, shapely, networkx as nx
    use_eda_walk = EDA_ROOT is not None and gu == GU_NAME
    if use_eda_walk:
        source = eda_tables("서울시 자치구별 도보 네트워크 공간정보", "clean.csv")[0]
        log(f"강남구 전처리 보행망: {source}")
    else:
        source = find(F["walk"])
    w = read_csv_any(source, low_memory=False, dtype={"링크 유형 코드": str, "노드 유형 코드": str},
                     usecols=["노드링크 유형", "노드 WKT", "노드 ID", "노드 유형 코드", "링크 WKT", "링크 유형 코드",
                              "시작노드 ID", "종료노드 ID", "시군구명"])
    if use_eda_walk and (w.empty or not w["시군구명"].eq(GU_NAME).all()):
        raise ValueError(f"강남구 노드·링크만 있는 보행망 clean.csv가 필요합니다: {source}")
    L = w[w["노드링크 유형"] == "LINK"].copy()
    L["code"] = L["링크 유형 코드"].fillna("0").str.split(".").str[0].str.zfill(4)
    L = L[L["code"].str[0] == "1"]                      # 보행자 통행 가능 링크
    L = gpd.GeoDataFrame(L[["시군구명", "시작노드 ID", "종료노드 ID"]], geometry=shapely.from_wkt(L["링크 WKT"].values), crs=4326).to_crs(CRS_M)
    L = L[L.geometry.notna() & ~L.geometry.is_empty].reset_index(drop=True)
    N = w[w["노드링크 유형"] == "NODE"].copy()
    N = gpd.GeoDataFrame(N[["노드 ID", "노드 유형 코드", "시군구명"]], geometry=shapely.from_wkt(N["노드 WKT"].values), crs=4326).to_crs(CRS_M)
    G = nx.Graph(); G.add_edges_from(zip(L["시작노드 ID"], L["종료노드 ID"]))
    small = set().union(*[c for c in nx.connected_components(G) if len(c) < min_component] or [set()])
    L = L[~L["시작노드 ID"].isin(small)].reset_index(drop=True)
    N = N[~N["노드 ID"].isin(small)].reset_index(drop=True)
    return L, N


def load_buildings(gu_code):
    import geopandas as gpd
    p = find(F["building"], required=False) or find("AL_D010*.shp")
    if p.endswith(".zip"):
        shp = [n for n in zipfile.ZipFile(p).namelist() if n.endswith(".shp")][0]
        p = f"/vsizip/{os.path.abspath(p)}/{shp}"
    b = gpd.read_file(p, encoding="euc-kr", engine="pyogrio", where=f"A3 LIKE '{gu_code}%'")
    b = b.rename(columns={"A9": "주용도", "A14": "연면적"})
    b["연면적"] = pd.to_numeric(b["연면적"], errors="coerce").fillna(0)
    return b.to_crs(CRS_M)


# ═════════════════════════ 특성 계산 ═════════════════════════
FEATURES = {
    "주점_50m": "반경 50m 주점 수", "주점_100m": "반경 100m 주점 수", "편의점_50m": "반경 50m 편의점 수",
    "음식점_50m": "반경 50m 음식점 수", "상가_50m": "반경 50m 전체 상가 수",
    "정류소_거리m": "가장 가까운 버스정류소까지 거리", "지하철출입구_거리m": "가장 가까운 지하철 출입구까지 거리",
    "생활인구_15_19": "지점 격자의 15~19시 평균 생활인구",
    "길_중심성_log": "붙은 길의 매개 중심성(사람이 지나갈 길목인 정도, log)",
    "붙은길_큰길": "붙은 길이 큰길이면 1", "붙은길_골목": "붙은 길이 골목이면 1",
    "큰길_거리m": "가장 가까운 큰길까지 거리", "골목입구_거리m": "가장 가까운 큰길 옆 골목 입구까지 거리",
    "건물연면적_50m": "반경 50m 건물 연면적 합", "상업업무비율_50m": "반경 50m 연면적 중 업무·판매·근린생활 비율",
    "격자_상업업무비율": "격자의 상업·업무 연면적 비율", "격자_주거비율": "격자의 주거 연면적 비율",
    "어린이집_거리m": "가장 가까운 어린이집까지 거리",
}
LEAK = ["금연구역_거리m"]   # 단속 장소와 겹쳐 정답을 미리 알려 주는 특성 → 모델 입력에서 뺌


def nearest_dist(pts, target):
    if len(target) == 0: return np.full(len(pts), np.nan)
    (ip, it), d = target.sindex.nearest(pts.geometry, return_distance=True, return_all=False)
    out = np.full(len(pts), np.nan); out[ip] = d
    return out.round(1)


def count_within(pts, target, r):
    if len(target) == 0: return np.zeros(len(pts), int)
    ip, _ = target.sindex.query(pts.geometry, predicate="dwithin", distance=r)
    return np.bincount(ip, minlength=len(pts))


def road_classes(links, area):
    """보행 링크 매개 중심성 → 큰길/골목 구분, 골목 입구 점"""
    import geopandas as gpd, networkx as nx
    sub = links[links.intersects(area)].copy()
    G = nx.Graph()
    for i, a, b, g in zip(sub.index, sub["시작노드 ID"], sub["종료노드 ID"], sub.geometry):
        if pd.notna(a) and pd.notna(b) and a != b: G.add_edge(a, b, idx=i, length=g.length)
    log(f"길목 계산(매개 중심성): 노드 {G.number_of_nodes():,}개 — 1~3분 걸림")
    btw = nx.edge_betweenness_centrality(G, k=min(BTW_SAMPLES, G.number_of_nodes()), weight="length", seed=SEED)
    sub["btw"] = np.nan
    for (a, b), v in btw.items(): sub.at[G[a][b]["idx"], "btw"] = v
    hi, lo = sub["btw"].quantile(1 - MAIN_ROAD_TOP), sub["btw"].quantile(ALLEY_BOTTOM)
    sub["길유형"] = np.select([sub["btw"] >= hi, sub["btw"] <= lo], ["큰길", "골목"], "중간")
    main = set(sub.loc[sub["길유형"] == "큰길", "시작노드 ID"]) | set(sub.loc[sub["길유형"] == "큰길", "종료노드 ID"])
    pts = []
    for _, r in sub[sub["길유형"] == "골목"].iterrows():
        g = r.geometry
        if g.geom_type != "LineString" or g.length < ALLEY_INTO_M + 5: continue
        if r["시작노드 ID"] in main: pts.append(g.interpolate(ALLEY_INTO_M))
        if r["종료노드 ID"] in main: pts.append(g.interpolate(g.length - ALLEY_INTO_M))
    return sub.reset_index(drop=True), gpd.GeoDataFrame(geometry=pts, crs=CRS_M)


def grid_stats(grids, links, buildings, gu):
    import geopandas as gpd, shapely
    il, ig = links.sindex.query(grids.geometry, predicate="intersects")[::-1]
    inter = shapely.intersection(links.geometry.values[il], grids.geometry.values[ig])
    t = pd.DataFrame({"g": ig, "len": shapely.length(inter), "gu": links["시군구명"].values[il]})
    tot = t.groupby("g")["len"].sum(); own = t[t["gu"] == gu].groupby("g")["len"].sum()
    grids["보행링크_m"] = grids.index.map(tot).fillna(0).round()
    grids["구비율"] = (grids.index.map(own).fillna(0) / grids["보행링크_m"].replace(0, np.nan)).fillna(0).round(2)
    c = buildings[["주용도", "연면적", "geometry"]].copy(); c["geometry"] = c.geometry.centroid
    j = gpd.sjoin(c, grids[["격자ID", "geometry"]], predicate="within")
    a = j.groupby("격자ID")["연면적"].sum()
    grids["상업업무비율"] = grids["격자ID"].map(j[j["주용도"].isin(BIZ_USES)].groupby("격자ID")["연면적"].sum() / a).fillna(0).round(2)
    grids["주거비율"] = grids["격자ID"].map(j[j["주용도"].isin(RES_USES)].groupby("격자ID")["연면적"].sum() / a).fillna(0).round(2)
    return grids


def build_features(gu=GU_NAME, gu_code=GU_CODE, rebuild=False):
    """구의 걷는 길 지점(보행 노드)마다 특성 18개 계산 → 결과/특성_<구>/ 에 저장. 이미 있으면 저장본을 읽음
    반환: (nodes 특성표, grid_hourly 격자×시간 생활인구)"""
    d = out_path(f"특성_{gu}"); os.makedirs(d, exist_ok=True)
    fp, hp = os.path.join(d, "지점특성.csv"), os.path.join(d, "격자_시간대별_생활인구.csv")
    if os.path.exists(fp) and os.path.exists(hp) and not rebuild:
        log(f"저장된 특성표 사용: {fp}  (다시 만들려면 파일을 지우세요)")
        return pd.read_csv(fp), pd.read_csv(hp, index_col=0)
    import geopandas as gpd

    log(f"{gu} 특성 만들기 시작 (처음 한 번만, 5~10분)")
    pop = load_livepop()
    grids = load_grids(pop, gu_code)
    links, nodes = load_walk(gu=gu)
    buildings = load_buildings(gu_code)
    area = grids.unary_union.buffer(1000)
    grids = grid_stats(grids, links, buildings, gu)
    hourly = grid_hourly(pop, grids["격자ID"].tolist())
    grids["생활인구_15_19"] = grids["격자ID"].map(hourly[LIVEPOP_HOURS].mean(axis=1)).round(1)
    roads, alley = road_classes(links, area)
    stores = load_stores(area)
    bus = load_bus(); nz = load_nosmoke(gu); care = load_daycare(area)
    exits = nodes[nodes["노드 유형 코드"].astype(str).str.startswith("1")][["geometry"]]   # 지하철 출입구 노드
    subway = gpd.GeoDataFrame(pd.concat([exits, nz[nz["금연구역구분"].fillna("").str.contains("지하철")][["geometry"]]],
                                        ignore_index=True), crs=CRS_M)
    log(f"자료: 격자 {len(grids)}, 상가 {len(stores):,}, 정류소 {len(bus):,}, 지하철 위치 {len(subway)}, 어린이집 {len(care)}, 건물 {len(buildings):,}")

    eligible = grids["보행링크_m"] >= MIN_WALK_M
    if EDA_ROOT is None or gu != GU_NAME:
        eligible &= grids["구비율"] >= MIN_GU_SHARE
    elig = set(grids.loc[eligible, "격자ID"])
    pts = gpd.sjoin(nodes[["노드 ID", "geometry"]], grids[["격자ID", "geometry"]], predicate="within")
    pts = pts.drop(columns="index_right").drop_duplicates("노드 ID").reset_index(drop=True)
    pts["분석대상"] = pts["격자ID"].isin(elig).astype(int)

    f = pd.DataFrame(index=pts.index)
    bars = stores[stores["상권업종중분류명"].astype(str).str.contains("주점")]
    f["주점_50m"] = count_within(pts, bars, R_NEAR); f["주점_100m"] = count_within(pts, bars, R_MID)
    f["편의점_50m"] = count_within(pts, stores[stores["상권업종소분류명"].astype(str).str.contains("편의점")], R_NEAR)
    f["음식점_50m"] = count_within(pts, stores[stores["상권업종대분류명"].astype(str).str.contains("음식")], R_NEAR)
    f["상가_50m"] = count_within(pts, stores, R_NEAR)
    f["정류소_거리m"] = nearest_dist(pts, bus)
    f["지하철출입구_거리m"] = nearest_dist(pts, subway)
    f["금연구역_거리m"] = nearest_dist(pts, nz)
    f["어린이집_거리m"] = nearest_dist(pts, care)
    g = grids.set_index("격자ID")
    f["생활인구_15_19"] = pts["격자ID"].map(g["생활인구_15_19"]).values
    f["격자_상업업무비율"] = pts["격자ID"].map(g["상업업무비율"]).values
    f["격자_주거비율"] = pts["격자ID"].map(g["주거비율"]).values
    (ip, ir), _ = roads.sindex.nearest(pts.geometry, return_distance=True, return_all=False)
    btw = np.zeros(len(pts)); kind = np.full(len(pts), "", object)
    btw[ip] = roads["btw"].values[ir]; kind[ip] = roads["길유형"].values[ir]
    f["길_중심성_log"] = np.log10(np.nan_to_num(btw) + 1e-6).round(3)
    f["붙은길_큰길"] = (kind == "큰길").astype(int); f["붙은길_골목"] = (kind == "골목").astype(int)
    f["큰길_거리m"] = nearest_dist(pts, roads[roads["길유형"] == "큰길"])
    f["골목입구_거리m"] = nearest_dist(pts, alley)
    ip, ib = buildings.sindex.query(pts.geometry, predicate="dwithin", distance=R_NEAR)
    t = pd.DataFrame({"p": ip, "a": buildings["연면적"].values[ib], "biz": buildings["주용도"].isin(BIZ_USES).values[ib]})
    tot = t.groupby("p")["a"].sum(); biz = t[t["biz"]].groupby("p")["a"].sum()
    pos = pd.Series(np.arange(len(pts)))
    f["건물연면적_50m"] = pos.map(tot).fillna(0).round(0).values
    f["상업업무비율_50m"] = (pos.map(biz).fillna(0) / pos.map(tot).replace(0, np.nan)).fillna(0).round(3).values

    ll = pts.to_crs(4326)
    out = pd.concat([pts[["노드 ID", "격자ID", "분석대상"]].assign(구=gu),
                     pd.DataFrame({"위도": ll.geometry.y.round(6), "경도": ll.geometry.x.round(6)}), f], axis=1)
    out.to_csv(fp, index=False, encoding="utf-8-sig")
    hourly.to_csv(hp, encoding="utf-8-sig")
    # 길찾기·지도용 보조 파일
    ids = set(out["노드 ID"])
    e = links[links["시작노드 ID"].isin(ids) & links["종료노드 ID"].isin(ids) & (links["시작노드 ID"] != links["종료노드 ID"])]
    pd.DataFrame({"시작노드 ID": e["시작노드 ID"].values, "종료노드 ID": e["종료노드 ID"].values,
                  "길이_m": e.geometry.length.round(1).values}).to_csv(os.path.join(d, "보행링크.csv"), index=False, encoding="utf-8-sig")
    log(f"저장: {fp} (지점 {len(out):,}개, 분석대상 {int(out['분석대상'].sum()):,}개)")
    return out, hourly


# ═════════════════════════ VWorld (주소 → 좌표) ═════════════════════════
def vworld_key():
    here = os.path.dirname(os.path.abspath(__file__))
    for d in [here, os.path.dirname(here), DATA_ROOT, os.path.expanduser("~/Downloads"), os.path.expanduser("~/다운로드")]:
        p = os.path.join(d, ".env") if d else ""
        if p and os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                if line.strip().startswith("VWORLD_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("VWORLD_API_KEY")


def vworld(q, how, key):
    """how: road / parcel / place. 실패하면 (None, None). 키가 섞인 URL은 출력하지 않음"""
    import requests
    try:
        if how in ("road", "parcel"):
            r = requests.get("https://api.vworld.kr/req/address", timeout=10, params={
                "service": "address", "request": "getcoord", "version": "2.0", "crs": "epsg:4326", "address": q,
                "refine": "true", "simple": "false", "format": "json", "type": how, "key": key})
            res = r.json().get("response", {})
            if res.get("status") == "OK":
                pt = res["result"]["point"]; return float(pt["y"]), float(pt["x"])
            return vworld(q, "place", key) if how == "road" else (None, None)
        r = requests.get("https://api.vworld.kr/req/search", timeout=10, params={
            "service": "search", "request": "search", "version": "2.0", "crs": "epsg:4326", "size": "1", "page": "1",
            "query": q, "type": "place", "format": "json", "key": key})
        res = r.json().get("response", {})
        if res.get("status") == "OK":
            it = res["result"]["items"][0]["point"]; return float(it["y"]), float(it["x"])
    except Exception as e:
        print(f"  요청 오류({q}): {type(e).__name__}")
    return None, None


def geocode_many(queries, cache_name, bbox):
    """[(검색어, 방식)] → {(검색어, 방식): (위도, 경도)}. 결과/ 캐시에 저장해 다시 묻지 않음"""
    cp = out_path(cache_name)
    cache = pd.read_csv(cp, dtype={"검색어": str}) if os.path.exists(cp) else pd.DataFrame(columns=["검색어", "방식", "위도", "경도"])
    done = set(zip(cache["검색어"], cache["방식"]))
    todo = [q for q in dict.fromkeys(queries) if q not in done]
    key = vworld_key() if (todo and USE_VWORLD) else None
    if todo and not key:
        log(f"VWorld 키가 없어 {len(todo):,}곳은 VWorld로 찾지 않습니다 (.env 의 VWORLD_API_KEY)")
    if todo and key:
        log(f"VWorld 좌표 찾기 {len(todo):,}곳 (중간에 끊겨도 다시 실행하면 이어서 함)")
        rows = []
        for i, (q, h) in enumerate(todo, 1):
            lat, lon = vworld(q, h, key)
            if lat is not None and not (bbox[0] <= lat <= bbox[1] and bbox[2] <= lon <= bbox[3]): lat = lon = None
            rows.append({"검색어": q, "방식": h, "위도": lat, "경도": lon})
            if i % 100 == 0 or i == len(todo):
                cache = pd.concat([cache, pd.DataFrame(rows)], ignore_index=True); rows = []
                cache.to_csv(cp, index=False, encoding="utf-8-sig"); log(f"  {i:,}/{len(todo):,}")
            time.sleep(0.15)
    c = cache.dropna(subset=["위도"])
    return {(q, h): (float(a), float(b)) for q, h, a, b in zip(c["검색어"], c["방식"], c["위도"], c["경도"])}


# ═════════════════════════ 정답: 강남구 담배꽁초 적발 장소 ═════════════════════════
GN_BBOX = (37.45, 37.55, 127.00, 127.14)


def load_butt_records():
    if EDA_ROOT is not None:
        path = eda_tables("*강남구_쓰레기무단투기적발내역*", "clean.csv")[0]
        cols = ["source_row_id", "cigarette_butt_offense_flag", "place_normalized", "violation_datetime"]
        data = read_csv_any(path, usecols=cols, dtype={"cigarette_butt_offense_flag": "boolean"})
        data = data.loc[data["cigarette_butt_offense_flag"].fillna(False)].rename(
            columns={"place_normalized": "장소", "violation_datetime": "일시"}
        )
        data["일시"] = pd.to_datetime(data["일시"], errors="coerce", format="mixed")
        log(f"전처리 꽁초 적발: {len(data):,}건 | {path}")
        return data

    d = read_csv_any(find(F["butt"]), dtype=str)
    d = d[d["위반쓰레기"].str.contains("꽁초", na=False)].copy()
    d["장소"] = d["위반장소"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    d["일시"] = pd.to_datetime(d["위반일시"], errors="coerce")
    return d


def _vworld_query(p):
    s = p
    m = re.match(r"^(?:\S+동\s*)?(\S+역)\s*(\d+)\s*번?\s*출구", s)
    if m: return f"{m.group(1)} {m.group(2)}번출구", "place"
    m = re.match(r"^(?:(\S+동)\s*)?(\S+?(?:로|길))\s*(\d+(?:-\d+)?)$", s)
    if m: return f"서울특별시 강남구 {m.group(2)} {m.group(3)}", "road"
    m = re.match(r"^(\S+동)\s*(?:산\s*)?(\d+(?:-\d+)?)$", s)
    if m: return f"서울특별시 강남구 {m.group(1)} {m.group(2)}", "parcel"
    return f"서울 강남구 {s}", "place"


def _local_geocoder():
    """VWorld 없이: 상가정보 주소·건물명, 금연구역 자료의 지하철역(출구) 좌표로 찾기"""
    # 좌표계 변환(pyproj) 없이 pandas만 씀 → pyproj가 막힌 PC에서도 돌아감
    sp = find(F["store_csv"], required=False)
    src = sp if sp else zip_member(find(F["store_zip"]), "서울")
    s = read_csv_any(src, low_memory=False, usecols=["시군구명", "도로명주소", "지번주소", "건물명", "경도", "위도"])
    s = s[s["시군구명"] == GU_NAME].copy()
    s["위도"] = pd.to_numeric(s["위도"], errors="coerce"); s["경도"] = pd.to_numeric(s["경도"], errors="coerce")
    s = s.dropna(subset=["위도", "경도"])
    pre = f"서울특별시 {GU_NAME} "
    s["road"] = s["도로명주소"].astype(str).str.replace(pre, "", regex=False).str.replace(r"\s+", " ", regex=True)
    s["jibun"] = s["지번주소"].astype(str).str.replace(pre, "", regex=False)
    s["dong"] = s["jibun"].str.split(" ").str[0]
    ROAD = s.groupby("road")[["위도", "경도"]].mean(); JIB = s.groupby("jibun")[["위도", "경도"]].mean()
    BLD = s.dropna(subset=["건물명"]).groupby(["dong", "건물명"])[["위도", "경도"]].mean()
    rr = s["road"].str.extract(r"^(\S+?(?:로|길)) (\d+)(?:-\d+)?$"); s["rname"] = rr[0]; s["rno"] = pd.to_numeric(rr[1])
    z = read_csv_any(find(F["nosmoke"]), dtype=str)
    z = z[(z["시군구명"].str.replace("서울특별시 ", "", regex=False) == GU_NAME) & z["금연구역구분"].fillna("").str.contains("지하철")]
    z = z.dropna(subset=["위도", "경도"])
    z["위도"] = z["위도"].astype(float); z["경도"] = z["경도"].astype(float)
    EXIT = z.groupby("금연구역명")[["위도", "경도"]].mean()

    def geo(p):
        p = re.sub(r"^\S+동 (?=\S+역)", "", p)
        m = re.match(r"^(\S+역)\s*(?:(\d+)\s*번?\s*출구)?", p)
        if m and (m.group(2) or re.fullmatch(r"\S+역", p)):
            k = f"{m.group(1)}({m.group(2)}번출구)" if m.group(2) else m.group(1)
            if k in EXIT.index: return (*EXIT.loc[k], "역출구" if m.group(2) else "역")
            c = [n for n in EXIT.index if n.startswith(m.group(1))]
            return (*EXIT.loc[c].mean(), "역(평균)") if c else (None, None, "실패")
        m = re.match(r"^(?:(\S+동) )?(\S+?(?:로|길)) ?(\d+)(?:-\d+)?$", p)
        if m:
            k = f"{m.group(2)} {m.group(3)}"
            if k in ROAD.index: return (*ROAD.loc[k], "도로명")
            c = s[s["rname"] == m.group(2)].assign(diff=lambda x: (x["rno"] - int(m.group(3))).abs())
            c = c[c["diff"] <= 6]
            if len(c): b = c[c["diff"] == c["diff"].min()]; return b["위도"].mean(), b["경도"].mean(), "도로명(가까운번호)"
            return None, None, "실패"
        m = re.match(r"^(\S+동) (\d+(?:-\d+)?)$", p)
        if m:
            k = f"{m.group(1)} {m.group(2)}"
            if k in JIB.index: return (*JIB.loc[k], "지번")
            base = f"{m.group(1)} {m.group(2).split('-')[0]}"
            c = [j for j in JIB.index if j == base or j.startswith(base + "-")]
            return (*JIB.loc[c].mean(), "지번(본번)") if c else (None, None, "실패")
        m = re.match(r"^(\S+동) (.+)$", p)
        if m:
            nm = re.sub(r"(앞|옆|뒤|건너편|입구)$", "", m.group(2)).strip()
            if (m.group(1), nm) in BLD.index: return (*BLD.loc[(m.group(1), nm)], "건물명")
        return None, None, "실패"
    return geo


def butt_places(records=None):
    """꽁초 적발 장소별 [장소, 적발건수, 위도, 경도, 방식]. VWorld(키 있을 때) → 실패한 곳만 로컬 방식"""
    cp = out_path("정답_꽁초적발_장소좌표.csv")
    if EDA_ROOT is not None:
        # 적발 건수는 전처리 행에서 다시 집계하고, 기존 결과에서는 주소별 좌표만 가져온다.
        records = load_butt_records() if records is None else records
        counts = records["장소"].value_counts().rename_axis("장소").reset_index(name="적발건수")
        source = RAW_OUT_DIR / "정답_꽁초적발_장소좌표.csv"
        if not source.is_file():
            raise FileNotFoundError(f"전처리 적발표에는 좌표가 없습니다. 0_VWorld_좌표찾기.py로 좌표표를 준비하세요: {source}")
        xy = read_csv_any(source, usecols=["장소", "위도", "경도", "방식"]).dropna(subset=["장소", "위도", "경도"])
        places = counts.merge(xy.drop_duplicates(), on="장소", how="left", validate="one_to_one")
        matched = places.loc[places["위도"].notna(), "적발건수"].sum()
        log(f"기존 좌표표와 주소 일치: {matched:,}/{len(records):,}건")
        save(places, "정답_꽁초적발_장소좌표.csv")
        return places

    if os.path.exists(cp):
        log(f"저장된 정답 좌표 사용: {cp}"); return pd.read_csv(cp)
    d = load_butt_records()
    P = d["장소"].value_counts().rename_axis("장소").reset_index(name="적발건수")
    q = [_vworld_query(p) for p in P["장소"]]
    hit = geocode_many(q, "vworld_캐시_꽁초.csv", GN_BBOX)
    P["위도"] = [hit.get(k, (None, None))[0] for k in q]; P["경도"] = [hit.get(k, (None, None))[1] for k in q]
    P["방식"] = np.where(P["위도"].notna(), "VWorld", "")
    miss = P["위도"].isna()
    if miss.any():
        geo = _local_geocoder()
        R = P.loc[miss, "장소"].apply(lambda p: pd.Series(geo(p), index=["위도", "경도", "방식"]))
        P.loc[miss, ["위도", "경도", "방식"]] = R.values
        P.loc[miss & P["위도"].notna(), "방식"] = "로컬:" + P.loc[miss & P["위도"].notna(), "방식"].astype(str)
    P["위도"] = pd.to_numeric(P["위도"], errors="coerce"); P["경도"] = pd.to_numeric(P["경도"], errors="coerce")
    ok = P["위도"].notna()
    log(f"정답 좌표: 장소 {ok.sum():,}/{len(P):,}곳, 적발 {P.loc[ok, '적발건수'].sum():,}/{P['적발건수'].sum():,}건 | 방식별 {P.loc[ok, '방식'].str.split(':').str[0].value_counts().to_dict()}")
    P.to_csv(cp, index=False, encoding="utf-8-sig")
    return P


def butt_records_with_xy():
    """꽁초 적발 기록 한 줄마다 좌표·시각 (좌표 못 찾은 기록은 뺌)"""
    d = load_butt_records()
    P = butt_places(records=d).dropna(subset=["위도", "경도"])
    return d.merge(P[["장소", "위도", "경도"]], on="장소", how="inner")


# ═════════════════════════ 흡연단속(과태료) 내역 ═════════════════════════
def load_fines():
    """강남구 흡연단속내역 → 시각, 장소유형, (규칙으로 찾은) 위치이름·좌표"""
    d = read_csv_any(find(F["fines"]))
    d["장소"] = d["위반장소"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    d["일시"] = pd.to_datetime(d["위반일시"], errors="coerce"); d["시"] = d["일시"].dt.hour; d["요일"] = d["일시"].dt.dayofweek
    z = pd.DataFrame(load_nosmoke(GU_NAME).drop(columns="geometry"))
    cc = pd.DataFrame(load_daycare().drop(columns="geometry")); cc = cc[cc["시군구"] == GU_NAME]
    bs = pd.read_excel(find(F["bus"]), dtype=str)
    def zone(n): r = z[z["금연구역명"] == n].iloc[0]; return float(r["위도"]), float(r["경도"])
    def care(n): r = cc[cc["어린이집명"] == n].iloc[0]; return float(r["위도"]), float(r["경도"])
    def bus(n): r = bs[bs["정류소명"] == n].iloc[0]; return float(r["Y좌표"]), float(r["X좌표"])
    RULES = [  # (패턴, 위치이름, 유형, 좌표) — 위에서부터 먼저 맞는 규칙
        (r"풀무원|수서역\)|\(수서역", "수서 풀무원어린이집", "어린이집", lambda: care("풀무원어린이집")),
        (r"보미나", "보미나어린이집", "어린이집", lambda: care("보미나어린이집")),
        (r"도곡중|세브란스", "도곡중 금연거리", "학교", lambda: zone("도곡중학교 주변 강남세브란스병원 후문 입구 전체")),
        (r"영동대로|코엑스", "영동대로 코엑스 주변", "금연거리", lambda: zone("영동대로 코엑스 주변")),
        (r"강남대로|미진", "강남대로 금연거리", "금연거리", lambda: zone("강남대로 동측")),
        (r"단대부고", "단대부고", "학교", lambda: bus("단대부고.대치아이파크아파트")),
        (r"논현초", "논현초등학교", "학교", lambda: zone("서울논현초등학교")),
        (r"도곡초", "도곡초등학교", "학교", lambda: zone("서울도곡초등학교")),
        (r"삼성역", "삼성역", "지하철역", lambda: zone("삼성역")),
    ]
    names, types, lat, lon = [], [], [], []
    for s in d["장소"]:
        for pat, nm, tp, fn in RULES:
            if re.search(pat, s):
                try: a, b = fn()
                except Exception: a = b = None
                names.append(nm); types.append(tp); lat.append(a); lon.append(b); break
        else:
            names.append(None); lat.append(None); lon.append(None)
            types.append("어린이집" if "어린이집" in s else "기타")
    d["위치이름"], d["장소유형"], d["위도"], d["경도"] = names, types, lat, lon
    return d


# ═════════════════════════ 머신러닝 공통 ═════════════════════════
def model_features(df):
    return [c for c in FEATURES if c in df.columns and c not in LEAK]


def prepare_classifier(classifier, scale=False):
    """모델의 fit에 전달된 학습 행으로만 결측값과 표준화 기준을 계산한다."""
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    imputer = SimpleImputer(strategy="median", keep_empty_features=True).set_output(transform="pandas")
    scaler = StandardScaler().set_output(transform="pandas") if scale else "passthrough"
    return make_pipeline(imputer, scaler, classifier)


def label_nodes(nodes, places):
    """가장 가까운 적발 장소까지의 거리로 정답과 거리 등급을 만든다."""
    from scipy.spatial import cKDTree

    located = places.dropna(subset=["위도", "경도"])
    if located.empty:
        raise ValueError("정답을 만들 수 있는 꽁초 적발 장소 좌표가 없습니다.")
    node_xy = xy_m(nodes["위도"], nodes["경도"])
    place_xy = xy_m(located["위도"], located["경도"])
    distance, _ = cKDTree(place_xy).query(node_xy)
    levels = pd.cut(distance, [-np.inf, HIGH_R, MEDIUM_R, LABEL_R, np.inf],
                    labels=DISTANCE_RISK_LEVELS)

    counts = np.zeros(len(nodes))
    nearby = cKDTree(node_xy).query_ball_point(place_xy, LABEL_R)
    for indices, count in zip(nearby, located["적발건수"]):
        counts[indices] += count

    return pd.DataFrame({
        "정답": (distance <= LABEL_R).astype(int),
        "최근접_적발거리_m": distance,
        "적발거리_위험등급": levels,
        LABEL_COUNT_COLUMN: counts,
    }, index=nodes.index)


def summarize_distance_risk(data):
    counts = data["적발거리_위험등급"].value_counts().reindex(DISTANCE_RISK_LEVELS, fill_value=0)
    return pd.DataFrame({
        "최근접 적발 거리": [
            f"{HIGH_R}m 이내", f"{HIGH_R}m 초과~{MEDIUM_R}m 이내",
            f"{MEDIUM_R}m 초과~{LABEL_R}m 이내", f"{LABEL_R}m 초과",
        ],
        "적발거리_위험등급": DISTANCE_RISK_LEVELS,
        "정답": [1, 1, 1, 0],
        "지점수": counts.to_numpy(),
    })


def spatial_blocks(nodes, size=1000):
    P = xy_m(nodes["위도"], nodes["경도"])
    return (P[:, 0] // size).astype(int).astype(str) + "_" + (P[:, 1] // size).astype(int).astype(str)


def top_capture(y, s, k=0.10):
    o = np.argsort(-np.asarray(s))[: max(1, int(len(s) * k))]
    return np.asarray(y)[o].sum() / max(1, np.asarray(y).sum())


def save_risk_maps(df, hourly, FE, p, test_predictions):
    """모델 예측을 기존 보행 지점·시간대별 격자 CSV 형식으로 저장한다."""
    df["위험확률"] = p.round(4)
    df["위험점수"] = (pd.Series(p).rank(pct=True) * 100).round(1)          # 강남구 안 순위(0~100)
    df["위험등급"] = pd.cut(df["위험점수"], [-1, 50, 70, 90, 100], labels=["보통", "약간 높음", "높음", "매우 높음(상위10%)"])
    df["시험셋_예측"] = test_predictions.round(4)
    keep = ["노드 ID", "격자ID", "위도", "경도", "위험확률", "위험점수", "위험등급", "시험셋_예측", "정답"]
    keep += LABEL_DETAIL_COLUMNS + FE
    save(df[keep], "1_위험지도_지점.csv")

    # ── 시간대별 격자 위험: 격자 평균 위험점수 × (그 시간 생활인구 / 하루 최대 생활인구) ──
    g = df.groupby("격자ID")["위험점수"].mean()
    h = hourly.reindex(g.index)
    share = h.div(h.max(axis=1), axis=0)
    hr = share.mul(g, axis=0).round(1)
    hr.columns = [f"{int(float(c))}시" for c in hr.columns]
    hr = hr.reset_index().rename(columns={"index": "격자ID"})
    import geopandas as gpd     # 지도 그리기용: 격자 네 모서리 위경도
    b = gpd.GeoSeries([grid_polygon(c) for c in hr["격자ID"]], crs=CRS_M).to_crs(4326).bounds.round(6)
    hr.insert(1, "서_경도", b["minx"].values)
    hr.insert(2, "남_위도", b["miny"].values)
    hr.insert(3, "동_경도", b["maxx"].values)
    hr.insert(4, "북_위도", b["maxy"].values)
    save(hr, "1_위험지도_격자시간대.csv")
