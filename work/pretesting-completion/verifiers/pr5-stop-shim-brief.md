# PR5 stop-writer shim brief

Task: PR5-STOP-WRITER-SHIM-01
Base: be9fc49a4a6340ade8165f8ae85b1d8315059619

The nested `die` test shim now accepts the actual `_write_run_json` trailing optional parameters (`record`, `head_state`). Its body is unchanged: it records `(outcome, reason)` and raises `Kill("run.json")`. No product code or assertions changed.
