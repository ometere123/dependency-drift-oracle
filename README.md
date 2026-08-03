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

StudioNet evidence passed on August 3, 2026.

| Contract | Address |
|---|---|
| `DependencyDriftOracle` | `0x9CCaD10e56Ba56fC702C23dc39092676bFe3ED74` |
| `DependencyReleaseGuard` | `0x961544c7C4dC4e8137D49c4205FB7a76d1051Cb3` |

Explorer links:

- Oracle: `https://explorer-studio.genlayer.com/address/0x9CCaD10e56Ba56fC702C23dc39092676bFe3ED74`
- Release guard: `https://explorer-studio.genlayer.com/address/0x961544c7C4dC4e8137D49c4205FB7a76d1051Cb3`

Main oracle evidence:

| Action | Transaction | Result |
|---|---|---|
| deploy `DependencyDriftOracle` | `0xb5ddce73e2abf2d4a6fc299b3ba638794d167d61016559003cb084c053a21c72` | success |
| register unchanged dependency | `0x68e86463958cafcbef0ff9aa239fd5105a4246e7d9718fe5891bfbf5fbeedd3c` | success |
| review unchanged dependency | `0x85df9c02b47ae6fe8d53b3fed03d05788ebefd4a096706bf6463f4b4c8d4db6e` | `UNCHANGED` |
| register stale/material dependency | `0x839530faec568048b3a553f47ae1f94bbb0df1fb21e7294958d3e398f3a3727e` | success |
| review stale/material dependency | `0xb6c73c40bd6bdd555ccb8bab971c8c34f7a54921db84d0fa343111182cf82e0e` | `MATERIAL_DRIFT` |
| register unavailable dependency | `0x7341fd34580b7e6ec9a971f4c73628109b7997b7818d664b68363fcc9fd40a2d` | success |
| review unavailable dependency | `0xd08d17288e52a48192e293da5af3fd6af6dedbc60023434a4024adae8f7c25dd` | `UNAVAILABLE` |
| deactivate dependency | `0x23bcf0b0569f527b5471592af0264351a24f34d162f92e14f0920ec3301b3c4e` | success |
| reactivate dependency | `0xdb871042d56f476c7b86c092d78aebf5df86714fa95b522fa2fe691c793b9ab5` | success |

Consumer guard evidence:

| Action | Transaction | Result |
|---|---|---|
| deploy `DependencyReleaseGuard` | `0xb90cdf8500e55b31ebcb5383a8cc46a014a3233f41f3a0908fddd2060156200f` | success |
| guard propose safe release | `0x600d07034b95a87c2e6d177968872c11f0c52acbf301c2e034f5fe24715009c3` | success |
| guard approve safe release | `0xf8af0f67fa3a478bae32eabc1b96570c702900c593c32e1b109b347d17af02ef` | `APPROVED`, checked oracle verdict `UNCHANGED` |
| guard propose risky release | `0x0d2a9641b68cedfe75b013ba457ff5e1f1f0febdda2f425ccd62f5be5e4d4d72` | success |
| guard attempt risky approval | `0xcd759716b309b0532bd2cd1c8f92ba5199ab8533344e3d69e8331c78c7c12166` | finalized/accepted with GenVM rollback: `EXPECTED: dependency verdict blocks release` |

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
