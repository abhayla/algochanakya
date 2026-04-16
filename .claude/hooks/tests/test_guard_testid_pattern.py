"""
Unit tests for guard_testid_pattern.py hook.

Run: python .claude/hooks/tests/test_guard_testid_pattern.py
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "guard_testid_pattern.py"


def run_hook(payload: dict) -> tuple:
    """Invoke hook with JSON payload on stdin; return (exit_code, stderr)."""
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stderr


def make_write(file_path: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}


def make_edit(file_path: str, new_string: str) -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": file_path,
            "old_string": "<div>old</div>",
            "new_string": new_string,
        },
    }


CASES = [
    # (label, payload, expected_exit_code)
    (
        "PASS: valid testid on button",
        make_write(
            "frontend/src/views/optionchain/OptionChainView.vue",
            '<template><button data-testid="optionchain-save-btn" @click="save">Save</button></template>',
        ),
        0,
    ),
    (
        "FAIL: missing testid on button",
        make_write(
            "frontend/src/views/optionchain/OptionChainView.vue",
            '<template><button @click="save">Save</button></template>',
        ),
        2,
    ),
    (
        "FAIL: two-segment testid 'btn-clear' (reproduces AIActivityFeed.vue violation)",
        make_write(
            "frontend/src/components/ai/AIActivityFeed.vue",
            '<template><button data-testid="btn-clear" @click="clear">Clear</button></template>',
        ),
        2,
    ),
    (
        "PASS: non-interactive div without testid",
        make_write(
            "frontend/src/views/optionchain/OptionChainView.vue",
            '<template><div class="heading">Hello</div></template>',
        ),
        0,
    ),
    (
        "PASS: dynamic :data-testid binding (pattern not statically validated)",
        make_write(
            "frontend/src/views/optionchain/OptionChainView.vue",
            '<template><button :data-testid="`optionchain-ce-ltp-${strike}`" @click="select">X</button></template>',
        ),
        0,
    ),
    (
        "PASS: v-bind:data-testid form",
        make_write(
            "frontend/src/views/optionchain/OptionChainView.vue",
            '<template><button v-bind:data-testid="dynamicId" @click="go">X</button></template>',
        ),
        0,
    ),
    (
        "PASS: out of scope (backend .py)",
        make_write("backend/app/main.py", 'print("hello")'),
        0,
    ),
    (
        "PASS: out of scope (tests/e2e)",
        make_write("tests/e2e/pages/OptionChainPage.js", "<button>click</button>"),
        0,
    ),
    (
        "PASS: out of scope (.vue outside frontend/src/views or /components)",
        make_write(
            "frontend/src/App.vue",
            '<template><button @click="go">X</button></template>',
        ),
        0,
    ),
    (
        "FAIL: @click on div without testid",
        make_write(
            "frontend/src/components/ai/AIActivityFeed.vue",
            '<template><div @click="doit">Go</div></template>',
        ),
        2,
    ),
    (
        "FAIL: input element without testid (via Edit)",
        make_edit(
            "frontend/src/views/settings/SettingsView.vue",
            '<input type="text" />',
        ),
        2,
    ),
    (
        "PASS: input with valid testid (via Edit)",
        make_edit(
            "frontend/src/views/settings/SettingsView.vue",
            '<input data-testid="settings-email-input" type="text" />',
        ),
        0,
    ),
    (
        "FAIL: select without testid",
        make_write(
            "frontend/src/components/strategy/StrategyForm.vue",
            '<template><select v-model="choice"><option>A</option></select></template>',
        ),
        2,
    ),
    (
        "PASS: select with valid testid",
        make_write(
            "frontend/src/components/strategy/StrategyForm.vue",
            '<template><select data-testid="strategy-broker-select" v-model="choice"><option>A</option></select></template>',
        ),
        0,
    ),
    (
        "PASS: 4-segment testid like autopilot-kill-switch-btn",
        make_write(
            "frontend/src/components/autopilot/KillSwitch.vue",
            '<template><button data-testid="autopilot-kill-switch-btn" @click="kill">K</button></template>',
        ),
        0,
    ),
    (
        "FAIL: @click.stop modifier still counts as interactive",
        make_write(
            "frontend/src/components/ai/AIActivityFeed.vue",
            '<template><div @click.stop="handle">Go</div></template>',
        ),
        2,
    ),
    (
        "PASS: empty Write content (no-op)",
        make_write("frontend/src/views/optionchain/OptionChainView.vue", ""),
        0,
    ),
    (
        "PASS: Edit removes a button (new_string without button is fine)",
        make_edit(
            "frontend/src/views/optionchain/OptionChainView.vue",
            "<div>replaced</div>",
        ),
        0,
    ),
    (
        "PASS: Edit preserves a grandfathered violation verbatim (brownfield)",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "frontend/src/components/ai/AIActivityFeed.vue",
                "old_string": '<button data-testid="btn-clear" @click="clear">Clear</button>',
                "new_string": '<button data-testid="btn-clear" @click="clear">Reset</button>',
            },
        },
        0,
    ),
    (
        "FAIL: Edit introduces a NEW violating button",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "frontend/src/components/ai/AIActivityFeed.vue",
                "old_string": "<div>old</div>",
                "new_string": '<button @click="foo">New</button>',
            },
        },
        2,
    ),
    (
        "FAIL: Edit mutates grandfathered violation into a different-but-still-invalid one",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "frontend/src/components/ai/AIActivityFeed.vue",
                "old_string": '<button data-testid="btn-clear" @click="clear">C</button>',
                "new_string": '<button data-testid="btn-refresh" @click="refresh">R</button>',
            },
        },
        2,
    ),
]


def main() -> int:
    failures = []
    for label, payload, expected in CASES:
        code, stderr = run_hook(payload)
        ok = code == expected
        status = "OK" if ok else "BAD"
        print(f"[{status}] {label}")
        if not ok:
            failures.append(label)
            print(f"      expected exit {expected}, got {code}")
            if stderr.strip():
                first_line = stderr.strip().splitlines()[0]
                print(f"      stderr: {first_line[:160]}")

    print()
    if failures:
        print(f"FAILED: {len(failures)} / {len(CASES)}")
        for label in failures:
            print(f"   - {label}")
        return 1
    print(f"OK: all {len(CASES)} cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
