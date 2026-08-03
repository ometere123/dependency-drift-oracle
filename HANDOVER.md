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
=> 31 passed
```

The linter reports only informational runner-update warning `I200`.

## StudioNet Evidence Completed

Completed transaction hashes:

```text
deploy DependencyDriftOracle:
0xb5ddce73e2abf2d4a6fc299b3ba638794d167d61016559003cb084c053a21c72

DependencyDriftOracle address:
0x9CCaD10e56Ba56fC702C23dc39092676bFe3ED74

register unchanged:
0x68e86463958cafcbef0ff9aa239fd5105a4246e7d9718fe5891bfbf5fbeedd3c

review unchanged -> UNCHANGED:
0x85df9c02b47ae6fe8d53b3fed03d05788ebefd4a096706bf6463f4b4c8d4db6e

register material:
0x839530faec568048b3a553f47ae1f94bbb0df1fb21e7294958d3e398f3a3727e

review material -> MATERIAL_DRIFT:
0xb6c73c40bd6bdd555ccb8bab971c8c34f7a54921db84d0fa343111182cf82e0e

register unavailable:
0x7341fd34580b7e6ec9a971f4c73628109b7997b7818d664b68363fcc9fd40a2d

review unavailable -> UNAVAILABLE:
0xd08d17288e52a48192e293da5af3fd6af6dedbc60023434a4024adae8f7c25dd

deactivate:
0x23bcf0b0569f527b5471592af0264351a24f34d162f92e14f0920ec3301b3c4e

reactivate:
0xdb871042d56f476c7b86c092d78aebf5df86714fa95b522fa2fe691c793b9ab5

deploy DependencyReleaseGuard:
0xb90cdf8500e55b31ebcb5383a8cc46a014a3233f41f3a0908fddd2060156200f

DependencyReleaseGuard address:
0x961544c7C4dC4e8137D49c4205FB7a76d1051Cb3

guard propose safe release:
0x600d07034b95a87c2e6d177968872c11f0c52acbf301c2e034f5fe24715009c3

guard approve safe release -> APPROVED, checked_verdict UNCHANGED:
0xf8af0f67fa3a478bae32eabc1b96570c702900c593c32e1b109b347d17af02ef

guard propose risky release:
0x0d2a9641b68cedfe75b013ba457ff5e1f1f0febdda2f425ccd62f5be5e4d4d72

guard attempt risky approval -> accepted rollback, action blocked:
0xcd759716b309b0532bd2cd1c8f92ba5199ab8533344e3d69e8331c78c7c12166
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
