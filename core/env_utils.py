import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def read_env_value(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    if not ENV_PATH.exists():
        return None

    prefix = f"{name}="
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        stripped_line = raw_line.strip()
        if not stripped_line or stripped_line.startswith("#") or not raw_line.startswith(prefix):
            index += 1
            continue

        raw_value = raw_line[len(prefix):]
        if not raw_value:
            return ""

        quote_char = raw_value[0]
        if quote_char not in {"'", '"'}:
            return raw_value.strip() or None

        if len(raw_value) >= 2 and raw_value.endswith(quote_char):
            return raw_value[1:-1]

        parts = [raw_value[1:]]
        index += 1
        while index < len(lines):
            current_line = lines[index]
            if current_line.endswith(quote_char):
                parts.append(current_line[:-1])
                return "\n".join(parts)
            parts.append(current_line)
            index += 1

        return "\n".join(parts)

    return None