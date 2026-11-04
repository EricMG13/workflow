# Confidence review — PR5 CI heavy-tier routing

Least confident about (ranked):
1. Affected test partition could omit or double-run earnings coverage. The selector's fast tier is selected minus `HEAVY`; checkpoint independently runs its heavy file matrix and excludes the same list from the suite. Focused temp-Git probes prove shared-source selection yields disjoint tiers whose union equals the three expected files, direct earnings edit yields earnings heavy-only, and the existing test asserts both checkpoint lists equal the selector tuple. **Verified.**
2. Adding verbosity could change CI selection or fail behavior. Inspected the two exact `pytest` commands: `-v` is the only invocation change and existing marker, duration report, runner, label condition and timeouts are unchanged. **By design; confirmed in diff.**
3. Moving earnings to heavy might hide its completion or exceed existing job limits. The job retains its existing 360-minute limit and all243 nodes collected; verbose output identifies each node if a later run stalls. This does not establish the file completes within360 minutes. **Open duration risk.**
4. Could claim the rerouted test proves the historical PR CI failure is resolved. Logs identify a plausible slow integration/recovery boundary but do not name the cancelled node; no test body, new CI or remote rerun was run. **Open; next evidence is the applicable heavy job with verbose output.**

Fixed: selector/CI tier mismatch. The changed source set includes exactly the four leased code/config files: `.github/workflows/checkpoint.yml, .github/workflows/pr-heavy.yml, cases/prove/affected_tests.py, tests/test_prove_affected.py`.
Verified fine: 23 focused selector tests passed; all243 earnings nodes collected in0.29s; `git diff --check` exited0; exact shared-change partition and direct-file selection pass.
By-design: no timeout increase, no test removal, no new PR label/run initiated.
Still open: exact cancelled CI node and eventual earnings suite duration; applicable PR heavy job has not run.
