"""Exercise DependencyReleaseGuard against the latest StudioNet oracle.

Run:
    gltest scripts/studionet_guard_latest.py -v -s --network studionet
"""

import json
from pathlib import Path

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded
from gltest.contracts.contract import Contract
from gltest.utils import extract_contract_address


ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "examples" / "dependency_release_guard.py"
WAIT = {"wait_interval": 5000, "wait_retries": 90}

ORACLE_ADDRESS = "0xe11a825b18df97c6AeC02e26028C54f57C74311a"
SAFE_DEP_ID = 1
LIVE_URL = "https://raw.githubusercontent.com/ometere123/service-uptime-oracle/main/README.md"

MAIN_SCHEMA = {
    "methods": {
        "register_dependency": {"readonly": False},
        "review_dependency": {"readonly": False},
        "get_dependency": {"readonly": True},
        "get_latest_review": {"readonly": True},
        "get_reliance_status": {"readonly": True},
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


def test_guard_against_latest_oracle():
    oracle = Contract.new(address=ORACLE_ADDRESS, schema=MAIN_SCHEMA)
    show("safe dependency before guard", oracle.get_dependency(args=[SAFE_DEP_ID]).call())

    before = oracle.dependency_count().call()
    material_register_receipt = oracle.register_dependency(
        args=[
            "Latest guard material-drift dependency",
            LIVE_URL,
            "This dependency is a decentralized exchange SDK page. It documents "
            "swap routing, token allowances, and an endpoint named /v1/swap. It "
            "does not describe a GenLayer uptime oracle or SLA vault.",
            "dependency identity; endpoint behavior; security model; release gating",
        ]
    ).transact(**WAIT)
    material_register = require_ok("latest oracle register material dependency", material_register_receipt)
    material_dep_id = before + 1

    material_review_receipt = oracle.review_dependency(args=[material_dep_id]).transact(**WAIT)
    material_review = require_ok("latest oracle review material dependency", material_review_receipt)
    material_dep = oracle.get_dependency(args=[material_dep_id]).call()
    show("material dependency", material_dep)
    assert material_dep["latest_verdict"] == "MATERIAL_DRIFT"

    guard_factory = get_contract_factory(contract_file_path=GUARD_PATH)
    guard_deploy_receipt = guard_factory.deploy_contract_tx(args=[ORACLE_ADDRESS], **WAIT)
    guard_deploy = require_ok("deploy latest release guard", guard_deploy_receipt)
    guard_address = extract_contract_address(guard_deploy_receipt)
    guard = Contract.new(address=guard_address, schema=GUARD_SCHEMA)

    safe_propose_receipt = guard.propose_release(args=[SAFE_DEP_ID, "1.0.2"]).transact(**WAIT)
    safe_propose = require_ok("latest guard propose safe release", safe_propose_receipt)
    safe_approve_receipt = guard.approve_release_if_dependency_safe(args=[0]).transact(**WAIT)
    safe_approve = require_ok("latest guard approve safe release", safe_approve_receipt)
    safe_release = guard.get_release(args=[0]).call()
    show("latest guard safe release", safe_release)
    assert safe_release["status"] == "APPROVED"
    assert safe_release["checked_verdict"] == "RELIABLE"

    risky_propose_receipt = guard.propose_release(args=[material_dep_id, "2.0.0"]).transact(**WAIT)
    risky_propose = require_ok("latest guard propose risky release", risky_propose_receipt)
    risky_attempt_receipt = guard.approve_release_if_dependency_safe(args=[1]).transact(**WAIT)
    risky_attempt = risky_attempt_receipt.get("hash") or risky_attempt_receipt.get("tx_id")
    assert not tx_execution_succeeded(risky_attempt_receipt)
    risky_release = guard.get_release(args=[1]).call()
    show(
        "latest guard risky release",
        {"tx": risky_attempt, "receipt": risky_attempt_receipt, "release": risky_release},
    )
    assert risky_release["status"] == "PROPOSED"
    assert risky_release["checked_verdict"] == "UNKNOWN"

    print("\nSUMMARY")
    print(
        json.dumps(
            {
                "oracle": ORACLE_ADDRESS,
                "guard": guard_address,
                "material": {
                    "dep_id": material_dep_id,
                    "register": material_register,
                    "review": material_review,
                    "verdict": material_dep["latest_verdict"],
                },
                "guard_txs": {
                    "deploy": guard_deploy,
                    "safe_propose": safe_propose,
                    "safe_approve": safe_approve,
                    "safe_release": safe_release,
                    "risky_propose": risky_propose,
                    "risky_attempt": risky_attempt,
                    "risky_release": risky_release,
                },
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
