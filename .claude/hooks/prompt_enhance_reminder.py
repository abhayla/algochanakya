"""
UserPromptSubmit hook — injects prompt-auto-enhance reminder into every turn.

Outputs additionalContext that Claude sees before responding, enforcing the
*Enhanced: ...* indicator rule from .claude/rules/prompt-auto-enhance-rule.md
"""
import json

reminder = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": (
            "MANDATORY BEFORE RESPONDING: Follow prompt-auto-enhance-rule.md.\n"
            "1. Gather Tier 1 context silently: scan .claude/ rules/skills, check git state, review CLAUDE.md.\n"
            "2. Start your response with: *Enhanced: <what was checked>* (max 15 words, italic).\n"
            "3. Only skip the indicator for one-word replies or pure tool-call-only turns.\n"
            "This is NON-NEGOTIABLE for every response."
        )
    }
}

print(json.dumps(reminder))
