# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass

VERDICT_MATERIAL = "MATERIAL_DRIFT"
VERDICT_UNAVAILABLE = "UNAVAILABLE"
ERR_EXPECTED = "EXPECTED"
MAX_RELEASES = 80


@gl.contract_interface
class IDependencyDriftOracle:
    class View:
        def get_latest_verdict(self, dep_id: u256) -> str: ...
        def is_materially_drifted(self, dep_id: u256) -> bool: ...


@allow_storage
@dataclass
class ReleaseRecord:
    dep_id: u256
    version: str
    status: str
    checked_verdict: str
    created_by: Address


class ReleaseProposed(gl.Event):
    def __init__(self, release_id: u256, dep_id: u256, version: str, /, **blob): ...


class ReleaseApproved(gl.Event):
    def __init__(self, release_id: u256, verdict: str, /, **blob): ...


class DependencyReleaseGuard(gl.Contract):
    oracle: Address
    owner: Address
    releases: TreeMap[u256, ReleaseRecord]
    release_count: u256

    def __init__(self, oracle: Address):
        self.oracle = oracle if isinstance(oracle, Address) else Address(oracle)
        self.owner = gl.message.sender_address
        self.release_count = u256(0)

    @gl.public.write
    def propose_release(self, dep_id: u256, version: str) -> u256:
        if len(version) < 1 or len(version) > 80:
            raise gl.vm.UserError(f"{ERR_EXPECTED}: invalid version")
        if int(self.release_count) >= MAX_RELEASES:
            raise gl.vm.UserError(f"{ERR_EXPECTED}: release cap reached")
        release_id = self.release_count
        self.release_count = u256(int(release_id) + 1)
        rec = self.releases.get_or_insert_default(release_id)
        rec.dep_id = dep_id
        rec.version = version
        rec.status = "PROPOSED"
        rec.checked_verdict = "UNKNOWN"
        rec.created_by = gl.message.sender_address
        ReleaseProposed(release_id, dep_id, version).emit()
        return release_id

    @gl.public.write
    def approve_release_if_dependency_safe(self, release_id: u256) -> None:
        if not release_id in self.releases:
            raise gl.vm.UserError(f"{ERR_EXPECTED}: release not found")
        rec = self.releases[release_id]
        if rec.status != "PROPOSED":
            raise gl.vm.UserError(f"{ERR_EXPECTED}: release is closed")
        oracle = gl.get_contract_at(self.oracle)
        verdict = str(oracle.view().get_latest_verdict(rec.dep_id))
        rec.checked_verdict = verdict
        if verdict == VERDICT_MATERIAL or verdict == VERDICT_UNAVAILABLE:
            rec.status = "BLOCKED"
            raise gl.vm.UserError(f"{ERR_EXPECTED}: dependency verdict blocks release")
        rec.status = "APPROVED"
        ReleaseApproved(release_id, verdict).emit()

    @gl.public.view
    def get_release(self, release_id: u256) -> dict:
        if not release_id in self.releases:
            return {"exists": False, "release_id": int(release_id)}
        rec = self.releases[release_id]
        return {
            "exists": True,
            "release_id": int(release_id),
            "dep_id": int(rec.dep_id),
            "version": str(rec.version),
            "status": str(rec.status),
            "checked_verdict": str(rec.checked_verdict),
            "created_by": str(rec.created_by),
        }
