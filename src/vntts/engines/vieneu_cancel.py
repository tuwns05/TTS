"""Cooperative frame-boundary cancellation for VieNeu v3 Turbo 3.2.x.

VieNeu 3.2.x accepts extra arguments at its public ``infer`` boundary but does
not yet carry a cancellation token into its ONNX and PyTorch generation loops.
This adapter keeps the SDK's single ``infer`` call and static batching intact,
while checking the caller's exact ``Event`` immediately before each next frame.
"""

from __future__ import annotations

import importlib
from concurrent.futures import CancelledError
from contextvars import ContextVar
from functools import wraps
from inspect import Parameter, signature
from threading import Event
from types import MethodType
from typing import Any

_CURRENT_CANCEL_EVENT: ContextVar[Event | None] = ContextVar(
    "vieneu_cancel_event",
    default=None,
)
_PATCH_MARKER = "__vntts_cancel_event_support__"


def _raise_if_cancelled() -> None:
    cancel_event = _CURRENT_CANCEL_EVENT.get()
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError()


def _accepts_keyword(function: object, keyword: str) -> bool:
    try:
        parameters = signature(function).parameters.values()  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == keyword or parameter.kind is Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _patch_frame_method(owner: type[Any], method_name: str) -> None:
    original = getattr(owner, method_name, None)
    if not callable(original) or getattr(original, _PATCH_MARKER, False):
        return

    @wraps(original)
    def checked(self: object, *args: object, **kwargs: object) -> object:
        _raise_if_cancelled()
        return original(self, *args, **kwargs)

    setattr(checked, _PATCH_MARKER, True)
    setattr(owner, method_name, checked)


def _patch_batch_engine(batch_engine: object) -> None:
    """Patch both regular and CUDA-graph static-batch frame boundaries."""

    try:
        engine_module = importlib.import_module(type(batch_engine).__module__)
    except (ImportError, ValueError):
        return

    original_frame = getattr(engine_module, "generate_frame_batched", None)
    if callable(original_frame) and not getattr(original_frame, _PATCH_MARKER, False):

        @wraps(original_frame)
        def checked_frame(*args: object, **kwargs: object) -> object:
            _raise_if_cancelled()
            return original_frame(*args, **kwargs)

        setattr(checked_frame, _PATCH_MARKER, True)
        engine_module.generate_frame_batched = checked_frame

    package_name, _, _ = type(batch_engine).__module__.rpartition(".")
    if not package_name:
        return
    try:
        graph_module = importlib.import_module(f"{package_name}.cudagraph")
    except ImportError:
        return
    graph_type = getattr(graph_module, "CudaGraphedFrame", None)
    if isinstance(graph_type, type):
        _patch_frame_method(graph_type, "run")


def install_vieneu_cancel_support(runtime: object) -> None:
    """Teach one VieNeu v3 runtime to honor an optional ``cancel_event``.

    The public runtime receives the event normally as a keyword argument. A
    context-local reference then reaches the SDK's frame kernels without
    changing scheduling, chunking, batch membership, or model residency.
    """

    if getattr(runtime, _PATCH_MARKER, False):
        return

    original_infer = getattr(runtime, "infer", None)
    if not callable(original_infer):
        return
    forwards_cancel_event = _accepts_keyword(original_infer, "cancel_event")

    @wraps(original_infer)
    def infer(
        *args: object,
        cancel_event: Event | None = None,
        **kwargs: object,
    ) -> object:
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError()
        token = _CURRENT_CANCEL_EVENT.set(cancel_event)
        try:
            if forwards_cancel_event and cancel_event is not None:
                kwargs["cancel_event"] = cancel_event
            return original_infer(*args, **kwargs)
        finally:
            _CURRENT_CANCEL_EVENT.reset(token)

    setattr(infer, _PATCH_MARKER, True)
    runtime.infer = infer

    engine = getattr(runtime, "engine", None)
    if engine is not None:
        _patch_frame_method(type(engine), "_acoustic_frame")
        model = getattr(engine, "model", None)
        if model is not None:
            _patch_frame_method(type(model), "decode_one_frame")

    original_get_batch_engine = getattr(runtime, "_get_batch_engine", None)
    if callable(original_get_batch_engine):

        @wraps(original_get_batch_engine)
        def get_batch_engine(self: object) -> object:
            batch_engine = original_get_batch_engine()
            if batch_engine is not None:
                _patch_batch_engine(batch_engine)
            return batch_engine

        runtime._get_batch_engine = MethodType(get_batch_engine, runtime)

    existing_batch_engine = getattr(runtime, "_batch_engine", None)
    if existing_batch_engine is not None:
        _patch_batch_engine(existing_batch_engine)
    setattr(runtime, _PATCH_MARKER, True)
