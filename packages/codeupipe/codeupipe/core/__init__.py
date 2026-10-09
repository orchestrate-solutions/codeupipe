"""
Core Module: Base Protocols and Classes

The foundation — protocols, abstract base classes, and fundamental types.
"""

from .payload import Payload, MutablePayload
from .shared_payload import SharedPayload, ShmPool
from .filter import AsyncFilter, Filter
from .stream_filter import StreamFilter
from .async_step_in_sync_run import AsyncStepInSyncRun
from .anonymous_step import AnonymousStep
from .pipeline import Pipeline, CircuitOpenError
from .valve import Valve
from .predicate import Predicate
from .tap import AsyncTap, Tap
from .state import State
from .hook import AsyncHook, Hook
from .event import PipelineEvent, EventEmitter
from .govern import (
    PayloadSchema, SchemaViolation, ContractViolation, PipelineTimeoutError,
    AuditEntry, AuditTrail, AuditHook,
    DeadLetterHandler, LogDeadLetterHandler,
)
from .secure import (
    seal_payload, verify_payload, encrypt_data, decrypt_data,
    SecurePayloadError,
)
from .sign_filter import SignFilter
from .verify_filter import VerifyFilter
from .encrypt_filter import EncryptFilter
from .decrypt_filter import DecryptFilter

__all__ = [
    "Payload", "MutablePayload", "SharedPayload", "ShmPool",
    "AsyncFilter", "AsyncHook", "AsyncTap", "Filter", "StreamFilter", "Pipeline", "AsyncStepInSyncRun", "AnonymousStep", "CircuitOpenError", "Valve", "Predicate", "Tap",
    "State", "Hook",
    "PipelineEvent", "EventEmitter",
    # Govern
    "PayloadSchema", "SchemaViolation", "ContractViolation", "PipelineTimeoutError",
    "AuditEntry", "AuditTrail", "AuditHook",
    "DeadLetterHandler", "LogDeadLetterHandler",
    # Secure
    "SignFilter", "VerifyFilter", "EncryptFilter", "DecryptFilter",
    "seal_payload", "verify_payload", "encrypt_data", "decrypt_data",
    "SecurePayloadError",
]
