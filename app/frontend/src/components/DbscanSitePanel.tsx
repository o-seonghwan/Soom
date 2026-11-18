import type { DbscanCandidate, DbscanSitesResponse } from "../types/dbscan";

interface DbscanSitePanelProps {
  data: DbscanSitesResponse | null;
  loading: boolean;
  error: string;
  selectedCluster: string;
  onClusterChange: (id: string) => void;
  onFocus: (candidate: DbscanCandidate) => void;
  onReload: () => void;
}

/**
 * Embedded in the administrator-only local-government analysis dashboard.
 * The input CSV contains a representative violation location, not the
 * candidate's geocoded street address. Never label that as an exact site address.
 */
export default function DbscanSitePanel({
  data, loading, error, selectedCluster, onClusterChange, onFocus, onReload,
}: DbscanSitePanelProps) {
  const candidates = data?.candidates.filter(candidate =>
    !selectedCluster || candidate.clusterId === selectedCluster
  ) ?? [];

  return (
    <section aria-label="DBSCAN 흡연시설 입지 후보" className="space-y-4">
      <header>
        <h3 className="text-lg font-bold text-slate-900">흡연시설 입지 추천 후보</h3>
        <p className="mt-1 text-xs text-slate-500">
          담배꽁초 적발 집중지 주변의 후보 위치 · 실제 설치 확정 아님
        </p>
      </header>

      {loading && <p role="status" className="text-sm text-slate-600">입지 후보 데이터를 불러오는 중...</p>}
      {error && (
        <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <p>{error}</p>
          <button type="button" onClick={onReload}
            className="mt-2 rounded-lg border border-amber-400 px-3 py-1 text-xs font-bold">다시 불러오기</button>
        </div>
      )}

      {data && !loading && (
        <>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-sm font-bold text-emerald-900">추천 후보</p>
            <p className="mt-1 text-3xl font-bold text-emerald-900">{data.summary.candidateCount}곳</p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-bold text-slate-700" htmlFor="dbscan-site-area">
              적발 집중지 선택
            </label>
            <select id="dbscan-site-area" value={selectedCluster}
              onChange={event => onClusterChange(event.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
              <option value="">전체 적발 집중지</option>
              {data.clusters.map(cluster => (
                <option key={cluster.id} value={cluster.id}>
                  {cluster.representativePlace}
                </option>
              ))}
            </select>
          </div>

          {candidates.length === 0 ? (
            <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
              해당 적발 집중지에는 1차 입지 조건을 통과한 후보가 없습니다.
              아래 제외 기준을 확인하세요.
            </p>
          ) : (
            <div className="space-y-2">
              {candidates.map(candidate => (
                <div key={candidate.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3">
                  <div>
                    <p className="font-semibold text-slate-900">{candidate.representativePlace}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      적발 집중지 주변 {Math.round(candidate.walkingDistanceM)}m
                    </p>
                  </div>
                  <button type="button" onClick={() => onFocus(candidate)}
                    className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white">
                    지도에서 보기
                  </button>
                </div>
              ))}
              <p className="text-xs text-slate-500">
                표시된 장소명은 적발 집중지의 대표 장소입니다. 후보 지점의 정확한 주소는
                분석 CSV에 없어 지도 위치로 확인해야 합니다.
              </p>
            </div>
          )}

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h4 className="font-bold text-slate-900">후보 지점은 어떻게 선정하나요?</h4>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              담배꽁초 적발 기록이 많이 모인 곳을 먼저 찾고, 그 주변에서
              접근 가능하면서 비흡연자 노출을 비교적 줄일 수 있을 것으로
              추정되는 보행 지점을 골랐습니다.
            </p>
            <ol className="mt-3 list-inside list-decimal space-y-3 text-sm leading-6 text-slate-700">
              <li>
                <strong>적발 집중지 탐색:</strong> DBSCAN으로 서로 30m 이내의
                적발 장소를 묶고, 적발 건수를 가중치로 반영해 최소 30건
                수준의 집중지를 찾습니다.
              </li>
              <li>
                <strong>걸어서 접근할 수 있는 곳만 탐색:</strong> 집중지에서
                보행 네트워크를 따라 200m 이내에 있는 지점만 후보로 검토합니다.
                직선거리가 가까워도 실제 보행 경로가 200m를 넘으면 제외합니다.
              </li>
              <li>
                <strong>민감시설·금연구역 인근 제외:</strong> 어린이집 30m 이내,
                학교정화구역 50m 이내, 공원·공공청사 등의 금연구역,
                지하철 출입구·택시승강장 10m 이내, 주유소·가스충전소 주변 약 15m,
                지정 금연거리의 해당 구간은 후보에서 제외합니다.
                금연구역은 원자료의 구분과 면적·거리 근사 조건을 사용합니다.
              </li>
              <li>
                <strong>집중지 자체가 민감시설에 가까우면 설치보다 단속:</strong>
                적발 집중지 중심이 어린이집 30m 이내이거나 학교 관련 제외구역에
                있으면, 주변에 후보 지점이 있더라도 단속·계도를 우선합니다.
              </li>
              <li>
                <strong>남은 후보의 우선순위:</strong> 가상의 보행 흐름을 이용해
                반경 21m 안의 간접흡연 노출 대리값이 작은 지점을 우선하고,
                값이 같으면 보행 접근거리가 짧은 곳을 우선합니다.
                후보 간 간격은 30m를 넘도록 하고 집중지당 최대 3곳을 선정합니다.
              </li>
            </ol>
            <p className="mt-3 rounded-lg bg-white p-3 text-xs leading-5 text-slate-600">
              <strong>즉,</strong> 민감시설 주변이거나 금연구역에 해당하는 곳,
              집중지에서 걸어서 200m 안에 도달할 수 없는 곳은 1차 후보에서
              빠집니다. 조건에 맞는 지점이 전혀 없으면 추천 대신 단속·계도
              대상으로 남습니다.
            </p>
          </div>
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
            {data.disclaimer} 위 거리·영역 판정에는 분석용 근사와 가정이 포함됩니다.
            실제 법적 설치 가능 여부, 보도 폭, 건물 출입구, 소유권과 민원 등은
            지자체 현장 조사와 최신 규정 확인이 필요합니다.
          </p>
        </>
      )}
    </section>
  );
}
