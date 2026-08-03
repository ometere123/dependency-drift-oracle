# DependencyDriftOracle

`DependencyDriftOracle` is a reusable GenLayer infrastructure primitive for
systems that rely on external dependencies whose meaning can change after
approval: API documentation, SDK release notes, model-provider behavior pages,
security advisories, package READMEs, licensing pages, and protocol integration
guides.

The primitive stores an approved baseline, then lets anyone trigger a consensus
review of the live dependency URL. Validators fetch the current source
themselves and classify whether the dependency is still safe to rely on.

## The Result

Each review stores one verdict:

| Verdict | Meaning |
|---|---|
| `UNCHANGED` | Current evidence still matches the approved baseline. |
| `MINOR_CHANGE` | Cosmetic, clarifying, additive, typo, example, or non-breaking change. |
| `MATERIAL_DRIFT` | Reliance-relevant change: compatibility, endpoint, auth, security, license, terms, or behavior changed materially. |
| `UNAVAILABLE` | The evidence could not be fetched or judged safely. |

`UNAVAILABLE` is not treated as unchanged. Consumers can fail closed when
dependency evidence is missing.

## Why GenLayer

A deterministic diff can show that a page changed. It cannot reliably answer
whether the change breaks a contract, agent, wallet flow, or integration promise.

Examples:

- "Added examples" is usually minor.
- "Endpoint `/v1/run` is removed" is material.
- "Scope `read:tasks` now requires `write:tasks`" is material.
- "License changed from MIT to commercial-only" is material.
- "Page unavailable" is not proof of drift, but it is not safe to rely on.

GenLayer validators independently fetch the live source and judge the semantic
effect of the change under the same baseline and watch terms. The contract then
writes only the normalized verdict and receipt fields.

## State Model

`register_dependency(name, url, baseline, watch_terms)` creates an immutable
baseline.

`review_dependency(dep_id)` fetches the URL and stores a consensus verdict.

`deactivate_dependency(dep_id)` and `reactivate_dependency(dep_id)` are owner-only
operational controls. They cannot rewrite the baseline or change past reviews.

There is intentionally no baseline setter. If a dependency has a newly approved
baseline, register a new dependency id. That keeps the primitive honest: old
reviews always mean "judged against the baseline that was actually approved."

## How Consensus Is Used

One review uses one nondeterministic consensus block:

1. `gl.nondet.web.render(url, mode="text")` fetches current public evidence.
2. `gl.nondet.exec_prompt(...)` classifies the evidence against the approved
   baseline and watch terms.
3. `prompt_comparative` requires validators to agree on the verdict.

Validators may word notes differently. They must agree on the verdict. A fetch,
HTTP, parsing, or evidence failure is `UNAVAILABLE`, never `UNCHANGED`.

The model is never asked what the contract should do. It only classifies the
dependency evidence. Deterministic code owns permissions, caps, ring-buffer
writes, normalization, and consumer-facing views.

## How Other Contracts Use It

Consumers read the latest verdict and apply their own policy:

```python
verdict = IDependencyDriftOracle(oracle).view().get_latest_verdict(dep_id)
if verdict == "MATERIAL_DRIFT" or verdict == "UNAVAILABLE":
    raise gl.vm.UserError("dependency must be reapproved before release")
```

The repo includes [`examples/dependency_release_guard.py`](examples/dependency_release_guard.py),
a minimal consumer that blocks a release when the dependency is materially
drifted or unavailable. It owns no drift logic; it only reads the oracle verdict.

## Why This Is Not SemanticWatcher

SemanticWatcher asks whether watched content changed materially.

`DependencyDriftOracle` asks a more infrastructure-specific question: whether a
registered external dependency is still safe for another system to rely on under
an approved baseline. The stored baseline, watch terms, verdict enum, fail-closed
`UNAVAILABLE`, and consumer guard are all designed around dependency reliance,
not generic page monitoring.

## Example Use Cases

- Agent platforms checking whether a tool-provider API changed before allowing
  new automated runs.
- Wallets checking whether an RPC/provider policy page changed before enabling
  a sensitive integration.
- Protocol teams checking whether a dependency's security advisory or SDK docs
  changed before unpausing a deployment.
- Marketplaces checking whether model-provider terms changed before routing
  tasks through that provider.
- Contracts gating release flows on dependency reapproval.

## Repository Layout

```text
contracts/dependency_drift_oracle.py       reusable primitive
examples/dependency_release_guard.py       worked consumer
tests/direct/test_dependency_drift_oracle.py
DECISION.md                               candidate screen and design record
gltest.config.yaml
```

## Verification So Far

Local checks completed:

```text
genvm-lint check contracts/dependency_drift_oracle.py --json
genvm-lint check examples/dependency_release_guard.py --json
pytest tests/direct -q
```

Results:

```text
DependencyDriftOracle lint: pass
DependencyReleaseGuard lint: pass
Direct tests: 31 passed
```

Direct tests cover registration, validation, owner-only activation controls,
all four verdict paths, fail-safe parsing, missing evidence, review history,
bounded notes, separate dependency state, and the consumer example's local state.

Direct mode does not execute real cross-contract `gl.get_contract_at(...).view()`
calls between two local contracts. That path should be proven on StudioNet, where
the example consumer calls the deployed oracle address.

## StudioNet Evidence

StudioNet run started on August 3, 2026 and reached the RPC hourly rate limit
while polling the consumer guard approval. The main oracle evidence completed
before the limit:

| Action | Transaction | Result |
|---|---|---|
| deploy `DependencyDriftOracle` | `0x81d98b8361dd0d81b470d5d04092281417936c5da743c4881d350170e02e1a78` | success |
| register unchanged dependency | `0x0e9dfe4ad3dfa949282717787c745f4faee989ab23c2505aa68178409af716df` | success |
| review unchanged dependency | `0x1881cffc72df441a660dceb8035c09625ea60aa62bd32e3304548c63a127fac5` | `UNCHANGED` |
| register stale/material dependency | `0xdbe5dea1a70819078760109b896322c5baf1fa62751bca93fe4f7906dafeafaa` | success |
| review stale/material dependency | `0x57740b282cbe2ca9ba257c8d4fb175100952b129bcb464dec2a5e436e7066438` | `MATERIAL_DRIFT` |
| register unavailable dependency | `0x45cdcf81e26969e7cf0604682f9954c221bf528fb62969f98412e71c0adddaf6` | success |
| review unavailable dependency | `0xf370c0397d9435aa339625327903e18b9fea8f0fd42a9331d4313d5adf11b1d8` | `UNAVAILABLE` |
| deactivate dependency | `0xec04d92799fe709ab2e70436927bfd8b5e2fa2c8555b08a95977ba94dadfe023` | success |
| reactivate dependency | `0x407db67971396ee44e44846628f212d604e1c543d033a89c7f5434783901f905` | success |
| deploy `DependencyReleaseGuard` | `0x9434cad6d184db94b16dba11018ae510b22141e7a6d11cea35d0a1be4379aaa6` | success |
| guard propose safe release | `0x9976f86232e1745c4fc110aa0c35331df4866dd1683736c2e2fb96bca773d468` | success |

The consumer guard approval transaction was interrupted by:

```text
Rate limit exceeded: 500 requests per hour
```

So the main oracle has live StudioNet evidence for all four write methods and
all three verdict classes. The guard still needs one resumed StudioNet run after
the rate window resets to prove `approve_release_if_dependency_safe` against the
deployed oracle.

## Remaining StudioNet Guard Step

After the rate limit resets, run:

```text
gltest scripts/studionet_evidence.py -v -s --network studionet
```

Or add a small resume script using the deployed oracle and guard addresses from
the deploy transactions above.

## Commands

```text
genvm-lint check contracts/dependency_drift_oracle.py --json
genvm-lint check examples/dependency_release_guard.py --json
python -m pytest tests/direct -q
gltest scripts/studionet_evidence.py -v -s --network studionet
```
