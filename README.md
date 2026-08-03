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

StudioNet evidence passed on August 3, 2026. The latest oracle deployment proves
successor lineage, material drift detection, and a consumer guard calling that
same oracle address.

| Contract | Address |
|---|---|
| `DependencyDriftOracle` | `0xe11a825b18df97c6AeC02e26028C54f57C74311a` |
| `DependencyReleaseGuard` | `0xcb84704a97F033E38c7151182F6A10BF355e0c84` |

Explorer links:

- Oracle: `https://explorer-studio.genlayer.com/address/0xe11a825b18df97c6AeC02e26028C54f57C74311a`
- Release guard: `https://explorer-studio.genlayer.com/address/0xcb84704a97F033E38c7151182F6A10BF355e0c84`

Main oracle evidence:

| Action | Transaction | Result |
|---|---|---|
| deploy updated `DependencyDriftOracle` | `0xbb2293622ff24330214a9608a81a0b0cc04af883ee80ec9c354079dd0a5094a1` | success |
| register dependency | `0x1e50a8cb75033f9fceea09469064aa5aa61aaa8e6143fac4cbb89466a6ce6dc7` | success |
| review dependency | `0xf7cf4ffaba3a268c87eed31236ffa4a1845bdcc13896c4d3225f9261fa057f6a` | `UNCHANGED` |
| register successor baseline | `0xe01da09c6246c03d54b1973171575f81b1bebd0a6e8afde45523874d3538052e` | success; old dep `1` now points to successor dep `2` |
| review successor dependency | `0x79366ece68319e314d50cef3ef5d0b5e04a72e242d5253b658b652b1e2769b17` | `UNCHANGED` |
| register material dependency | `0xff33b1c23087cfb2c164f02720d71828589000922d35fe9f02bfa02f5b0a2592` | success |
| review material dependency | `0x3a950640cb722e501834062600ff3338b0a13cf874715b1d7e0d9f0044a63725` | `MATERIAL_DRIFT` |

Consumer guard evidence:

| Action | Transaction | Result |
|---|---|---|
| deploy `DependencyReleaseGuard` with latest oracle address | `0xb8f72f2332dd4e7fdf461b50cce4e63f5b10b7e11a44217149be86ea31b07975` | success |
| guard propose safe release | `0x79874fdf18b9a79af97eb9ed18265570554171c396d705037cb06508a946ba5a` | success |
| guard approve safe release | `0xe974fedfc89a0318fd59961dd0ec2d063caaa7a7297099e1c07a7ff7eb23b560` | `APPROVED`, checked oracle reliance status `RELIABLE` |
| guard propose risky release | `0x2907b1726cc5a7e4f0902f3bf7c28714f7a5251316f209fd870ba6e4c410b75c` | success |
| guard attempt risky approval | `0x4b0ad040ca8f953b6ccdc38f188ea8ff289ac0f7de1b932a47b72a876d383308` | accepted rollback: `EXPECTED: dependency reliance status blocks release` |

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
