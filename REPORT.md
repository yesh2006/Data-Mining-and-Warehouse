# TENDER DEDUPLICATION — QUESTION 2

## SECTION A

### A — Define Similarity
The corpus contains 12,000 notices from 260 portals with no missing values. The labelled sample
contains 900 pairs: 279 SAME and 621 DIFFERENT.

Word-3 shingles and Character-5 shingles were compared using Jaccard similarity. On all 900 labelled
pairs, Word-3 produced 0.644673 mean similarity for SAME pairs and 0.253793 for DIFFERENT pairs,
a separation of 0.3909. Character-5 produced 0.708862 and 0.430489 respectively, separation 0.2784.
Word-3 was adopted.

The required concrete examples were:
- SAME: N010018 vs N010020, with Word-3 = 0.2217 and Character-5 = 0.3049.
- DIFFERENT: N007876 vs N008565, with Word-3 = 0.1872 and Character-5 = 0.3864.

The examples also show why portal/reference/date formatting and repeated portal boilerplate should
not dominate the similarity decision.

### B — MinHash
An engineering requirement of MAE <= 0.03 was used for the approximation experiment.
Measured MAE was 0.0504 (32), 0.0336 (64), and 0.0285 (128). Therefore 128 permutations was the
smallest tested configuration meeting the requirement.

### C — LSH
Using 128 permutations, measured SAME-pair recall was 82.08% at threshold 0.4, 69.89% at 0.5,
48.39% at 0.6, and 38.71% at 0.7. The chosen candidate-stage configuration is threshold 0.4,
with 32 bands and 4 rows.

A 100:1 false-merge-to-missed-duplicate cost ratio is used as an explicit engineering risk model
for the operating point. The C survival curve is shown as the theoretical LSH survival probability
for b=32, r=4; the measured 82.08% SAME-pair recall is reported separately.

## SECTION B

### D — Database
The persistent relational design uses notices, opportunities, notice_opportunity and lsh_buckets.
The `(band, bucket_hash)` B-tree index is used for lookup.

Measured PostgreSQL query:
- Indexed: Index Scan using idx_lsh_bucket_lookup — 0.046 ms.
- Forced sequential scan: Seq Scan on lsh_buckets — 0.779 ms.
- The indexed test was approximately 16.9 times faster.

The opportunity mapping uses a persistent opportunity_id rather than relying on an in-memory Python
object.

### E — Hotspot and Mitigation
At threshold 0.4, full-corpus candidate work was 19,375,358. Candidate counts were highly uneven,
with a maximum of 4,563 candidates for one notice. P094, P002, P005 and P001 were among the largest
contributors in the displayed portal totals.

Capping candidate lists at 25 reduced candidate work to 299,573, a measured 98.45% reduction.
This bounds the pathological candidate workload.

The supplied E terminal run did not print before/after wall-clock timings, so no unsupported runtime
value is stated.
