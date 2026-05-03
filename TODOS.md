# TODOS

Deferred work captured during /plan-eng-review on 2026-05-03.
Each item includes context to pick up without needing to reconstruct the reasoning.

---

## TODO-1 — SO survey column mapping for pre-2015 CSVs

**What:** Add a `{year: column_name}` mapping dict to `ingest_so.py` so pre-2015 SO survey CSVs resolve to the closest equivalent of the "Admired %" column.

**Why:** The plan locks in "Admired %" (love-not-dread) as the SO sub-score signal. SO surveys before 2015 used different column names (`Liked`, `Loved`, or no equivalent). Without this mapping, 2011–2014 CSVs either silently skip the SO sub-score or crash — the slider loses 4 years of SO signal and those rows are permanently `partial=True`.

**Current state:** `ingest_so.py` doesn't exist yet. Add the mapping table at the top of the script when building it in Week 2. Requires a one-time check of the 2011–2014 CSV headers (downloadable from `survey.stackoverflow.co/datasets`).

**Effort:** ~30 lines in `ingest_so.py`. Low risk. Check headers for: 2011 (`tech_use`), 2012 (`tech_use`), 2013 (`have_tech`), 2014 (`loved`).

**Depends on:** Week 2 `ingest_so.py` being built.

---

## TODO-2 — GitHub Actions CI pipeline

**What:** Add `.github/workflows/ci.yml` with: Python lint (flake8/black), pytest-django test suite, Scala build (`sbt compile test`), Angular lint + jest, Docker build verification.

**Why:** The design doc mentions CI in the Distribution Plan but it never made it into Week 1–4 deliverables. A repo with tests but no CI signals tests only run locally. Employers reading the repo will expect CI. The tests in the plan (6 test files) are a living guarantee only if CI runs them.

**Current state:** No CI config exists. Week 4 is the right place — add to Week 4 polish list alongside the README and demo video.

**Effort:** ~100 lines of YAML. Completely standard boilerplate — CC can generate it in 5 min. Key gotcha: Scala CI takes 15–20 min per run unless sbt dependency cache is configured (use `actions/cache` on `.sbt/` and `.ivy2/`).

**Depends on:** All test files from Week 2–3 being written first.

---

## TODO-3 — Adzuna API rate limit handling in ingest_adzuna.py

**What:** Add rate-limit-aware batching to `ingest_adzuna.py` — specifically: exponential backoff on HTTP 429, progress checkpointing so re-runs resume rather than restart, and optional annual-granularity mode for the historical backfill.

**Why:** Adzuna free tier = 250 req/month. Full historical backfill (15 years × 20 languages × 12 months) = 3,600 requests — 14.4× the free tier limit. Silent 429 failure means 25% of the composite score has no data for unknown months, permanent `partial=True` in ways that are hard to diagnose.

**Recommended strategy for historical backfill:** Query Adzuna at annual granularity only (300 requests total, within free tier). Interpolate monthly values from annual counts. Use monthly queries going forward for the real-time use case. Saves 3,300 requests while preserving the 15-year slider.

**Current state:** `ingest_adzuna.py` doesn't exist yet. Architect this before building it in Week 2.

**Depends on:** Week 2 `ingest_adzuna.py` being designed.

---

## TODO-4 — Weight configurability UI (strong v2 candidate)

**What:** A weight adjustment panel in the Angular UI — 4 sliders constrained to sum to 100 (GitHub %, SO %, Jobs %, Citations %) — that re-queries `/tree/` with custom weights. Backend: add optional query params to `/tree/` (`?github_weight=30&so_weight=25` etc.) and recompute composite score on the fly.

**Why:** Transforms Fossil from visualization tool to interactive analytics tool. An employer can drag weights to "job demand only" and watch the tree reshape in real time — a memorable demo moment that no other tool offers. The design doc flagged this as a "strong portfolio differentiator if added in week 4."

**Current state:** Fixed 30/25/25/20 weights baked into `compute_health_score()`. Adding on-demand recomputation requires: backend param parsing in the `/tree/` view, on-demand weight application (bypass the cached batch-computed scores), Angular slider component.

**Effort:** Medium (human: ~1 day / CC: ~20 min). Non-trivial because on-demand recomputation is architecturally different from batch computation. Week 4 is already full — this is a v2 feature if Week 3 finishes early.

**Depends on:** Week 2 `compute_health_score()` being factored as a pure function (not tightly coupled to the batch pipeline).
