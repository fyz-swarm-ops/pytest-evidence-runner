from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class FileHash:
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class RunMetadata:
    python: str
    platform: str
    executable: str


@dataclass(frozen=True)
class EvidenceLog:
    id: str
    stream: str
    path: str | None
    sha256: str
    size_bytes: int
    content: str


@dataclass(frozen=True)
class FailureRecord:
    id: str
    test_case_id: str | None
    kind: str
    message: str
    details: str


@dataclass(frozen=True)
class TestCaseRecord:
    id: str
    session_id: str
    name: str
    classname: str
    status: str
    duration_seconds: float
    stdout: str = ""
    stderr: str = ""
    failure_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TestSession:
    id: str
    command: list[str]
    status: str
    exit_code: int
    started_at: str
    finished_at: str
    duration_seconds: float
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    test_case_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ContainerEnvironment:
    id: str
    image: str
    image_id: str | None
    docker_version: str
    docker_build_id: str | None
    project_mount: str
    evidence_mount: str
    network_disabled: bool
    privileged: bool
    resources: dict[str, str]


@dataclass(frozen=True)
class VerificationReport:
    schema_version: str
    run_id: str
    started_at: str
    finished_at: str
    duration_seconds: float
    workdir: str
    command: list[str]
    exit_code: int
    verdict: str
    failure_kind: str | None
    summary: str
    stdout: str
    stderr: str
    execution_mode: str = "local"
    file_hashes: list[FileHash] = field(default_factory=list)
    metadata: RunMetadata | None = None
    container: ContainerEnvironment | None = None
    test_session: TestSession | None = None
    test_cases: list[TestCaseRecord] = field(default_factory=list)
    failures: list[FailureRecord] = field(default_factory=list)
    logs: list[EvidenceLog] = field(default_factory=list)
    artifacts: list[FileHash] = field(default_factory=list)
    reproduction: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
