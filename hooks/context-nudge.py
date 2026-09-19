#!/usr/bin/env python3
"""UserPromptSubmit hook: say how large the session is, so a large session hands off to a fresh one.

Every step Claude takes re-reads the whole conversation. A hook cannot run
/handoff or /clear, so this hook only tells two readers the size: the user sees
a one-line message with the three steps, and Claude gets an instruction to
suggest them when the new request is not part of the current task. Below the
threshold it prints nothing.

The threshold is CONTEXT_NUDGE_TOKENS (default 500000). Keep it equal to
claudeUsageBar.warnTokens, the warning line of the usage bar extension in
vscode/, so the bar and the prompt agree. The kit plugin ships this hook in
hooks/hooks.json, so it runs in every project.
"""
import json
import os
import sys

THRESHOLD = int(os.environ.get("CONTEXT_NUDGE_TOKENS", "500000"))
STEPS = 'run /kit:handoff, then /clear, then say "continue from handoff <topic>"'
# Session logs grow past 50 MB. The newest usage block is near the end, so read
# only the tail.
TAIL_BYTES = 4 * 1024 * 1024


def last_context_tokens(transcript_path: str) -> int | None:
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL_BYTES))
            lines = f.read().decode("utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        usage = (entry.get("message") or {}).get("usage")
        if not usage:
            continue
        return sum(
            usage.get(key) or 0
            for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
        )
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    tokens = last_context_tokens(data.get("transcript_path") or "")
    if tokens is None or tokens < THRESHOLD:
        return
    size = f"{tokens // 1000}k"
    print(json.dumps({
        "systemMessage": f"This session holds about {size} tokens of context. Time to {STEPS}.",
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"Context check: this session holds about {size} tokens, and every step re-reads all of it. "
                "If the new request is not part of the current task, start your reply with one sentence: "
                f"tell the user to {STEPS}. "
                "Then answer the request. If the request continues the current task, do not mention this."
            ),
        },
    }))


if __name__ == "__main__":
    main()
