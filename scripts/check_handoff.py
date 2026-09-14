#!/usr/bin/env python3
"""Hard release gate: success means a final guide handoff is allowed."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _build_state import QA_NAME, evaluate, load_json, print_state, save


def preview_export_allowed(root: Path, state: dict) -> bool:
    """Allow a portable preview, never promote an unobserved QA result."""
    if not (state.get('stage') == 'browser_qa_required'
            and state.get('response_state') == 'waiting_for_review'
            and state.get('final_response_allowed') is True):
        return False
    required = ('research_pass', 'profile_preflight_pass', 'asset_machine_preflight',
                'assets_verified', 'strict_audit_pass', 'forward_test_pass')
    if not all(state.get('checks', {}).get(key) is True for key in required):
        return False
    from _manual_qa import build_fingerprint
    qa = load_json(root / QA_NAME)
    if qa.get('status') != 'pending' or qa.get('build_fingerprint') != build_fingerprint(root):
        return False
    if qa.get('validation_mode') == 'manual_representative':
        return qa.get('user_authorized') is True
    limitation = qa.get('host_limitation', {})
    return (qa.get('validation_mode') == 'unavailable'
            and isinstance(limitation, dict)
            and all(isinstance(limitation.get(key), str) and limitation[key].strip()
                    for key in ('reason', 'tool_reference', 'checked_at')))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbench", type=Path)
    args = parser.parse_args()
    root = args.workbench.resolve()
    state = evaluate(root, run_gates=True)
    preview_export = preview_export_allowed(root, state)
    if state['stage'] == 'offline_export_required' or preview_export:
        from package_handbook import package
        from _offline_qa import export_state, read
        try:
            export_stage, _, _ = export_state(root)
            if export_stage == 'offline_export_required':
                artifact = package(root)
                print(f'EXPORTED FOR QA: {artifact}')
                state = evaluate(root, run_gates=True)
            else:
                artifact = Path(read(root / 'offline-export.json')['file'])
            if preview_export_allowed(root, state):
                print(f'PREVIEW OPEN / DOWNLOAD (QA pending): {artifact}')
                print('自包含 HTML 已生成；浏览器验证仍待完成，不能声称完整交付。')
        except (ValueError, OSError) as exc:
            state.update(handoff_allowed=False, final_response_allowed=False, continuation_required=True,
                         status='in_progress', response_state='in_progress', user_input_required=False,
                         next_action_kind='bounded_agent_work',
                         final_response_guard='forbidden_until_valid_export',
                         next_required_action='Repair the reported offline export dependency or write failure, then rerun check_handoff.py. Browser QA remains pending; do not repeat research or bypass an access denial.',
                         next_command=f'"{sys.executable}" "{Path(__file__).resolve()}" "{root}"')
            state['evidence']['offline_export'] = str(exc)
    save(args.workbench, state)
    print_state(state)
    dimensions = state.get("audit_dimensions", {})
    for name in ("structure", "research", "media"):
        print(f"{name.upper()} {'PASS' if dimensions.get(name) is True else 'FAIL'}")
    handbook_state_ok = state.get("checks", {}).get("trip_decisions_recorded") is True
    print(f"HANDBOOK-STATE {'PASS' if handbook_state_ok else 'FAIL'}")
    if not state["handoff_allowed"]:
        print("HANDOFF BLOCKED: perform the printed next action; do not send a completion final response.")
        return 3
    cache = Path(__file__).with_name("plan_incremental_validation.py")
    result = subprocess.run([sys.executable, str(cache), str(args.workbench.resolve()), "--write"])
    if result.returncode:
        state.update(handoff_allowed=False, final_response_allowed=False, continuation_required=True,
                     status='in_progress', response_state='in_progress')
        state['evidence']['validation_cache'] = 'Could not record incremental validation cache.'
        save(args.workbench, state)
        print("HANDOFF BLOCKED: incremental validation cache could not be recorded.")
        return result.returncode
    # Deliver exactly the hash-verified artifact; do not regenerate after its QA.
    from _offline_qa import read
    archive = Path(read(args.workbench / 'offline-export.json')['file'])
    print(f"OPEN / DOWNLOAD (self-contained): {archive}")
    print(f"WORKBENCH ENTRY (requires sibling assets; never attach alone): {args.workbench.resolve() / 'index.html'}")
    print(f"OFFLINE HTML: {archive}")
    print("双击离线 HTML 即可在本地离线打开，无需解压。")
    print("HANDOFF ALLOWED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
