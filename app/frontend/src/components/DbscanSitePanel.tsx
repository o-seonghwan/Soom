import type { DbscanCandidate, DbscanSitesResponse } from "../types/dbscan";

interface DbscanSitePanelProps {
  data: DbscanSitesResponse | null;
  loading: boolean;
  error: string;
  selectedCluster: string;
  onClusterChange: (id: string) => void;
  onFocus: (candidate: DbscanCandidate) => void;
  onReload: () => void;
  onClose: () => void;
}

export default function DbscanSitePanel({
  data, loading, error, selectedCluster, onClusterChange,
  onFocus, onReload, onClose,
}: DbscanSitePanelProps) {
  const candidates = data?.candidates.filter(candidate =>
    !selectedCluster || candidate.clusterId === selectedCluster
  ) ?? [];
  return (
    <section
      aria-label="DBSCAN 흡연시설 입지 후보"
      className="absolute left-3 top-[64px] z-[1100] flex max-h-[min(72dvh,calc(100%-85px))] w-[min(420px,calc(100%-24px))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white/95 shadow-xl"
    >
      <header className="flex items-start justify-between border-b border-slate-100 px-4 py-3">
        <div>
          <h2 className="font-bold text-slate-900">DBSCAN 흡연시설 입지 후보</h2>
          <p className="mt-1 text-xs text-slate-500">담배꽁초 적발 집중지 기반 · 현장 검토 전</p>
        </div>
        <button type="button" onClick={onClose} aria-label="입지 후보 패널 닫기"
          className="rounded-lg border px-2 py-1 text-sm text-slate-600">닫기 ×</button>
      </header>

      <div className="space-y-3 overflow-y-auto p-4">
        {loading && <p role="status" className="text-sm text-slate-600">분석 결과를 불러오는 중...</p>}
        {error && (
          <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <p>{error}</p>
            <button type="button" onClick={onReload}
              className="mt-2 rounded-lg border border-amber-400 px-3 py-1 text-xs font-bold">다시 불러오기</button>
          </div>
        )}
        {data && !loading && (
          <>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                {name: "집중 군집", value: data.summary.clusterCount},
                {name: "검토 대상", value: data.summary.reviewClusterCount},
                {name: "추천 후보", value: data.summary.candidateCount},
              ].map(item => (
                <div key={item.name} className="rounded-lg bg-slate-100 p-2">
                  <p className="text-[11px] text-slate-500">{item.name}</p>
                  <p className="text-lg font-bold text-slate-900">{item.value}</p>
                </div>
              ))}
            </div>
            <div className="rounded-lg bg-emerald-50 p-3 text-xs leading-5 text-emerald-900">
              <p className="font-bold">분석 설정</p>
              <p>DBSCAN 반경 {data.parameters.epsM}m · 최소 적발 건수 {data.parameters.minRecords}건 ·
                집중지에서 보행 {data.parameters.accessLimitM}m 이내 · 군집당 최대 {data.parameters.maxCandidatesPerCluster}곳</p>
            </div>
            <label className="block text-xs font-bold text-slate-700" htmlFor="dbscan-cluster-filter">
              집중 군집 선택
            </label>
            <select id="dbscan-cluster-filter" value={selectedCluster}
              onChange={event => onClusterChange(event.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
              <option value="">전체 후보</option>
              {data.clusters.map(cluster => (
                <option key={cluster.id} value={cluster.id}>
                  군집 {cluster.id} · {cluster.representativePlace} ({cluster.recordCount}건)
                </option>
              ))}
            </select>
            {candidates.length === 0 ? (
              <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">
                이 조건에 해당하는 입지 후보가 없습니다. 군집 판정 또는 제외 조건을 확인하세요.
              </p>
            ) : (
              <ol className="space-y-2">
                {candidates.map(candidate => (
                  <li key={candidate.id} className="rounded-xl border border-slate-200 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-bold text-slate-900">
                          군집 {candidate.clusterId} · {candidate.rank}순위 후보
                        </p>
                        <p className="mt-1 text-xs text-slate-600">{candidate.representativePlace}</p>
                      </div>
                      <button type="button" onClick={() => onFocus(candidate)}
                        className="shrink-0 rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-bold text-white">
                        지도에서 보기
                      </button>
                    </div>
                    <p className="mt-2 text-xs text-slate-700">
                      보행 접근거리 {candidate.walkingDistanceM}m · {candidate.recommendedType}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      보행 흐름 백분위 {candidate.pedestrianFlowPercentile?.toFixed(1) ?? "미산정"} ·
                      모델 OOF 확률 {candidate.riskProbabilityOOF?.toFixed(3) ?? "미산정"}
                    </p>
                  </li>
                ))}
              </ol>
            )}
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
              {data.disclaimer} 금연구역 제한·보도 폭·건물 출입구·토지 소유권 등은
              담당 기관의 현장·법규 확인이 필요합니다. 적발 집중지 ≠ 흡연시설 설치 가능 지점입니다.
            </p>
          </>
        )}
      </div>
    </section>
  );
}
