"""강남구 DBSCAN 설정별 집중지와 부스 후보를 비교한다."""
import importlib.util
from itertools import product
from pathlib import Path

import pandas as pd

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C


def main():
    path = Path(__file__).with_name("4_B2G_흡연자_흡연부스후보.py")
    spec = importlib.util.spec_from_file_location("booth_model", path)
    booth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(booth)

    C.use_preprocessed_data()
    records = C.butt_records_with_xy().dropna(subset=["위도", "경도"]).copy()
    if records.empty:
        raise ValueError("군집 분석에 사용할 강남구 꽁초 적발 좌표가 없습니다.")
    locations = booth.group_locations(records)
    search = booth.prepare_booth_search()

    rows = []
    details = []
    print("<DBSCAN 반경과 최소 적발 건수 비교>")
    print("######################################################################")
    for eps_m, min_records in product([20, 30, 40, 50], [20, 30, 40]):
        labels, hotspots = booth.cluster_locations(locations, records, eps_m, min_records)
        candidates = booth.find_booth_candidates(hotspots, search)
        field = candidates.loc[candidates["판단"].eq("현장 검토 후보")]
        assigned = int(labels.loc[labels["집중지"].ge(0), "건수"].sum())
        rows.append({
            "반경_eps_m": eps_m,
            "최소_적발건수": min_records,
            "기존_설정": (eps_m, min_records) == (booth.EPS_M, booth.MIN_RECORDS),
            "집중지_수": len(hotspots),
            "군집_적발건수": assigned,
            "군집_포함률_pct": round(100 * assigned / len(records), 2),
            "군집_밖_적발건수": len(records) - assigned,
            "최대_군집반경_m": hotspots["반경_m"].max(),
            "최대_군집적발건수": hotspots["적발건수"].max(),
            "현장_검토_후보_배정건수": len(field),
            "고유_부스후보_수": len(field[["부스후보_위도", "부스후보_경도"]].drop_duplicates()),
            "단속_우선_집중지_수": candidates["판단"].eq("어린이집 인근 단속 우선 검토").sum(),
            "후보_없음_집중지_수": candidates["판단"].str.endswith("검토 후보 없음").sum(),
            "보호_대상_미확인_집중지_수": candidates["판단"].eq("보호 대상 자료 미확인").sum(),
        })
        details.append(candidates.assign(반경_eps_m=eps_m, 최소_적발건수=min_records))

    summary = pd.DataFrame(rows)
    C.save(summary, "4_DBSCAN_파라미터_비교.csv")
    detail = pd.concat(details, ignore_index=True)
    parameters = ["반경_eps_m", "최소_적발건수"]
    C.save(detail[parameters + booth.HOTSPOT_COLUMNS + booth.BOOTH_COLUMNS], "4_DBSCAN_설정별_집중지와_부스후보.csv")
    print(summary.to_string(index=False))
    print("######################################################################")


if __name__ == "__main__":
    main()
