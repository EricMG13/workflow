# Perf-sweep progress

- 06:53Z prepare: profiles copied (prof2.out already gone); CONTRACT.md, register.md written.
- 06:58Z discover: prof3 callers mapped; micro-trial (probes/micro_trial.py, exit 0) on a real CP-1 blob; product-plan.md written (P1–P3 proposed, P4 not recommended, P5/P6 deferred).
- 07:00Z waiting: Stage 5 tip on codex/checkpoint (still 2bbf633; asked PR manager local_73a216ba); machine busy with Modules' Stage 5 pytest runs (load ≈ 11 on 10 cores). Before-timings start on the tip once load is low.
- Harness ready: probes/time_tests.sh <label> <targets-file>; probes/durations.py <logs>.
- 07:02Z PR manager: no Stage 5 release yet (codex/checkpoint 2bbf633); will send the sha. Heavy set taken from its transcript (pm-410afa2-durations.txt); heavy-targets.txt and noise-targets.txt written.
- 11:40Z Stage 5 landed (PR manager): local codex/checkpoint 05c3b27 (origin still 2bbf633). Merged into the branch at 5ee6c9b; no overlap with P1–P3 files. Snapshots T0–T3 built. pins --check exit 0 at 5ee6c9b (86 paths); suppressions 13/5.
- 11:40Z Phase A started: noise T0 ∥ T0 (runs/noise-a, runs/noise-b), load 1.6 at start.
- 12:13Z Phase A done: noise T0∥T0 — s1a tampering[gap] 895/888 s (0.79%), E-NO-YOY 1060/1055 s (0.47%); peak RSS 5.1–5.3 GiB per process. Noise = 0.79% → 5% floor governs.
- 12:14Z Modules asked to run its final long suites (lane 373037d). Told it: wait until ~13:05Z (sentinel + identity pairs need the quiet machine), then run capped at 6 concurrent pytest processes alongside the heavy pair. Noise under that load = deviation of the heavy-pass T0 E-NO-YOY and s1a tampering[gap] from their quiet-machine Phase A values (no extra runs).
- 12:27Z Phase C: sentinel E-NO-YOY T2 (P2+P1) 789 s (KEEP, 230 MB tree); T1 running; T3 started early; T0 queued after T1; heavy pair T0∥T3 queued to start when both identity runs finish.
- 12:31Z Phase C: T1 (P2) 999 s, T2 (P2+P1) 789 s. Unseeded T1/T2 trees differ only by uuid4 run ids (ticket/call/session ids; 204 hash fields cascade) — not comparable. Stopped unseeded T0/T3 runs; started seeded identity pair (probes/seeded_uuid.py, PYTHONHASHSEED=0, KEEP) ident-T0 ∥ ident-T3; heavy pair queued after it.
- 12:49Z Identity: seeded E-NO-YOY T0 vs T3 trees: 131 vs 131 files, 0 only-in-one, 0 differ (probes/compare_trees.py exit 0). Timing seeded: T0 1038 s, T3 736 s; peak RSS 5.72 vs 5.87 GB. Heavy pair T0 ∥ T3 started 12:48Z.
