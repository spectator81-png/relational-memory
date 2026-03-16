"""Relational Memory — a relationship-aware memory layer for LLM chatbots."""

__version__ = "2.1.0"

from .context import assemble_context
from .layers import LayerStore, LAYER_NAMES, MAX_VERSIONS
from .llm import LLMClient, LLMConfigError, LLMAuthError, PROVIDERS
from .signals import (
    extract_signals,
    format_conversation,
    save_signal_log,
    load_signal_log,
    check_stuck_dimensions,
    validate_signals,
)
from .drift import detect_drift, format_drift_warning
from .sleep import condense, should_condense
from .storage import secure_mkdir, secure_write_text, secure_write_json
from .truncation import truncate_messages
from .vector import DIMENSIONS, RelationalVector

__all__ = [
    # Core
    "RelationalVector",
    "DIMENSIONS",
    # LLM
    "LLMClient",
    "LLMConfigError",
    "LLMAuthError",
    "PROVIDERS",
    # Signals
    "extract_signals",
    "format_conversation",
    "save_signal_log",
    "load_signal_log",
    "check_stuck_dimensions",
    "validate_signals",
    # Layers
    "LayerStore",
    "LAYER_NAMES",
    "MAX_VERSIONS",
    # Context
    "assemble_context",
    # Sleep
    "condense",
    "should_condense",
    # Truncation
    "truncate_messages",
    # Drift
    "detect_drift",
    "format_drift_warning",
    # Storage
    "secure_mkdir",
    "secure_write_text",
    "secure_write_json",
]
