# Handover - DependencyDriftOracle

Current status: local implementation and StudioNet evidence complete.

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
=> 34 passed
```

The linter reports only informational runner-update warning `I200`.

## StudioNet Evidence Completed

Completed transaction hashes:

```text
deploy DependencyDriftOracle:
0x013415db8f63ca42cc5ca32e68fb36e5babdd914d268864723a983aef0c88a1c

DependencyDriftOracle address:
0xF11a20059470e8d5d1B6735B6E015117b8C8aEBE

register unchanged:
0x3d4bc70e6ca8e1229bae0e4e0a75eebb23a118b2f8fa404c6a9e873462c9b985

review unchanged -> UNCHANGED:
0x0c3706a63f990d2cd9d32ee02f1e57ba008f11aeb186fff153bfd14e7b9d990e

register material:
0x198e54da6d88eb68c082e6cfd1e58eacc604e7f49df6834849bd3e771706fc25

review material -> MATERIAL_DRIFT:
0x10b0a97126b3ee08b6d726f162140deee08e44a942b9f0b69503d6de4f91a7fc

register unavailable:
0xa29449899b19d9384530c47bb894ab11e1168c47ad44d32f6d4f6f96774ee977

review unavailable -> UNAVAILABLE:
0xf090a54f887560cb875004834191d08ca1cf6c6008ecbbbe6b12fbf9254bb9fe

deactivate:
0x78457d011fd7407f9eef409a4f59837c59a00b93a4cb4ea68495514ff95af6a2

reactivate:
0x88fc7242951b077445c52da8c9dd57c2a155d2abe07f03bb2441cdecad4a3076

deploy DependencyReleaseGuard:
0x29608e753014a177eef6a15f7919198bedaf9cab97457ac4d22e7084de60b25d

DependencyReleaseGuard address:
0x17eaDd5316f9f07f715424452dAa5264002c3005

guard propose safe release:
0x600d07034b95a87c2e6d177968872c11f0c52acbf301c2e034f5fe24715009c3

guard approve safe release -> APPROVED, checked_verdict RELIABLE:
0xf5e4554e15ed8d9837e01ae9ac041b2cdb240861293c013ecb6318147f30116a

guard propose risky release:
0xa588c57d0115427c3c4b8c293908c5b7fcbc49abef5a21e481af83b0f0e47b16

guard attempt risky approval -> accepted rollback, action blocked:
0xd6e2196129bd029e02ab3149ce0a9d44775715662129bff3929cab53fb5d800c
```

## Important Design Notes

- No mutable baseline setter. Reapproval means registering a new dependency id.
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
