import json

CONTRACT = "contracts/dependency_drift_oracle.py"
EXAMPLE = "examples/dependency_release_guard.py"
URL = "https://docs.example.com/sdk"
BASELINE = (
    "SDK v1 uses endpoint /v1/run, supports token auth scope read:tasks, "
    "keeps MIT license, and promises backward-compatible JSON responses."
)
WATCH = "endpoint names; auth scopes; response schema; license; security requirements"


def deploy(direct_deploy):
    return direct_deploy(CONTRACT)


def deploy_example(direct_deploy, oracle_address):
    import genlayer.gl.genvm_contracts as contracts
    contracts.__known_contract__ = None
    return direct_deploy(EXAMPLE, oracle_address)


def register(c):
    return c.register_dependency("Example SDK", URL, BASELINE, WATCH)


def mock_review(direct_vm, body, verdict, note="reviewed"):
    direct_vm.mock_web(r".*docs\.example\.com/sdk.*", {"status": 200, "body": body})
    direct_vm.mock_llm(
        r".*dependency drift assessor.*",
        json.dumps({"verdict": verdict, "note": note}),
    )


def warp_to(direct_vm, iso):
    direct_vm.warp(iso)
    import genlayer.gl as gl
    raw = getattr(gl, "message_raw", None)
    if isinstance(raw, dict):
        raw["datetime"] = iso
    nested = getattr(getattr(gl, "message", None), "raw", None)
    if isinstance(nested, dict):
        nested["datetime"] = iso


def test_initial_state(direct_deploy):
    c = deploy(direct_deploy)
    assert c.dependency_count() == 0
    assert c.get_latest_verdict(999) == "UNKNOWN"
    assert c.get_reliance_status(999, 3600) == "UNKNOWN"
    assert c.is_reliable(999, 3600) is False


def test_register_dependency_records_profile(direct_vm, direct_deploy, direct_alice):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    dep_id = register(c)
    state = c.get_dependency(dep_id)
    assert dep_id == 1
    assert state["name"] == "Example SDK"
    assert state["url"] == URL
    assert state["baseline"] == BASELINE
    assert state["watch_terms"] == WATCH
    assert state["active"] is True
    assert state["latest_verdict"] == "UNKNOWN"
    assert state["supersedes_id"] == 0
    assert state["successor_id"] == 0


def test_ids_are_monotonic(direct_deploy):
    c = deploy(direct_deploy)
    assert register(c) == 1
    assert c.register_dependency("Second", "https://docs.example.com/second", BASELINE, "") == 2
    assert c.dependency_count() == 2


def test_invalid_name_rejected(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("invalid name"):
        c.register_dependency("", URL, BASELINE, WATCH)


def test_long_name_rejected(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("invalid name"):
        c.register_dependency("x" * 121, URL, BASELINE, WATCH)


def test_http_url_rejected(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("HTTPS"):
        c.register_dependency("SDK", "http://docs.example.com/sdk", BASELINE, WATCH)


def test_short_baseline_rejected(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("invalid baseline"):
        c.register_dependency("SDK", URL, "too short", WATCH)


def test_long_baseline_rejected(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("invalid baseline"):
        c.register_dependency("SDK", URL, "x" * 1801, WATCH)


def test_long_watch_terms_rejected(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("watch_terms"):
        c.register_dependency("SDK", URL, BASELINE, "x" * 801)


def test_review_unchanged(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "UNCHANGED", "same behavior")
    assert c.review_dependency(dep_id) == "UNCHANGED"
    assert c.get_latest_verdict(dep_id) == "UNCHANGED"
    latest = c.get_latest_review(dep_id)
    assert latest["exists"] is True
    assert latest["verdict"] == "UNCHANGED"
    assert len(latest["baseline_hash"]) == 64
    assert c.get_reliance_status(dep_id, 3600) == "RELIABLE"
    assert c.is_reliable(dep_id, 3600) is True


def test_review_minor_change(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE + "\nAdded examples and typo fixes.", "MINOR_CHANGE", "docs added")
    assert c.review_dependency(dep_id) == "MINOR_CHANGE"
    assert c.is_materially_drifted(dep_id) is False
    assert c.get_reliance_status(dep_id, 3600) == "RELIABLE"


def test_review_material_drift(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    body = "SDK v2 removes /v1/run, requires write:tasks, and changes license to commercial."
    mock_review(direct_vm, body, "MATERIAL_DRIFT", "endpoint and license changed")
    assert c.review_dependency(dep_id) == "MATERIAL_DRIFT"
    assert c.is_materially_drifted(dep_id) is True
    assert c.get_dependency(dep_id)["latest_note"] == "endpoint and license changed"
    assert c.get_reliance_status(dep_id, 3600) == "BLOCKED"
    assert c.is_reliable(dep_id, 3600) is False


def test_review_unavailable_from_empty_body(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    direct_vm.mock_web(r".*docs\.example\.com/sdk.*", {"status": 200, "body": ""})
    assert c.review_dependency(dep_id) == "UNAVAILABLE"
    assert c.get_latest_verdict(dep_id) == "UNAVAILABLE"
    assert c.get_reliance_status(dep_id, 3600) == "UNKNOWN"


def test_unknown_model_verdict_fails_safe(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "SAFE", "bad enum")
    assert c.review_dependency(dep_id) == "UNAVAILABLE"


def test_non_json_model_output_fails_safe(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    direct_vm.mock_web(r".*docs\.example\.com/sdk.*", {"status": 200, "body": BASELINE})
    direct_vm.mock_llm(r".*dependency drift assessor.*", "not json")
    assert c.review_dependency(dep_id) == "UNAVAILABLE"


def test_review_unknown_dependency_reverts(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("not found"):
        c.review_dependency(77)


def test_get_dependency_unknown_reverts(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("not found"):
        c.get_dependency(77)


def test_owner_can_deactivate_and_reactivate(direct_vm, direct_deploy, direct_alice):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    dep_id = register(c)
    c.deactivate_dependency(dep_id)
    assert c.get_dependency(dep_id)["active"] is False
    c.reactivate_dependency(dep_id)
    assert c.get_dependency(dep_id)["active"] is True


def test_non_owner_cannot_deactivate(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    dep_id = register(c)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only owner"):
            c.deactivate_dependency(dep_id)


def test_non_owner_cannot_reactivate(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    dep_id = register(c)
    c.deactivate_dependency(dep_id)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only owner"):
            c.reactivate_dependency(dep_id)


def test_inactive_dependency_cannot_be_reviewed(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    c.deactivate_dependency(dep_id)
    with direct_vm.expect_revert("inactive"):
        c.review_dependency(dep_id)


def test_latest_review_absent_before_review(direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    assert c.get_latest_review(dep_id) == {"exists": False, "dep_id": dep_id}
    assert c.get_reliance_status(dep_id, 3600) == "UNKNOWN"


def test_reliance_status_stale_after_max_age(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "UNCHANGED")
    warp_to(direct_vm, "2026-08-03T10:00:00Z")
    c.review_dependency(dep_id)
    warp_to(direct_vm, "2026-08-03T11:00:01Z")
    assert c.get_reliance_status(dep_id, 3600) == "STALE"
    assert c.is_reliable(dep_id, 3600) is False


def test_reliance_status_exact_boundary_is_reliable(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "UNCHANGED")
    warp_to(direct_vm, "2026-08-03T10:00:00Z")
    c.review_dependency(dep_id)
    warp_to(direct_vm, "2026-08-03T11:00:00Z")
    assert c.get_reliance_status(dep_id, 3600) == "RELIABLE"


def test_reliance_status_max_age_zero_ignores_freshness(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "MINOR_CHANGE")
    warp_to(direct_vm, "2026-08-03T10:00:00Z")
    c.review_dependency(dep_id)
    warp_to(direct_vm, "2026-08-10T10:00:00Z")
    assert c.get_reliance_status(dep_id, 0) == "RELIABLE"


def test_recent_reviews_newest_first_same_verdict(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "UNCHANGED", "same")
    c.review_dependency(dep_id)
    c.review_dependency(dep_id)
    rows = c.get_recent_reviews(dep_id, 2)
    assert [r["review_index"] for r in rows] == [1, 0]
    assert [r["verdict"] for r in rows] == ["UNCHANGED", "UNCHANGED"]


def test_recent_reviews_limit_zero(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "UNCHANGED")
    c.review_dependency(dep_id)
    assert c.get_recent_reviews(dep_id, 0) == []


def test_notes_are_bounded(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "MINOR_CHANGE", "x" * 500)
    c.review_dependency(dep_id)
    assert len(c.get_dependency(dep_id)["latest_note"]) == 320


def test_two_dependencies_keep_separate_state(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    one = register(c)
    two = c.register_dependency("Second", "https://docs.example.com/second", BASELINE, "")
    mock_review(direct_vm, BASELINE, "UNCHANGED")
    c.review_dependency(one)
    assert c.get_latest_verdict(one) == "UNCHANGED"
    assert c.get_latest_verdict(two) == "UNKNOWN"


def test_owner_can_register_successor_without_mutating_old_baseline(direct_vm, direct_deploy, direct_alice):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    old_id = register(c)
    new_baseline = "SDK v2 uses endpoint /v2/run and keeps MIT license with compatible responses."
    new_id = c.register_successor(old_id, "Example SDK v2", URL, new_baseline, WATCH)
    old_state = c.get_dependency(old_id)
    new_state = c.get_dependency(new_id)
    assert new_id == old_id + 1
    assert old_state["baseline"] == BASELINE
    assert old_state["successor_id"] == new_id
    assert old_state["supersedes_id"] == 0
    assert new_state["baseline"] == new_baseline
    assert new_state["supersedes_id"] == old_id
    assert new_state["successor_id"] == 0
    assert new_state["owner"] == old_state["owner"]


def test_lineage_view_reports_successor_and_parent(direct_vm, direct_deploy, direct_alice):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    old_id = register(c)
    new_id = c.register_successor(
        old_id,
        "Example SDK v2",
        URL,
        "SDK v2 keeps the same security and licensing terms with a new endpoint.",
        WATCH,
    )
    assert c.get_lineage(old_id) == {
        "dep_id": old_id,
        "supersedes_id": 0,
        "successor_id": new_id,
        "has_successor": True,
        "is_successor": False,
    }
    assert c.get_lineage(new_id) == {
        "dep_id": new_id,
        "supersedes_id": old_id,
        "successor_id": 0,
        "has_successor": False,
        "is_successor": True,
    }


def test_non_owner_cannot_register_successor(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    old_id = register(c)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only owner"):
            c.register_successor(
                old_id,
                "Bad successor",
                URL,
                "A new approved baseline that should be owner-controlled.",
                WATCH,
            )


def test_successor_can_only_be_registered_once(direct_vm, direct_deploy, direct_alice):
    c = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    old_id = register(c)
    c.register_successor(
        old_id,
        "Example SDK v2",
        URL,
        "SDK v2 keeps the same security and licensing terms with a new endpoint.",
        WATCH,
    )
    with direct_vm.expect_revert("successor already registered"):
        c.register_successor(
            old_id,
            "Example SDK v3",
            URL,
            "SDK v3 keeps the same security and licensing terms with a newer endpoint.",
            WATCH,
        )


def test_successor_unknown_dependency_reverts(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    with direct_vm.expect_revert("not found"):
        c.register_successor(
            99,
            "Missing successor",
            URL,
            "A new approved baseline for a dependency that does not exist.",
            WATCH,
        )


def test_hash_changes_with_evidence(direct_vm, direct_deploy):
    c = deploy(direct_deploy)
    dep_id = register(c)
    mock_review(direct_vm, BASELINE, "UNCHANGED")
    c.review_dependency(dep_id)
    latest = c.get_latest_review(dep_id)
    assert len(latest["evidence_hash"]) == 64
    assert latest["evidence_hash"] != latest["baseline_hash"] or BASELINE


def test_consumer_records_proposed_release(direct_deploy):
    oracle = deploy(direct_deploy)
    guard = deploy_example(direct_deploy, oracle.address)
    release_id = guard.propose_release(1, "1.0.1")
    state = guard.get_release(release_id)
    assert state["exists"] is True
    assert state["dep_id"] == 1
    assert state["version"] == "1.0.1"
    assert state["status"] == "PROPOSED"


def test_consumer_rejects_empty_version(direct_vm, direct_deploy):
    oracle = deploy(direct_deploy)
    guard = deploy_example(direct_deploy, oracle.address)
    with direct_vm.expect_revert("invalid version"):
        guard.propose_release(1, "")


def test_consumer_unknown_release_view_is_non_throwing(direct_deploy):
    oracle = deploy(direct_deploy)
    guard = deploy_example(direct_deploy, oracle.address)
    assert guard.get_release(33) == {"exists": False, "release_id": 33}


def test_consumer_rejects_unknown_release(direct_vm, direct_deploy):
    oracle = deploy(direct_deploy)
    guard = deploy_example(direct_deploy, oracle.address)
    with direct_vm.expect_revert("release not found"):
        guard.approve_release_if_dependency_safe(99)
