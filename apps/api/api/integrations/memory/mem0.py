from __future__ import annotations

# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOptionalCall=false, reportPrivateUsage=false
from dataclasses import dataclass
from typing import Any

from api.config import Settings
from api.executors.contracts import EvidenceRef, MemoryType, MemoryWriteCandidate

try:
    from mem0 import MemoryClient
except ImportError:  # pragma: no cover - dependency is installed in runtime
    MemoryClient = None


@dataclass(slots=True)
class Mem0WriteResult:
    success: bool
    external_ref: str
    provider: str = "mem0"
    memory_id: str | None = None
    error_message: str | None = None
    retryable: bool = False


class Mem0MemoryAdapter:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self._settings.mem0_api_key)

    def write(
        self,
        *,
        candidate: MemoryWriteCandidate,
        namespace: str,
        existing_external_ref: str | None = None,
    ) -> Mem0WriteResult:
        if not self.configured:
            return Mem0WriteResult(
                success=False,
                external_ref=candidate.external_ref,
                error_message="mem0 not configured",
            )

        try:
            client = self._get_client()
            metadata = self._build_metadata(candidate, namespace)
            existing_memory_id = self._memory_id_from_ref(existing_external_ref)
            if existing_memory_id:
                payload = client.update(
                    existing_memory_id,
                    text=candidate.summary,
                    metadata=metadata,
                )
                memory_id = self._extract_memory_id(payload, fallback=existing_memory_id)
                return Mem0WriteResult(
                    success=True,
                    external_ref=self._external_ref(memory_id),
                    memory_id=memory_id,
                )

            payload = client.add(
                candidate.summary,
                filters={
                    "user_id": candidate.project_id,
                    "agent_id": namespace,
                },
                metadata=metadata,
                infer=False,
            )
            memory_id = self._extract_memory_id(payload)
            return Mem0WriteResult(
                success=True,
                external_ref=self._external_ref(memory_id),
                memory_id=memory_id,
            )
        except Exception as exc:
            return Mem0WriteResult(
                success=False,
                external_ref=candidate.external_ref,
                error_message=str(exc),
                retryable=self._is_retryable(exc),
            )

    def recall(
        self,
        *,
        project_id: str,
        namespace_prefix: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not self.configured:
            return []

        client = self._get_client()
        payload = client.get_all(
            filters={"user_id": project_id},
            page_size=max(limit * 3, limit),
        )
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            return []

        matches: list[dict[str, Any]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata")
            metadata_dict = metadata if isinstance(metadata, dict) else {}
            namespace = str(metadata_dict.get("namespace") or "")
            if namespace_prefix and not namespace.startswith(namespace_prefix):
                continue
            matches.append(item)
            if len(matches) >= limit:
                break
        return matches

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if MemoryClient is None:
            raise RuntimeError("mem0 client dependency is not installed")
        self._client = MemoryClient(
            api_key=self._settings.mem0_api_key,
            host=self._settings.mem0_api_url,
        )
        return self._client

    @staticmethod
    def _build_metadata(candidate: MemoryWriteCandidate, namespace: str) -> dict[str, Any]:
        return {
            **dict(candidate.metadata),
            "project_id": candidate.project_id,
            "iteration_id": candidate.iteration_id,
            "namespace": namespace,
            "memory_type": str(candidate.memory_type),
            "external_ref": candidate.external_ref,
            "content_hash": candidate.content_hash,
            "quality_score": candidate.quality_score,
            "retention_policy": str(candidate.retention_policy),
            "summary": candidate.summary,
            "evidence_refs": [ref.model_dump(mode="json") for ref in candidate.evidence_refs],
            "supersedes_record_id": candidate.supersedes_record_id,
        }

    @staticmethod
    def _extract_memory_id(payload: object, fallback: str | None = None) -> str | None:
        if isinstance(payload, dict):
            if isinstance(payload.get("id"), str):
                return payload["id"]
            results = payload.get("results")
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict) and isinstance(item.get("id"), str):
                        return item["id"]
        return fallback

    @staticmethod
    def _memory_id_from_ref(external_ref: str | None) -> str | None:
        if not external_ref or not external_ref.startswith("mem0://memories/"):
            return None
        memory_id = external_ref.removeprefix("mem0://memories/").strip()
        return memory_id or None

    @staticmethod
    def _external_ref(memory_id: str | None) -> str:
        if memory_id:
            return f"mem0://memories/{memory_id}"
        return "mem0://memories/unknown"

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in ("timeout", "timed out", "connect", "503", "429"))


def map_mem0_item(
    *,
    item: dict[str, Any],
    project_id: str,
    namespace_prefix: str | None = None,
) -> dict[str, Any]:
    metadata = item.get("metadata")
    metadata_dict = metadata if isinstance(metadata, dict) else {}
    evidence_refs = metadata_dict.get("evidence_refs")
    normalized_refs = (
        [EvidenceRef.model_validate(ref) for ref in evidence_refs if isinstance(ref, dict)]
        if isinstance(evidence_refs, list)
        else []
    )
    namespace = str(metadata_dict.get("namespace") or namespace_prefix or f"{project_id}:mem0")
    memory_type_value = str(metadata_dict.get("memory_type") or "")
    try:
        memory_type = MemoryType(memory_type_value or MemoryType.LONG_TERM_KNOWLEDGE.value)
    except ValueError:
        memory_type = MemoryType.LONG_TERM_KNOWLEDGE
    summary = str(
        item.get("memory")
        or item.get("text")
        or metadata_dict.get("summary")
        or "Mem0 memory"
    )
    quality_score = float(metadata_dict.get("quality_score") or item.get("score") or 0.5)
    external_ref = str(
        metadata_dict.get("external_ref")
        or Mem0MemoryAdapter._external_ref(str(item.get("id") or "unknown"))
    )
    return {
        "record_id": str(item.get("id") or external_ref),
        "project_id": project_id,
        "iteration_id": (
            str(metadata_dict["iteration_id"])
            if metadata_dict.get("iteration_id") is not None
            else None
        ),
        "namespace": namespace,
        "memory_type": memory_type,
        "external_ref": external_ref,
        "summary": summary,
        "content_hash": str(metadata_dict.get("content_hash") or item.get("id") or summary),
        "score": quality_score,
        "quality_score": quality_score,
        "evidence_refs": normalized_refs,
        "metadata": {
            **metadata_dict,
            "provider": "mem0",
            "remote": True,
        },
    }
