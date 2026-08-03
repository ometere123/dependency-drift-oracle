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

`register_successor(old_dep_id, name, url, baseline, watch_terms)` creates a new
immutable dependency id that supersedes an old one. The old baseline remains
unchanged, but `get_lineage(old_dep_id)` points to the successor and
`get_lineage(new_dep_id)` points back to the superseded profile.

There is intentionally no baseline setter. If a dependency has a newly approved
baseline, register a successor. That keeps the primitive honest: old reviews
always mean "judged against the baseline that was actually approved."

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

Consumers can read the raw verdict, but the safer path is to ask for a
freshness-aware reliance status:

```python
status = IDependencyDriftOracle(oracle).view().get_reliance_status(
    dep_id, 86400
)
if status != "RELIABLE":
    raise gl.vm.UserError("dependency must be reapproved before release")
```

`get_reliance_status(dep_id, max_age_seconds)` returns:

| Status | Meaning |
|---|---|
| `RELIABLE` | Latest verdict is `UNCHANGED` or `MINOR_CHANGE`, and it is fresh enough. |
| `STALE` | Latest safe verdict is older than the consumer's freshness window. |
| `BLOCKED` | Latest verdict is `MATERIAL_DRIFT`. |
| `UNKNOWN` | No review, unavailable evidence, or unsafe/unparseable state. |

The repo includes [`examples/dependency_release_guard.py`](examples/dependency_release_guard.py),
a minimal consumer that blocks a release when the dependency is materially
drifted, unavailable, unknown, or stale. It owns no drift logic; it only reads the
oracle's reliance status.

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
Direct tests: 39 passed
```

Direct tests cover registration, validation, owner-only activation controls,
all four verdict paths, fail-safe parsing, missing evidence, successor baseline
lineage, freshness-aware reliance status, stale-review boundaries, review
history, bounded notes, separate dependency state, and the consumer example's
local state.

Direct mode does not execute real cross-contract `gl.get_contract_at(...).view()`
calls between two local contracts. That path should be proven on StudioNet, where
the example consumer calls the deployed oracle address.

## StudioNet Evidence

StudioNet evidence passed on August 3, 2026. The latest source also has a
separate successor-lineage StudioNet deployment proving the upgrade path.

| Contract | Address |
|---|---|
| `DependencyDriftOracle` with successor lineage | `0xe11a825b18df97c6AeC02e26028C54f57C74311a` |
| Earlier full `DependencyDriftOracle` guard run | `0xF11a20059470e8d5d1B6735B6E015117b8C8aEBE` |
| `DependencyReleaseGuard` full run | `0x17eaDd5316f9f07f715424452dAa5264002c3005` |

Explorer links:

- Latest oracle: `https://explorer-studio.genlayer.com/address/0xe11a825b18df97c6AeC02e26028C54f57C74311a`
- Full-run oracle: `https://explorer-studio.genlayer.com/address/0xF11a20059470e8d5d1B6735B6E015117b8C8aEBE`
- Release guard: `https://explorer-studio.genlayer.com/address/0x17eaDd5316f9f07f715424452dAa5264002c3005`

Latest successor-lineage oracle evidence:

| Action | Transaction | Result |
|---|---|---|
| deploy updated `DependencyDriftOracle` | `0xbb2293622ff24330214a9608a81a0b0cc04af883ee80ec9c354079dd0a5094a1` | success |
| register dependency | `0x1e50a8cb75033f9fceea09469064aa5aa61aaa8e6143fac4cbb89466a6ce6dc7` | success |
| review dependency | `0xf7cf4ffaba3a268c87eed31236ffa4a1845bdcc13896c4d3225f9261fa057f6a` | `UNCHANGED` |
| register successor baseline | `0xe01da09c6246c03d54b1973171575f81b1bebd0a6e8afde45523874d3538052e` | success; old dep `1` now points to successor dep `2` |
| review successor dependency | `0x79366ece68319e314d50cef3ef5d0b5e04a72e242d5253b658b652b1e2769b17` | `UNCHANGED` |

Full oracle evidence from the earlier compatible deployment:

| Action | Transaction | Result |
|---|---|---|
| deploy `DependencyDriftOracle` | `0x013415db8f63ca42cc5ca32e68fb36e5babdd914d268864723a983aef0c88a1c` | success |
| register unchanged dependency | `0x3d4bc70e6ca8e1229bae0e4e0a75eebb23a118b2f8fa404c6a9e873462c9b985` | success |
| review unchanged dependency | `0x0c3706a63f990d2cd9d32ee02f1e57ba008f11aeb186fff153bfd14e7b9d990e` | `UNCHANGED` |
| register stale/material dependency | `0x198e54da6d88eb68c082e6cfd1e58eacc604e7f49df6834849bd3e771706fc25` | success |
| review stale/material dependency | `0x10b0a97126b3ee08b6d726f162140deee08e44a942b9f0b69503d6de4f91a7fc` | `MATERIAL_DRIFT` |
| register unavailable dependency | `0xa29449899b19d9384530c47bb894ab11e1168c47ad44d32f6d4f6f96774ee977` | success |
| review unavailable dependency | `0xf090a54f887560cb875004834191d08ca1cf6c6008ecbbbe6b12fbf9254bb9fe` | `UNAVAILABLE` |
| deactivate dependency | `0x78457d011fd7407f9eef409a4f59837c59a00b93a4cb4ea68495514ff95af6a2` | success |
| reactivate dependency | `0x88fc7242951b077445c52da8c9dd57c2a155d2abe07f03bb2441cdecad4a3076` | success |

Consumer guard evidence:

| Action | Transaction | Result |
|---|---|---|
| deploy `DependencyReleaseGuard` | `0x29608e753014a177eef6a15f7919198bedaf9cab97457ac4d22e7084de60b25d` | success |
| guard propose safe release | `0xe9023725c4c3f4addd4eb2128f3f01916148c46ceedd780a468f85b893bf379c` | success |
| guard approve safe release | `0xf5e4554e15ed8d9837e01ae9ac041b2cdb240861293c013ecb6318147f30116a` | `APPROVED`, checked oracle reliance status `RELIABLE` |
| guard propose risky release | `0xa588c57d0115427c3c4b8c293908c5b7fcbc49abef5a21e481af83b0f0e47b16` | success |
| guard attempt risky approval | `0xd6e2196129bd029e02ab3149ce0a9d44775715662129bff3929cab53fb5d800c` | finalized/accepted with GenVM rollback: `EXPECTED: dependency reliance status blocks release` |

The risky release remained `PROPOSED` with `checked_verdict: UNKNOWN`, proving the
guard did not approve or mutate the release after the oracle returned
`MATERIAL_DRIFT`.

## Commands

```text
genvm-lint check contracts/dependency_drift_oracle.py --json
genvm-lint check examples/dependency_release_guard.py --json
python -m pytest tests/direct -q
gltest scripts/studionet_evidence.py -v -s --network studionet
```
