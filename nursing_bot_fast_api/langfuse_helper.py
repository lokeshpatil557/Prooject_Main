import logging
import os
from contextlib import contextmanager, nullcontext
from typing import Any, Dict, Iterator, Optional

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger("main_logger")


class _NoOpObservation:
    def update(self, **kwargs: Any) -> None:
        return None


@contextmanager
def _noop_observation() -> Iterator[_NoOpObservation]:
    yield _NoOpObservation()


_langfuse_client = None
_langfuse_propagate_attributes = None
_langfuse_load_error = None


def _has_langfuse_credentials() -> bool:
    return bool(
        os.getenv("LANGFUSE_PUBLIC_KEY")
        and os.getenv("LANGFUSE_SECRET_KEY")
        and (os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL"))
    )


def _stringify_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    if not metadata:
        return None

    sanitized: Dict[str, str] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        text_value = value if isinstance(value, str) else str(value)
        sanitized[str(key)] = text_value[:200]

    return sanitized or None


def get_langfuse_client():
    global _langfuse_client, _langfuse_propagate_attributes, _langfuse_load_error

    if _langfuse_client is not None:
        return _langfuse_client

    if _langfuse_load_error is not None:
        return None

    if not _has_langfuse_credentials():
        return None

    try:
        from langfuse import Langfuse, propagate_attributes

        _langfuse_client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            base_url=os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST"),
            environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "local"),
        )
        _langfuse_propagate_attributes = propagate_attributes
        logger.info("Langfuse tracing is enabled.")
        return _langfuse_client
    except Exception as exc:
        _langfuse_load_error = exc
        logger.warning("Langfuse is configured but could not be initialized: %s", exc)
        return None


def langfuse_status() -> Dict[str, Any]:
    client = get_langfuse_client()
    return {
        "enabled": client is not None,
        "configured": _has_langfuse_credentials(),
        "sdk_loaded": client is not None,
        "error": str(_langfuse_load_error) if _langfuse_load_error else None,
        "base_url": os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST"),
        "environment": os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "local"),
    }


@contextmanager
def langfuse_trace_context(
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Iterator[None]:
    get_langfuse_client()

    if _langfuse_propagate_attributes is None:
        with nullcontext():
            yield
        return

    trace_kwargs: Dict[str, Any] = {}
    if user_id:
        trace_kwargs["user_id"] = user_id
    if session_id:
        trace_kwargs["session_id"] = session_id
    sanitized_metadata = _stringify_metadata(metadata)
    if sanitized_metadata:
        trace_kwargs["metadata"] = sanitized_metadata

    with _langfuse_propagate_attributes(**trace_kwargs):
        yield


@contextmanager
def start_langfuse_observation(
    *,
    name: str,
    as_type: str = "span",
    input_data: Any = None,
    output_data: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    model_parameters: Optional[Dict[str, Any]] = None,
) -> Iterator[Any]:
    client = get_langfuse_client()
    if client is None:
        with _noop_observation() as observation:
            yield observation
        return

    observation_kwargs: Dict[str, Any] = {
        "name": name,
        "as_type": as_type,
    }
    if input_data is not None:
        observation_kwargs["input"] = input_data
    if output_data is not None:
        observation_kwargs["output"] = output_data
    if metadata is not None:
        observation_kwargs["metadata"] = metadata
    if model is not None:
        observation_kwargs["model"] = model
    if model_parameters is not None:
        observation_kwargs["model_parameters"] = model_parameters

    try:
        observation_manager = client.start_as_current_observation(**observation_kwargs)
    except Exception as exc:
        logger.warning("Langfuse observation '%s' failed: %s", name, exc)
        with _noop_observation() as observation:
            yield observation
        flush_langfuse()
        return

    try:
        with observation_manager as observation:
            yield observation
    finally:
        flush_langfuse()


def flush_langfuse() -> None:
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception as exc:
        logger.warning("Langfuse flush failed: %s", exc)
