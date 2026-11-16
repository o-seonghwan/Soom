"""
[준비] 꽁초 적발 장소 3,143곳에 VWorld로 좌표 붙이기 (1번 코드보다 먼저, .env 가 있는 PC에서 한 번)

- .env 의 VWORLD_API_KEY 를 읽습니다 (코드 폴더, 그 위 폴더, 다운로드 폴더 순서). 키는 출력하지 않습니다.
- 약 3,000곳 × 0.15초 ≈ 8~10분. 중간에 끊겨도 다시 실행하면 이어서 합니다 (결과/vworld_캐시_꽁초.csv).
- VWorld로 못 찾은 곳만 상가정보 주소로 한 번 더 찾습니다.
결과: 결과/정답_꽁초적발_장소좌표.csv  → 1~4번 코드가 이 파일을 씁니다.

실행: python 0_VWorld_좌표찾기.py
"""
import os, sys
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # 공통.py가 있는 code 폴더
import 공통 as C

if __name__ == "__main__":
    if not C.vworld_key() and not os.path.exists(C.out_path("vworld_캐시_꽁초.csv")):
        sys.exit("VWORLD_API_KEY를 찾지 못했습니다. .env 파일을 코드 폴더나 다운로드 폴더에 두세요.")
    p = C.out_path("정답_꽁초적발_장소좌표.csv")
    if os.path.exists(p):
        os.remove(p)      # 예전(로컬 방식) 정답 좌표는 지우고 새로 만듦. VWorld 응답 캐시는 남겨 둠
        C.log("예전 정답 좌표 파일을 지우고 새로 만듭니다.")
    P = C.butt_places(fresh=True)
    ok = P["위도"].notna()
    print(f"\n완료: 장소 {ok.sum():,}/{len(P):,}곳, 적발 {P.loc[ok, '적발건수'].sum():,}/{P['적발건수'].sum():,}건")
    print("방식별 장소 수:", P.loc[ok, "방식"].str.split(":").str[0].value_counts().to_dict())
    print("\n못 찾은 장소 상위 10곳:\n" + P[~ok].head(10)[["장소", "적발건수"]].to_string(index=False))
    # 팀원 EDA 데이터와 합치기용: 담배꽁초 적발 기록 한 줄마다 좌표 (원본 열 + 좌표 열)
    d = C.load_butt_records().reset_index(drop=True)
    d.insert(0, "꽁초기록번호", d.index + 1)
    m = d.merge(P[["장소", "위도", "경도", "방식"]].rename(columns={"방식": "좌표방식"}), on="장소", how="left")
    m["좌표있음"] = m["위도"].notna().astype(int)
    m = m.drop(columns=["일시"]).rename(columns={"장소": "장소_정리"})
    C.save(m, "강남_꽁초적발_전체기록_좌표.csv")
    print(f"\n전체 기록 {len(m):,}건 중 좌표 있음 {int(m['좌표있음'].sum()):,}건 → 결과/강남_꽁초적발_전체기록_좌표.csv")
    print("다음: 결과 폴더의 특성표는 그대로 두고 1번 코드를 다시 실행하세요.")
