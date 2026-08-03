# Handover - DependencyDriftOracle

Current status: local implementation complete, pushed-ready docs updated, and
StudioNet evidence collected.

## Built

- `contracts/dependency_drift_oracle.py`
- `examples/dependency_release_guard.py`
- `tests/direct/test_dependency_drift_oracle.py`
- `DECISION.md`
- `README.md`

## Verification Completed

```text
genvm-lint check contracts/dependency_drift_oracle.py --json
=> ok true

genvm-lint check examples/dependency_release_guard.py --json
=> ok true

python -m pytest tests/direct -q
=> 39 passed
```

The linter reports only informational runner-update warning `I200`.

## StudioNet Evidence Completed

Latest successor-lineage deployment:

```text
deploy updated DependencyDriftOracle:
0xbb2293622ff24330214a9608a81a0b0cc04af883ee80ec9c354079dd0a5094a1

DependencyDriftOracle address:
0xe11a825b18df97c6AeC02e26028C54f57C74311a

register dependency:
0x1e50a8cb75033f9fceea09469064aa5aa61aaa8e6143fac4cbb89466a6ce6dc7

review dependency -> UNCHANGED:
0xf7cf4ffaba3a268c87eed31236ffa4a1845bdcc13896c4d3225f9261fa057f6a

register successor:
0xe01da09c6246c03d54b1973171575f81b1bebd0a6e8afde45523874d3538052e

review successor -> UNCHANGED:
0x79366ece68319e314d50cef3ef5d0b5e04a72e242d5253b658b652b1e2769b17

latest oracle register material:
0xff33b1c23087cfb2c164f02720d71828589000922d35fe9f02bfa02f5b0a2592

latest oracle review material -> MATERIAL_DRIFT:
0x3a950640cb722e501834062600ff3338b0a13cf874715b1d7e0d9f0044a63725

DependencyReleaseGuard address:
0xcb84704a97F033E38c7151182F6A10BF355e0c84

deploy DependencyReleaseGuard with latest oracle address:
0xb8f72f2332dd4e7fdf461b50cce4e63f5b10b7e11a44217149be86ea31b07975

guard propose safe release:
0x79874fdf18b9a79af97eb9ed18265570554171c396d705037cb06508a946ba5a

guard approve safe release -> APPROVED, checked_verdict RELIABLE:
0xe974fedfc89a0318fd59961dd0ec2d063caaa7a7297099e1c07a7ff7eb23b560

guard propose risky release:
0x2907b1726cc5a7e4f0902f3bf7c28714f7a5251316f209fd870ba6e4c410b75c

guard attempt risky approval -> accepted rollback, action blocked:
0x4b0ad040ca8f953b6ccdc38f188ea8ff289ac0f7de1b932a47b72a876d383308
```

## Important Design Notes

- No mutable baseline setter. Reapproval means registering a new dependency id.
- `register_successor(old_dep_id, ...)` is the approved baseline-upgrade path.
  It links old/new dependency ids without mutating the old baseline.
- `get_reliance_status(dep_id, max_age_seconds)` is the preferred consumer view.
  It returns `RELIABLE`, `STALE`, `BLOCKED`, or `UNKNOWN`.
- `review_dependency` is permissionless; the caller cannot control evidence except
  by choosing an already-registered dependency id.
- Fetch or model failure returns `UNAVAILABLE`, not `UNCHANGED`.
- Direct mode cannot prove cross-contract `gl.get_contract_at(...).view()` calls.
  The consumer example is linted and direct-tested for local state, but wrapper to
  oracle must be proven on StudioNet.

## Next Steps

1. Commit the updated README/HANDOVER.
2. Create public GitHub repo and push.
3. Prepare the <=1000-character submission note.

## Suggested Live Rounds

Use stable public URLs where possible:

- SAFE or MINOR: a stable official docs page with baseline matching the page.
- MATERIAL: register a dependency baseline that intentionally conflicts with the
  current page, e.g. baseline says "MIT license and /v1/run endpoint exists" while
  the live evidence says otherwise.
- UNAVAILABLE: an HTTPS URL that returns no readable evidence or is intentionally
  invalid.

For the material-drift round, it is acceptable to use a serious public page with an
intentionally stale baseline. The point is to show the primitive detects baseline
drift; the baseline is the approved dependency state supplied at registration.
