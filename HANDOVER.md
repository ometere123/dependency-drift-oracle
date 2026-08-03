# Handover - DependencyDriftOracle

Current status: local implementation complete, main StudioNet oracle evidence
partially complete.

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
=> 31 passed
```

The linter reports only informational runner-update warning `I200`.

## StudioNet Evidence Completed Before Rate Limit

The evidence script deployed the oracle, executed every main oracle write, and
deployed/proposed on the consumer guard. It then hit StudioNet's hourly RPC rate
limit while polling `approve_release_if_dependency_safe`.

Completed transaction hashes:

```text
deploy DependencyDriftOracle:
0x81d98b8361dd0d81b470d5d04092281417936c5da743c4881d350170e02e1a78

register unchanged:
0x0e9dfe4ad3dfa949282717787c745f4faee989ab23c2505aa68178409af716df

review unchanged -> UNCHANGED:
0x1881cffc72df441a660dceb8035c09625ea60aa62bd32e3304548c63a127fac5

register material:
0xdbe5dea1a70819078760109b896322c5baf1fa62751bca93fe4f7906dafeafaa

review material -> MATERIAL_DRIFT:
0x57740b282cbe2ca9ba257c8d4fb175100952b129bcb464dec2a5e436e7066438

register unavailable:
0x45cdcf81e26969e7cf0604682f9954c221bf528fb62969f98412e71c0adddaf6

review unavailable -> UNAVAILABLE:
0xf370c0397d9435aa339625327903e18b9fea8f0fd42a9331d4313d5adf11b1d8

deactivate:
0xec04d92799fe709ab2e70436927bfd8b5e2fa2c8555b08a95977ba94dadfe023

reactivate:
0x407db67971396ee44e44846628f212d604e1c543d033a89c7f5434783901f905

deploy DependencyReleaseGuard:
0x9434cad6d184db94b16dba11018ae510b22141e7a6d11cea35d0a1be4379aaa6

guard propose safe release:
0x9976f86232e1745c4fc110aa0c35331df4866dd1683736c2e2fb96bca773d468
```

The script failed only because of:

```text
Rate limit exceeded: 500 requests per hour
```

## Important Design Notes

- No mutable baseline setter. Reapproval means registering a new dependency id.
- `review_dependency` is permissionless; the caller cannot control evidence except
  by choosing an already-registered dependency id.
- Fetch or model failure returns `UNAVAILABLE`, not `UNCHANGED`.
- Direct mode cannot prove cross-contract `gl.get_contract_at(...).view()` calls.
  The consumer example is linted and direct-tested for local state, but wrapper to
  oracle must be proven on StudioNet.

## Next Steps

1. After the hourly rate limit resets, resume the guard approval/blocking proof.
2. Open the deploy transactions in Explorer and copy the main/guard addresses.
3. Update README with final addresses and explorer links.
4. Commit and push to GitHub.

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
