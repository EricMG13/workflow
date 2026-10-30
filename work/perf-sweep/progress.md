# Perf-sweep progress

- 06:53Z prepare: profiles copied (prof2.out already gone); CONTRACT.md, register.md written.
- 06:58Z discover: prof3 callers mapped; micro-trial (probes/micro_trial.py, exit 0) on a real CP-1 blob; product-plan.md written (P1–P3 proposed, P4 not recommended, P5/P6 deferred).
- 07:00Z waiting: Stage 5 tip on codex/checkpoint (still 2bbf633; asked PR manager local_73a216ba); machine busy with Modules' Stage 5 pytest runs (load ≈ 11 on 10 cores). Before-timings start on the tip once load is low.
- Harness ready: probes/time_tests.sh <label> <targets-file>; probes/durations.py <logs>.
- 07:02Z PR manager: no Stage 5 release yet (codex/checkpoint 2bbf633); will send the sha. Heavy set taken from its transcript (pm-410afa2-durations.txt); heavy-targets.txt and noise-targets.txt written.
