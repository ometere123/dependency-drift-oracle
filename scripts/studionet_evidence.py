"""Deploy and exercise DependencyDriftOracle on StudioNet.

Run:
    gltest scripts/studionet_evidence.py -v -s --network studionet
"""

import json
from pathlib import Path

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded
from gltest.contracts.contract import Contract
from gltest.utils import extract_contract_address


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "contracts" / "dependency_drift_oracle.py"
GUARD_PATH = ROOT / "examples" / "dependency_release_guard.py"
WAIT = {"wait_interval": 5000, "wait_retries": 90}

LIVE_URL = "https://raw.githubusercontent.com/ometere123/service-uptime-oracle/main/README.md"
BAD_URL = "https://nonexistent-dependency-drift-oracle.invalid/readme"

MAIN_SCHEMA = {
    "methods": {
        "register_dependency": {"readonly": False},
        "review_dependency": {"readonly": False},
        "deactivate_dependency": {"readonly": False},
        "reactivate_dependency": {"readonly": False},
        "get_dependency": {"readonly": True},
        "get_latest_review": {"readonly": True},
        "get_latest_verdict": {"readonly": True},
        "get_reliance_status": {"readonly": True},
        "is_reliable": {"readonly": True},
        "is_materially_drifted": {"readonly": True},
        "dependency_count": {"readonly": True},
    }
}

GUARD_SCHEMA = {
    "methods": {
        "propose_release": {"readonly": False},
        "approve_release_if_dependency_safe": {"readonly": False},
        "get_release": {"readonly": True},
    }
}


def show(label, value):
    print(f"\n[{label}]\n{json.dumps(value, indent=2, sort_keys=True, default=str)}")


def require_ok(label, receipt):
    assert tx_execution_succeeded(receipt), label
    tx_hash = receipt.get("hash") or receipt.get("tx_id")
    print(f"{label}: {tx_hash}")
    return tx_hash


def register(contract, name, url, baseline, watch_terms):
    before = contract.dependency_count().call()
    receipt = contract.register_dependency(
        args=[name, url, baseline, watch_terms]
    ).transact(**WAIT)
    tx_hash = require_ok(f"register_dependency {name}", receipt)
    dep_id = before + 1
    show(f"dependency {dep_id}", contract.get_dependency(args=[dep_id]).call())
    return dep_id, tx_hash


def review(contract, dep_id, label):
    receipt = contract.review_dependency(args=[dep_id]).transact(**WAIT)
    tx_hash = require_ok(f"review_dependency {label}", receipt)
    dep = contract.get_dependency(args=[dep_id]).call()
    latest = contract.get_latest_review(args=[dep_id]).call()
    show(f"review {label}", {"dependency": dep, "latest": latest})
    return tx_hash, dep["latest_verdict"]


def test_studionet_evidence():
    factory = get_contract_factory(contract_file_path=MAIN_PATH)
    deploy_receipt = factory.deploy_contract_tx(**WAIT)
    deploy_tx = require_ok("deploy oracle", deploy_receipt)
    main_address = extract_contract_address(deploy_receipt)
    oracle = Contract.new(address=main_address, schema=MAIN_SCHEMA)

    unchanged_id, unchanged_register = register(
        oracle,
        "ServiceUptimeOracle README baseline",
        LIVE_URL,
        "The README describes ServiceUptimeOracle, a GenLayer uptime/SLA primitive, "
        "with an SLA vault example and StudioNet evidence.",
        "project purpose; SLA vault example; StudioNet evidence; uptime oracle",
    )
    unchanged_review, unchanged_verdict = review(oracle, unchanged_id, "unchanged")

    material_id, material_register = register(
        oracle,
        "Intentionally stale integration baseline",
        LIVE_URL,
        "This dependency is a decentralized exchange SDK. It has no uptime oracle, "
        "no SLA vault, no StudioNet deployment evidence, and no service monitoring behavior.",
        "project purpose; service monitoring behavior; SLA vault; deployment evidence",
    )
    material_review, material_verdict = review(oracle, material_id, "material")

    unavailable_id, unavailable_register = register(
        oracle,
        "Unavailable dependency URL",
        BAD_URL,
        "A dependency page that should describe a stable API integration.",
        "availability; API behavior",
    )
    unavailable_review, unavailable_verdict = review(oracle, unavailable_id, "unavailable")

    deactivate_tx = require_ok(
        "deactivate_dependency",
        oracle.deactivate_dependency(args=[unavailable_id]).transact(**WAIT),
    )
    reactivate_tx = require_ok(
        "reactivate_dependency",
        oracle.reactivate_dependency(args=[unavailable_id]).transact(**WAIT),
    )

    guard_factory = get_contract_factory(contract_file_path=GUARD_PATH)
    guard_deploy_receipt = guard_factory.deploy_contract_tx(args=[main_address], **WAIT)
    guard_deploy = require_ok("deploy release guard", guard_deploy_receipt)
    guard_address = extract_contract_address(guard_deploy_receipt)
    guard = Contract.new(address=guard_address, schema=GUARD_SCHEMA)

    safe_release_receipt = guard.propose_release(args=[unchanged_id, "1.0.1"]).transact(**WAIT)
    safe_release_tx = require_ok("guard propose safe release", safe_release_receipt)
    safe_release_id = 0
    guard_approve_tx = require_ok(
        "guard approve safe release",
        guard.approve_release_if_dependency_safe(args=[safe_release_id]).transact(**WAIT),
    )
    safe_release = guard.get_release(args=[safe_release_id]).call()
    show("safe release", safe_release)

    risky_release_receipt = guard.propose_release(args=[material_id, "2.0.0"]).transact(**WAIT)
    risky_release_tx = require_ok("guard propose risky release", risky_release_receipt)
    risky_release_id = 1
    risky_result = guard.approve_release_if_dependency_safe(args=[risky_release_id]).transact(**WAIT)
    risky_tx = risky_result.get("hash") or risky_result.get("tx_id")
    risky_release = guard.get_release(args=[risky_release_id]).call()
    show("risky release", {"tx": risky_tx, "receipt": risky_result, "release": risky_release})

    print("\nSUMMARY")
    print(
        json.dumps(
            {
                "oracle": main_address,
                "guard": guard_address,
                "oracle_deploy": deploy_tx,
                "unchanged": {
                    "dep_id": unchanged_id,
                    "register": unchanged_register,
                    "review": unchanged_review,
                    "verdict": unchanged_verdict,
                },
                "material": {
                    "dep_id": material_id,
                    "register": material_register,
                    "review": material_review,
                    "verdict": material_verdict,
                },
                "unavailable": {
                    "dep_id": unavailable_id,
                    "register": unavailable_register,
                    "review": unavailable_review,
                    "verdict": unavailable_verdict,
                    "deactivate": deactivate_tx,
                    "reactivate": reactivate_tx,
                },
                "guard": {
                    "deploy": guard_deploy,
                    "safe_release_propose": safe_release_tx,
                    "safe_release_approve": guard_approve_tx,
                    "safe_release": safe_release,
                    "risky_release_propose": risky_release_tx,
                    "risky_release_attempt": risky_tx,
                    "risky_release": risky_release,
                },
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
