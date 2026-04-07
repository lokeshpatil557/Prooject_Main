import os
import json
from threading import Lock
from typing import Any, Dict, List, Optional

import requests


MEM0_MODE = os.getenv("MEM0_MODE", "local").strip().lower()
MEM0_CONFIG_JSON = os.getenv("MEM0_CONFIG_JSON", "")
MEM0_LOCAL_PATH = os.getenv("MEM0_LOCAL_PATH", ".mem0")
MEM0_COLLECTION = os.getenv("MEM0_COLLECTION", "nursing_bot_memory")
MEM0_BASE_URL = os.getenv("MEM0_BASE_URL", "").rstrip("/")
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_TIMEOUT_SECONDS = int(os.getenv("MEM0_TIMEOUT_SECONDS", "8"))

_MEM0_CLIENT = None
_MEM0_INIT_LOCK = Lock()


def mem0_is_configured() -> bool:
    if MEM0_MODE == "local":
        try:
            from mem0 import Memory  # noqa: F401
            return True
        except Exception:
            return False
    return bool(MEM0_BASE_URL and MEM0_API_KEY)


def _init_local_client():
    global _MEM0_CLIENT
    if _MEM0_CLIENT is not None:
        return _MEM0_CLIENT

    with _MEM0_INIT_LOCK:
        if _MEM0_CLIENT is not None:
            return _MEM0_CLIENT

        from mem0 import Memory

        if MEM0_CONFIG_JSON:
            config = json.loads(MEM0_CONFIG_JSON)
        else:
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": MEM0_COLLECTION,
                        "path": MEM0_LOCAL_PATH,
                    },
                }
            }

            # Optional local model setup if provided
            llm_model = os.getenv("MEM0_LLM_MODEL")
            embed_model = os.getenv("MEM0_EMBED_MODEL")
            ollama_url = os.getenv("MEM0_OLLAMA_BASE_URL")
            if llm_model and ollama_url:
                config["llm"] = {
                    "provider": "ollama",
                    "config": {
                        "model": llm_model,
                        "ollama_base_url": ollama_url,
                        "temperature": 0.1,
                    },
                }
            if embed_model and ollama_url:
                config["embedder"] = {
                    "provider": "ollama",
                    "config": {
                        "model": embed_model,
                        "ollama_base_url": ollama_url,
                    },
                }

        _MEM0_CLIENT = Memory.from_config(config)
        return _MEM0_CLIENT


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {MEM0_API_KEY}",
        "Content-Type": "application/json",
    }


def get_mem0_context(
    *,
    query: str,
    user_id: str,
    org_id: Optional[int] = None,
    department: Optional[str] = None,
    limit: int = 5,
) -> List[str]:
    """
    Fetch relevant memory items from Mem0.
    Returns plain text memory snippets. Never raises to caller.
    """
    if not mem0_is_configured():
        return []

    filters: Dict[str, Any] = {}
    if org_id is not None:
        filters["org_id"] = org_id
    if department:
        filters["department"] = department

    try:
        if MEM0_MODE == "local":
            client = _init_local_client()

            try:
                result = client.search(query=query, user_id=user_id, limit=limit, filters=filters or None)
            except TypeError:
                try:
                    result = client.search(query, user_id=user_id, limit=limit, filters=filters or None)
                except TypeError:
                    mem_filters = {"user_id": user_id}
                    mem_filters.update(filters)
                    result = client.search(query, filters=mem_filters)
        else:
            payload: Dict[str, Any] = {
                "query": query,
                "user_id": user_id,
                "limit": limit,
            }
            if filters:
                payload["filters"] = filters
            resp = requests.post(
                f"{MEM0_BASE_URL}/v1/memories/search",
                headers=_headers(),
                json=payload,
                timeout=MEM0_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            result = resp.json()

        items = result.get("results") if isinstance(result, dict) else result
        if items is None:
            items = []

        memory_lines: List[str] = []
        for item in items:
            if isinstance(item, str):
                memory_lines.append(item)
                continue
            memory_text = item.get("memory") or item.get("text") or item.get("content") or item.get("data")
            if memory_text:
                memory_lines.append(str(memory_text))
        return memory_lines
    except Exception:
        return []


def save_mem0_interaction(
    *,
    user_id: str,
    query: str,
    response: str,
    org_id: Optional[int] = None,
    department: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Store user+assistant interaction to Mem0.
    Never raises to caller.
    """
    if not mem0_is_configured():
        return False

    try:
        merged_metadata = metadata.copy() if metadata else {}
        if org_id is not None:
            merged_metadata["org_id"] = org_id
        if department:
            merged_metadata["department"] = department

        if MEM0_MODE == "local":
            client = _init_local_client()
            messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": response},
            ]
            try:
                client.add(messages=messages, user_id=user_id, metadata=merged_metadata)
            except TypeError:
                try:
                    client.add(messages, user_id=user_id, metadata=merged_metadata)
                except TypeError:
                    content = f"Nurse question: {query}\nAssistant answer: {response}"
                    client.add(content, user_id=user_id, metadata=merged_metadata)
            return True

        content = f"Nurse question: {query}\nAssistant answer: {response}"
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "content": content,
            "metadata": merged_metadata,
        }
        resp = requests.post(
            f"{MEM0_BASE_URL}/v1/memories",
            headers=_headers(),
            json=payload,
            timeout=MEM0_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return True
    except Exception:
        return False
