"""Advance persisted research status and report the next batch (not read-only)."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PHASES = (('framing',), ('places-core', 'places-shopping'), ('places-experiences', 'places-food'), ('itinerary',), ('modules-discovery', 'modules-practical'), ('modules-language-notes',))

def select_phase_batch(pending: list[dict], size: int) -> tuple[int, list[dict]]:
    pending_by_id = {str(item.get('id')): item for item in pending}
    for phase_no, phase_ids in enumerate(PHASES, 1):
        selected = [pending_by_id[item_id] for item_id in phase_ids if item_id in pending_by_id]
        if selected:
            return (phase_no, selected[:size])
    return (len(PHASES), pending[:size])

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('workbench', type=Path)
    parser.add_argument('--batch-size', type=int)
    args = parser.parse_args()
    root = args.workbench.resolve()
    plan_path = root / 'research-plan.json'
    if not plan_path.is_file():
        raise SystemExit('research-plan.json missing; run init_research_workspace.py')
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    pending = []
    complete = 0
    diagnostics = []
    for pack in plan.get('packs', []):
        path = root / pack['file']
        valid_json = False
        if path.is_file():
            try:
                checker = Path(__file__).with_name('validate_research_pack.py')
                error_file = root / '.contract-errors' / f"{pack['id']}.json"
                checked = subprocess.run([sys.executable, str(checker), pack['id'], str(path), '--repair-safe', '--errors', str(error_file)], capture_output=True)
                if checked.returncode:
                    detail = (checked.stdout + checked.stderr).decode('utf-8', errors='replace').strip()
                    diagnostics.append(f"PACK {pack['id']} ({path}):\n{detail or 'validator failed without output'}\nERROR RECORD: {error_file}")
                payload = json.loads(path.read_text(encoding='utf-8-sig'))
                valid_json = checked.returncode == 0 and (not (isinstance(payload, dict) and payload.get('_draft') is True))
            except (OSError, json.JSONDecodeError) as exc:
                diagnostics.append(f"PACK {pack['id']} ({path}): {type(exc).__name__}: {exc}")
                valid_json = False
        if valid_json:
            pack['status'] = 'complete'
            complete += 1
        else:
            pack['status'] = 'pending'
            pending.append(pack)
    plan['status'] = 'ready_for_contract_check' if not pending else 'in_progress'
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    total = len(plan.get('packs', []))
    print(f'RESEARCH FILES {complete}/{total} present')
    for message in diagnostics:
        if message:
            print(message)
    if not pending:
        compiler = Path(__file__).with_name('compile_destination_profile.py')
        result = subprocess.run([sys.executable, str(compiler), str(root)], capture_output=True, text=True, encoding='utf-8', errors='replace')
        output = ((result.stdout or '') + (result.stderr or '')).strip()
        report_path = root / '.contract-errors' / 'compiled-profile.txt'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output + '\n', encoding='utf-8')
        if result.returncode:
            plan['status'] = 'contract_invalid'
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print('RESEARCH CONTRACT INVALID — files exist but required fields are incomplete')
            if output:
                print(output)
            print(f'FULL DIAGNOSTICS: {report_path}')
            print('CONTINUE: fix the named source packs, then rerun research_status.py')
            return 2
        plan['status'] = 'complete'
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # Only the status field changed after a successful official compilation.
        # Bind that final plan state so advance_build does not recompile it again.
        provenance_path = root / 'RESEARCH_PROVENANCE.json'
        if provenance_path.is_file():
            import hashlib
            provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
            provenance['research_plan_sha256'] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
            provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'RESEARCH {complete}/{total} contract-complete')
        if output:
            print(output)
        return 0
    size = max(1, args.batch_size or int(plan.get('batch_size', 2)))
    phase_no, batch = select_phase_batch(pending, size)
    print(f'NEXT BATCH — PHASE {phase_no}/{len(PHASES)}')
    print('PHASE is a dependency barrier. Complete each printed canonical pack as one bounded batch; record-level timers are recovery tools only.')
    for item in batch:
        task_file = root / item.get('task_file', '')
        print(f"- {item['id']}: {item['purpose']} -> {root / item['file']}")
        if task_file.is_file():
            print(f'  task spec: {task_file}')
        checker = Path(__file__).with_name('validate_research_pack.py')
        print(f"  validate immediately: {sys.executable} {checker} {item['id']} {root / item['file']}")
    print('CONTINUE: follow references/production-flow.md; validate each completed pack once, then rerun research_status.py')
    return 2
if __name__ == '__main__':
    raise SystemExit(main())
