
import os, re, glob, time, hashlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# QUESTION 2 - SECTIONS A and B/C/E
# Run this file from the data_2\data_2 folder.
#
# Required packages:
#   pip install pandas numpy matplotlib datasketch
# ============================================================

BASE = "."
NOTICE_DIR = os.path.join(BASE, "notices")
LABEL_FILE = os.path.join(BASE, "labelled_pairs.csv")
OUT = os.path.join(BASE, "q2_results")
os.makedirs(OUT, exist_ok=True)

NODAL = {"P001","P002","P003","P004","P005","P006"}

def clean_text(x):
    x = str(x).lower()
    x = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", x))
    return x.strip()

def strip_nodal_boilerplate(row):
    s = clean_text(str(row["title"]) + " " + str(row["body"]))
    if row["portal_id"] in NODAL:
        m = re.search(r"notice details follow", s)
        if m:
            s = s[m.end():]
        else:
            m = re.search(r"name of work", s)
            if m and m.start() < 1800:
                s = s[m.start():]
    return clean_text(s)

def word_shingles(text, k=3):
    w = text.split()
    return {" ".join(w[i:i+k]) for i in range(max(0, len(w)-k+1))}

def char_shingles(text, k=5):
    return {text[i:i+k] for i in range(max(0, len(text)-k+1))}

def jaccard(a, b):
    u = a | b
    return len(a & b) / len(u) if u else 1.0

print("="*70)
print("QUESTION 2 - DATA LOAD")
print("="*70)

files = sorted(glob.glob(os.path.join(NOTICE_DIR, "part-*.csv")))
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
df = df.set_index("notice_id")

pairs = pd.read_csv(LABEL_FILE)

print("Notices:", len(df))
print("Portals:", df["portal_id"].nunique())
print("Labelled pairs:", len(pairs))
print(pairs["label"].value_counts())
print()

# ------------------------------------------------------------
# A1: corpus inspection
# ------------------------------------------------------------
df["body_length"] = df["body"].fillna("").astype(str).str.len()
df["title_length"] = df["title"].fillna("").astype(str).str.len()

inspection = pd.DataFrame({
    "metric": [
        "notices", "portals", "missing_total",
        "body_mean", "body_median", "body_min", "body_max"
    ],
    "value": [
        len(df), df["portal_id"].nunique(), int(df.isna().sum().sum()),
        df["body_length"].mean(), df["body_length"].median(),
        df["body_length"].min(), df["body_length"].max()
    ]
})
inspection.to_csv(os.path.join(OUT, "A1_inspection.csv"), index=False)

nodal_df = df[df["portal_id"].isin(NODAL)]
other_df = df[~df["portal_id"].isin(NODAL)]
portal_summary = pd.DataFrame({
    "group": ["P001-P006", "other portals"],
    "count": [len(nodal_df), len(other_df)],
    "mean_body_length": [nodal_df.body_length.mean(), other_df.body_length.mean()],
    "median_body_length": [nodal_df.body_length.median(), other_df.body_length.median()]
})
portal_summary.to_csv(os.path.join(OUT, "A1_nodal_vs_other.csv"), index=False)

# ------------------------------------------------------------
# A2: word-3 vs char-5 on all 900 labels
# ------------------------------------------------------------
print("="*70)
print("A2 - REPRESENTATION COMPARISON")
print("="*70)

texts = (df["title"].fillna("") + " " + df["body"].fillna("")).map(clean_text)
ids = set(pairs.notice_id_a) | set(pairs.notice_id_b)

word_cache = {i: word_shingles(texts.loc[i], 3) for i in ids}
char_cache = {i: char_shingles(texts.loc[i], 5) for i in ids}

pairs["word3"] = [
    jaccard(word_cache[a], word_cache[b])
    for a,b in zip(pairs.notice_id_a, pairs.notice_id_b)
]
pairs["char5"] = [
    jaccard(char_cache[a], char_cache[b])
    for a,b in zip(pairs.notice_id_a, pairs.notice_id_b)
]

summary = pairs.groupby("label")[["word3","char5"]].agg(
    ["count","mean","median","min","max"]
)
summary.to_csv(os.path.join(OUT, "A2_representation_summary.csv"))

word_sep = pairs[pairs.label=="same"].word3.mean() - pairs[pairs.label=="different"].word3.mean()
char_sep = pairs[pairs.label=="same"].char5.mean() - pairs[pairs.label=="different"].char5.mean()

print(summary)
print("\nWord-3 mean separation:", round(word_sep,4))
print("Char-5 mean separation:", round(char_sep,4))

# ------------------------------------------------------------
# A3: remove nodal boilerplate and re-measure
# ------------------------------------------------------------
print("\nA3 - NODAL BOILERPLATE TEST")

cleaned2 = {i: strip_nodal_boilerplate(df.loc[i]) for i in ids}
word2_cache = {i: word_shingles(cleaned2[i], 3) for i in ids}
pairs["word3_nodal_stripped"] = [
    jaccard(word2_cache[a], word2_cache[b])
    for a,b in zip(pairs.notice_id_a, pairs.notice_id_b)
]

strip_summary = pairs.groupby("label")["word3_nodal_stripped"].agg(
    ["count","mean","median","min","max"]
)
strip_summary.to_csv(os.path.join(OUT, "A3_boilerplate_summary.csv"))

strip_sep = (
    pairs[pairs.label=="same"].word3_nodal_stripped.mean()
    - pairs[pairs.label=="different"].word3_nodal_stripped.mean()
)

print(strip_summary)
print("Stripped mean separation:", round(strip_sep,4))

# Required two example pairs
examples = pairs.iloc[[0,1]][
    ["notice_id_a","notice_id_b","label","word3","char5","word3_nodal_stripped"]
]
examples.to_csv(os.path.join(OUT, "A_required_examples.csv"), index=False)

# ------------------------------------------------------------
# B: MinHash error using datasketch
# ------------------------------------------------------------
print("\n" + "="*70)
print("B - MINHASH")
print("="*70)

try:
    from datasketch import MinHash, MinHashLSH
except ImportError:
    print("datasketch is not installed.")
    print("Run: pip install datasketch")
    raise

# Use the selected representation: word-3 shingles after portal boilerplate removal.
all_cleaned = {i: strip_nodal_boilerplate(df.loc[i]) for i in df.index}

def make_minhash(text, num_perm):
    m = MinHash(num_perm=num_perm, seed=20240917)
    for sh in word_shingles(text, 3):
        m.update(sh.encode("utf-8"))
    return m

sizes = [32, 64, 128]
mh_results = []

# Only build signatures for notices appearing in the trusted labelled set.
label_ids = sorted(set(pairs.notice_id_a) | set(pairs.notice_id_b))

for nperm in sizes:
    print(f"Building {nperm}-permutation signatures for labelled notices...")
    sig = {i: make_minhash(all_cleaned[i], nperm) for i in label_ids}

    errs = []
    estimates = []
    exacts = []

    for a,b in zip(pairs.notice_id_a, pairs.notice_id_b):
        exact = jaccard(
            word_shingles(all_cleaned[a],3),
            word_shingles(all_cleaned[b],3)
        )
        est = sig[a].jaccard(sig[b])
        exacts.append(exact)
        estimates.append(est)
        errs.append(abs(exact-est))

    mh_results.append({
        "num_perm": nperm,
        "MAE": np.mean(errs),
        "RMSE": np.sqrt(np.mean(np.square(np.array(errs)))),
        "max_abs_error": np.max(errs),
        "p95_abs_error": np.percentile(errs,95)
    })

mh_df = pd.DataFrame(mh_results)
mh_df.to_csv(os.path.join(OUT, "B_minhash_error.csv"), index=False)
print(mh_df.to_string(index=False))

plt.figure()
plt.plot(mh_df["num_perm"], mh_df["MAE"], marker="o")
plt.xlabel("MinHash signature size (permutations)")
plt.ylabel("Mean absolute error")
plt.title("MinHash estimation error")
plt.grid(True)
plt.savefig(os.path.join(OUT, "B_minhash_error.png"), bbox_inches="tight")
plt.close()

# Choose smallest tested signature. The report should state the required
# error target explicitly and compare it with these measured values.
chosen_perm = 128
print("\nChosen working size for C:", chosen_perm)

# ------------------------------------------------------------
# C: LSH candidate retrieval using trusted SAME labelled pairs
# ------------------------------------------------------------
print("\n" + "="*70)
print("C - LSH CANDIDATE RETRIEVAL")
print("="*70)

# Build signatures for all 12,000 notices at the chosen size.
t0 = time.perf_counter()
signatures = {}
for idx, notice_id in enumerate(df.index):
    signatures[notice_id] = make_minhash(all_cleaned[notice_id], chosen_perm)
    if (idx+1) % 1000 == 0:
        print("  signatures:", idx+1)

print("Signature build seconds:", round(time.perf_counter()-t0,2))

# Evaluate several LSH thresholds. These are retrieval configurations,
# not final duplicate-decision thresholds.
lsh_rows = []
for lsh_threshold in [0.40, 0.50, 0.60, 0.70]:
    print("Testing LSH threshold:", lsh_threshold)
    lsh = MinHashLSH(threshold=lsh_threshold, num_perm=chosen_perm)
    for notice_id, sig in signatures.items():
        lsh.insert(notice_id, sig)

    retrieved = 0
    candidate_total = 0

    for a,b in zip(pairs.notice_id_a, pairs.notice_id_b):
        cands = lsh.query(signatures[a])
        candidate_total += len(cands)
        if b in cands:
            retrieved += 1

    lsh_rows.append({
        "lsh_threshold": lsh_threshold,
        "same_pairs": int((pairs.label=="same").sum()),
        "same_pairs_retrieved": retrieved,
        "same_pair_recall": retrieved / int((pairs.label=="same").sum()),
        "avg_candidates_for_labelled_A": candidate_total / len(pairs)
    })

lsh_df = pd.DataFrame(lsh_rows)
lsh_df.to_csv(os.path.join(OUT, "C_lsh_configurations.csv"), index=False)
print(lsh_df.to_string(index=False))

# Use the 0.40 LSH configuration for hotspot analysis.
lsh = MinHashLSH(threshold=0.40, num_perm=chosen_perm)
for notice_id, sig in signatures.items():
    lsh.insert(notice_id, sig)

# Retrieval probability vs exact similarity, using SAME labelled pairs.
curve = []
same_pairs = pairs[pairs.label=="same"].copy()

for a,b in zip(same_pairs.notice_id_a, same_pairs.notice_id_b):
    exact = jaccard(
        word_shingles(all_cleaned[a],3),
        word_shingles(all_cleaned[b],3)
    )
    hit = b in lsh.query(signatures[a])
    curve.append((exact, hit))

curve_df = pd.DataFrame(curve, columns=["exact_similarity","retrieved"])
bins = np.arange(0.1, 1.01, 0.1)
curve_df["similarity_bin"] = pd.cut(
    curve_df["exact_similarity"], bins=bins, include_lowest=True
)
curve_summary = curve_df.groupby("similarity_bin", observed=True).agg(
    pairs=("retrieved","size"),
    retrieval_probability=("retrieved","mean")
).reset_index()
curve_summary.to_csv(os.path.join(OUT, "C_retrieval_curve.csv"), index=False)

plt.figure()
plt.plot(
    curve_df["exact_similarity"],
    curve_df["retrieved"].astype(int),
    "o",
    alpha=0.25
)
plt.xlabel("Exact Word-3 Jaccard similarity")
plt.ylabel("Retrieved by LSH (0/1)")
plt.title("LSH retrieval against exact similarity")
plt.grid(True)
plt.savefig(os.path.join(OUT, "C_retrieval_scatter.png"), bbox_inches="tight")
plt.close()

# ------------------------------------------------------------
# C2: final duplicate threshold candidates on labelled pairs
# ------------------------------------------------------------
# This is a sensitivity table. The final threshold must be chosen using
# the business cost ratio and the trusted labelled sample.
print("\nC2 - FINAL SIMILARITY THRESHOLD SENSITIVITY")
threshold_rows = []
for t in np.arange(0.30, 0.71, 0.01):
    pred = pairs["word3_nodal_stripped"] >= t
    y = pairs["label"].eq("same")
    tp = int((pred & y).sum())
    fp = int((pred & ~y).sum())
    fn = int((~pred & y).sum())
    tn = int((~pred & ~y).sum())
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    threshold_rows.append({
        "threshold": round(float(t),2),
        "TP":tp,"FP":fp,"FN":fn,"TN":tn,
        "precision":precision,"recall":recall
    })

threshold_df = pd.DataFrame(threshold_rows)
threshold_df.to_csv(os.path.join(OUT, "C_similarity_thresholds.csv"), index=False)

# ------------------------------------------------------------
# E: hotspot distribution
# ------------------------------------------------------------
print("\n" + "="*70)
print("E - CANDIDATE WORK DISTRIBUTION")
print("="*70)

t0 = time.perf_counter()
candidate_counts = []
for notice_id in df.index:
    candidate_counts.append(len(lsh.query(signatures[notice_id])) - 1)

candidate_df = pd.DataFrame({
    "notice_id": df.index,
    "portal_id": df["portal_id"].values,
    "candidate_count": candidate_counts
})
candidate_df.to_csv(os.path.join(OUT, "E_candidate_counts.csv"), index=False)

print("Candidate-query seconds:", round(time.perf_counter()-t0,2))
print(candidate_df["candidate_count"].describe())

portal_work = candidate_df.groupby("portal_id").agg(
    notices=("notice_id","size"),
    total_candidates=("candidate_count","sum"),
    mean_candidates=("candidate_count","mean"),
    max_candidates=("candidate_count","max")
).sort_values("total_candidates", ascending=False)

portal_work.to_csv(os.path.join(OUT, "E_portal_work.csv"))

top = candidate_df.nlargest(25, "candidate_count")
top.to_csv(os.path.join(OUT, "E_top_25_hotspots.csv"), index=False)

# Mitigation experiment: cap candidate list at 25.
# This deliberately trades recall for bounded work.
cap = 25
candidate_df["capped_candidates"] = candidate_df["candidate_count"].clip(upper=cap)
before = candidate_df["candidate_count"].sum()
after = candidate_df["capped_candidates"].sum()

pd.DataFrame([{
    "cap": cap,
    "candidate_work_before": int(before),
    "candidate_work_after": int(after),
    "reduction_fraction": 1 - after/before if before else 0
}]).to_csv(os.path.join(OUT, "E_cap25_effect.csv"), index=False)

print("\nTop portal work:")
print(portal_work.head(10).to_string())
print("\nCandidate work before cap:", int(before))
print("Candidate work after cap:", int(after))

print("\nDONE.")
print("All result tables/graphs are in:", OUT)
