"""Helpers for single and composite question answer types."""

from shared.constants import QUESTION_TYPE_COMPOSITE, QUESTION_TYPES


def get_answer_types(question):
    """Return ordered answer component types for a question."""
    types = getattr(question, "answer_types", None)
    if isinstance(types, list) and types:
        return [t for t in types if t in QUESTION_TYPES]
    qtype = getattr(question, "type", None)
    if qtype and qtype != QUESTION_TYPE_COMPOSITE:
        return [qtype]
    return []


def question_has_type(question, qtype):
    return qtype in get_answer_types(question)


def normalize_answer_types(answer_types, fallback_type=None):
    """Validate and normalize answer_types from API input."""
    if answer_types is None:
        if fallback_type in QUESTION_TYPES:
            return [fallback_type], fallback_type
        return None, None

    if not isinstance(answer_types, list) or not answer_types:
        raise ValueError("answer_types must be a non-empty list")

    normalized = []
    for t in answer_types:
        if t not in QUESTION_TYPES:
            raise ValueError(f"Invalid answer type: {t}")
        if t not in normalized:
            normalized.append(t)

    if len(normalized) == 1:
        return normalized, normalized[0]
    return normalized, QUESTION_TYPE_COMPOSITE


def format_type_label(question):
    """Human-readable type label for lists and UI."""
    types = get_answer_types(question)
    if not types:
        return getattr(question, "type", "?")
    if len(types) == 1:
        return types[0].replace("_", " ")
    return " + ".join(t.replace("_", " ") for t in types)
