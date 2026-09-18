CREATE TABLE IF NOT EXISTS notices (
    notice_id TEXT PRIMARY KEY,
    portal_id TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    estimated_value NUMERIC,
    closing_date DATE
);

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notice_opportunity (
    notice_id TEXT PRIMARY KEY REFERENCES notices(notice_id),
    opportunity_id BIGINT NOT NULL REFERENCES opportunities(opportunity_id)
);

CREATE TABLE IF NOT EXISTS lsh_buckets (
    band INTEGER NOT NULL,
    bucket_hash TEXT NOT NULL,
    notice_id TEXT NOT NULL REFERENCES notices(notice_id),
    PRIMARY KEY (band, bucket_hash, notice_id)
);

CREATE INDEX IF NOT EXISTS idx_lsh_bucket_lookup
ON lsh_buckets (band, bucket_hash);

CREATE INDEX IF NOT EXISTS idx_notice_opportunity_opportunity
ON notice_opportunity (opportunity_id);
