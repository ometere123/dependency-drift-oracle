# Decision Record - DependencyDriftOracle

## Chosen Primitive

`DependencyDriftOracle` is a reusable infrastructure primitive for contracts,
agents, wallets, and platforms that rely on external dependencies whose meaning
can change over time: API docs, SDK release notes, terms, model-provider pages,
security advisories, package READMEs, or protocol integration guides.

The primitive stores an approved baseline and later lets anyone trigger a
validator-consensus review of the live dependency URL. The stored verdict is one
of `UNCHANGED`, `MINOR_CHANGE`, `MATERIAL_DRIFT`, or `UNAVAILABLE`.

This is not a generic page watcher. The question is narrower and more useful:
"can a consuming system still safely rely on this dependency under the approved
baseline?"

## Candidate Screen

| # | Candidate | Capability | Value? | Verdict |
|---|---|---|---|---|
| 1 | DependencyDriftOracle | web + semantic consensus | no | chosen |
| 2 | AgentCalldataFirewall | cross-contract execution gate | no | rejected; crowded and easy to mis-specify |
| 3 | SDKBreakingChangeOracle | web + semantic consensus | no | folded into #1 |
| 4 | TermsChangeGate | web + legal-language judgment | no | folded into #1 |
| 5 | DependencyBondVault | native value + drift verdict | yes | too application-specific |
| 6 | MaintenanceCreditVault | native value + uptime/drift | yes | overlaps uptime |
| 7 | VisualStatusPanelOracle | screenshot/image evidence | no | weaker reuse story |
| 8 | PackageReadmeSimilarityIndex | embeddings | no | too search-shaped |
| 9 | PolicyClauseMatcher | embeddings + policy | no | close to policy-gate |
| 10 | BridgeNoticeDriftOracle | EVM/web notices | no | narrower than #1 |
| 11 | APICompatibilitySentinel | web + interface reasoning | no | overlaps interface compatibility |
| 12 | DependencyFactoryRegistry | deploys child monitors | no | useful later, not core primitive |

Capabilities represented: web/API consensus, native value, image evidence,
embeddings, EVM/cross-chain evidence, contract factories/composition.

## Anti-Drift Audit

The most similar pair is `DependencyDriftOracle` and `SDKBreakingChangeOracle`.
They are the same primitive at different scope, so the broader dependency form
was chosen and the narrower one was discarded.

If web access did not exist, the strongest alternative would be a native-value
`DependencyBondVault`, where maintainers post collateral against a signed
compatibility promise. I did not choose it because the hard problem is discovering
semantic drift from public evidence; value can be added by consumers.

The strongest discarded idea is `AgentCalldataFirewall`. It is timely, but a
friend's review showed the category is fragile unless the contract enforces
exact calldata-bound execution. That turns it into middleware rather than a
neutral primitive and increases review risk.

## Gate Checks

**Counterfactual.** Without GenLayer, a single backend decides whether dependency
docs changed materially. The maintainer, platform, or integrator can all be biased.
With GenLayer, validators fetch and judge the dependency independently.

**Distrusting parties.** Dependency maintainer, integrator, downstream users, and
contracts/apps that use the dependency. A maintainer may understate breaking
changes; an integrator may exaggerate drift to avoid obligations.

**Judgment.** "Material drift" is semantic. A deterministic diff cannot know that
"endpoint renamed" or "auth scope changed" breaks a consumer while a typo does not.

**Reusable interface.** Consumers only need:

```python
verdict = IDependencyDriftOracle(oracle).view().get_latest_verdict(dep_id)
if verdict == "MATERIAL_DRIFT":
    pause_or_require_reapproval()
```

**Consequential state.** The verdict gates releases, agent execution, integration
pauses, deployment approvals, or contract configuration changes in consumers.

**Originality.** Existing GenLayer examples focus on prediction/oracle outcomes,
deliverable acceptance, uptime, source corroboration, or compatibility checks.
This primitive focuses on dependency reliance risk after an approved baseline.

## Nondeterminism Budget

One consensus block per review:

1. `web.render(url, mode="text")`: fetch the live dependency evidence.
2. `exec_prompt`: classify drift against the immutable baseline and watch terms.

Everything else is deterministic: access control, registration, baseline storage,
status normalization, caps, ring-buffer writes, and consumer-facing views.

## Failure Semantics

External fetch failure is `UNAVAILABLE`, never `MATERIAL_DRIFT` and never
`UNCHANGED`. Unparseable model output becomes `UNAVAILABLE`. This is safe for
consumers because it says "do not rely blindly; evidence could not be checked."

## Consumer Boundary

The primitive does not pause another system by itself. That policy belongs to the
consumer. The example `DependencyReleaseGuard` demonstrates the intended pattern:
read the oracle verdict and block release only when the latest verdict is
`MATERIAL_DRIFT` or `UNAVAILABLE`.
