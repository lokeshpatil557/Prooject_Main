from guardrails.hub import ToxicLanguage
from guardrails import Guard

def get_input_guard():
    def custom_fail_handler(failures, value, metadata=None):
        raise ValueError("⚠️ Please use respectful language and avoid toxic content.")

    return Guard().use(
        ToxicLanguage,
        threshold=0.5,
        validation_method="sentence",
        on_fail=custom_fail_handler  
    )


def get_output_guard():
    return Guard().use(
        ToxicLanguage,
        threshold=0.5,
        validation_method="sentence"
    )


def redact_pii(failures, value, metadata=None):
    if isinstance(failures, str):
        return value

    failures.sort(key=lambda x: x.span[0])
    offset = 0
    for failure in failures:
        start, end = failure.span
        if failure.reason == 'PERSON':
            if "Dr." in value[max(0, start - 50):start] or "primary performer" in value[max(0, start - 50):start]:
                continue
            value = value[:start + offset] + "[REDACTED]" + value[end + offset:]
            offset += len("[REDACTED]") - (end - start)
    return value

# def get_output_guard(text):
#     guard = Guard().use(
#         DetectPII(
#             entities=["PERSON"],
#             on_fail=redact_pii
#         )
#     )
#     return guard.validate(text)
