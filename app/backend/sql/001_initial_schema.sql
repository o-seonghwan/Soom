
-- =====================================================
-- 13단계: PostgreSQL + PostGIS 초기 테이블
-- 대상 DB: do_not_lung
-- PostGIS 확장이 활성화되어 있어야 함
-- =====================================================


-- =====================================================
-- 1. 사용자 제보
-- =====================================================

CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    report_type VARCHAR(30) NOT NULL
        CHECK (
            report_type IN (
                'smoking',
                'cigarette_butt',
                'other'
            )
        ),

    location GEOMETRY(Point, 4326) NOT NULL,

    observed_at TIMESTAMPTZ NOT NULL,

    description TEXT NOT NULL DEFAULT '',

    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (
            status IN (
                'pending',
                'verified',
                'rejected'
            )
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    reviewed_at TIMESTAMPTZ,
    review_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_reports_location
ON public.reports
USING GIST (location);

CREATE INDEX IF NOT EXISTS idx_reports_status
ON public.reports (status);

CREATE INDEX IF NOT EXISTS idx_reports_observed_at
ON public.reports (observed_at);


-- =====================================================
-- 2. 위험도 스냅샷
-- =====================================================

CREATE TABLE IF NOT EXISTS public.risk_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source VARCHAR(30) NOT NULL
        CHECK (
            source IN (
                'mock',
                'model',
                'import'
            )
        ),

    version VARCHAR(100) NOT NULL,

    predicted_at TIMESTAMPTZ,

    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    description TEXT,

    UNIQUE (source, version, generated_at)
);


-- =====================================================
-- 3. 위치별 위험도
-- =====================================================

CREATE TABLE IF NOT EXISTS public.risk_locations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    snapshot_id BIGINT NOT NULL
        REFERENCES public.risk_snapshots(id)
        ON DELETE CASCADE,

    source_risk_id VARCHAR(100) NOT NULL,

    location GEOMETRY(Point, 4326) NOT NULL,

    score DOUBLE PRECISION NOT NULL
        CHECK (score BETWEEN 0 AND 100),

    radius_m DOUBLE PRECISION NOT NULL
        CHECK (radius_m > 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (snapshot_id, source_risk_id)
);

CREATE INDEX IF NOT EXISTS idx_risk_locations_location
ON public.risk_locations
USING GIST (location);

CREATE INDEX IF NOT EXISTS idx_risk_locations_snapshot
ON public.risk_locations (snapshot_id);


-- =====================================================
-- 4. 보행 링크별 위험도
-- =====================================================

CREATE TABLE IF NOT EXISTS public.risk_edge_scores (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    snapshot_id BIGINT NOT NULL
        REFERENCES public.risk_snapshots(id)
        ON DELETE CASCADE,

    -- 원본 GraphML의 (u, v, key)
    edge_u VARCHAR(100) NOT NULL,
    edge_v VARCHAR(100) NOT NULL,
    edge_key VARCHAR(100) NOT NULL,

    -- 점수 범위: 0~100
    score DOUBLE PRECISION NOT NULL
        CHECK (score BETWEEN 0 AND 100),

    normalized_risk DOUBLE PRECISION NOT NULL
        CHECK (normalized_risk BETWEEN 0 AND 1),

    -- 영향을 준 위험 위치 ID 목록
    source_risk_ids JSONB NOT NULL DEFAULT '[]'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (
        snapshot_id,
        edge_u,
        edge_v,
        edge_key
    )
);

CREATE INDEX IF NOT EXISTS idx_risk_edge_snapshot
ON public.risk_edge_scores (snapshot_id);

CREATE INDEX IF NOT EXISTS idx_risk_edge_nodes
ON public.risk_edge_scores (
    edge_u,
    edge_v,
    edge_key
);


-- =====================================================
-- 5. 초기 확인
-- =====================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'reports',
      'risk_snapshots',
      'risk_locations',
      'risk_edge_scores'
  )
ORDER BY table_name;
