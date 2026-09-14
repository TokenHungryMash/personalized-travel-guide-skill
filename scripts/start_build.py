"""Create a resumable travel-handbook build state."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from _build_state import DECISIONS_NAME, STATE_NAME, now, print_state, save
from runtime_preflight import ensure_runtime
from _travel_brief import resolve_brief
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')

def main() -> int:
    skill_root = ensure_runtime()
    parser = argparse.ArgumentParser()
    parser.add_argument('workbench', type=Path)
    parser.add_argument('--destination')
    parser.add_argument('--country')
    parser.add_argument('--start-date')
    parser.add_argument('--days', type=int)
    parser.add_argument('--brief-file', type=Path, help='current approved user brief as a JSON object; no destination research is imported')
    parser.add_argument('--travelers', help='explicit traveler count or description; otherwise preserve the brief')
    parser.add_argument('--rhythm', help='explicit pace; otherwise preserve the brief')
    parser.add_argument('--budget-level')
    parser.add_argument('--budget-total')
    parser.add_argument('--local-daily-budget', help='local daily budget per traveler')
    approval = parser.add_mutually_exclusive_group(required=True)
    approval.add_argument('--itinerary-approved', action='store_true', help='the user approved the displayed itinerary proposal')
    approval.add_argument('--discussion-waived', action='store_true', help='the user explicitly asked to skip itinerary discussion and generate directly')
    parser.add_argument('--user-statement', required=True, help='verbatim user statement that approved the proposal or waived discussion')
    parser.add_argument('--force-new-workbench', action='store_true', help='explicitly allow a second active workbench for the same trip')
    parser.add_argument('--cold-start', action='store_true', help='explicit user-requested independent rebuild; require an empty target and do not resume prior work')
    args = parser.parse_args()
    user_statement = args.user_statement.strip()
    if not user_statement:
        raise SystemExit('--user-statement must contain the user\'s actual approval or waiver; generated or inferred consent is invalid')
    if user_statement.strip('。.!！?？ \t\r\n') in {'按默认', '默认', '使用默认', '按默认来', '先给草案', '先给行程草案'}:
        raise SystemExit('intake/default permission is not itinerary approval; show the proposal and wait for the user')
    root = args.workbench.resolve()
    if args.cold_start and root.exists() and any(root.iterdir()):
        raise SystemExit('COLD START requires a new empty workbench; choose a fresh path, never delete or reuse its contents')
    state_path = root / STATE_NAME
    if state_path.exists():
        raise SystemExit(f'build state already exists: {state_path}; use advance_build.py')
    brief = resolve_brief(root, brief_file=args.brief_file, require_country=False, overrides={
        'destination': args.destination, 'country': args.country, 'start_date': args.start_date,
        'days': args.days, 'travelers': args.travelers, 'rhythm': args.rhythm,
        'budget_level': args.budget_level, 'budget_total': args.budget_total,
        'local_daily_budget': args.local_daily_budget,
    })
    args.destination, args.country, args.start_date, args.days = (brief[key] for key in ('destination', 'country', 'start_date', 'days'))
    if not (args.force_new_workbench or args.cold_start) and root.parent.is_dir():
        matches = []
        for candidate in root.parent.glob(f'*/{STATE_NAME}'):
            try:
                prior = json.loads(candidate.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            prior_start = str(prior.get('start_date', 'pending') or 'pending')
            requested_start = str(args.start_date or 'pending')
            requested_compact = requested_start.replace('-', '')
            dates_compatible = prior_start == requested_start or requested_start == 'pending'
            if prior_start == 'pending' and requested_start != 'pending':
                dates_compatible = requested_compact in candidate.parent.name.replace('-', '')
            if prior.get('destination') == args.destination.strip() and dates_compatible and (int(prior.get('days', 0) or 0) == args.days) and (prior.get('handoff_allowed') is not True):
                matches.append((candidate.parent.resolve(), prior))
        if matches:
            existing, existing_state = max(matches, key=lambda item: (item[0] / STATE_NAME).stat().st_mtime)
            original_root = str(existing_state.get('skill_root', '') or '').strip()
            resume_root = Path(original_root).resolve() if original_root else skill_root
            resume_script = resume_root / 'scripts' / 'advance_build.py'
            message = f'ACTIVE BUILD EXISTS — resume it instead of creating retry/V2/V3 directories.\nACTIVE_WORKBENCH: {existing}'
            if resume_script.is_file():
                command = [sys.executable, str(resume_script), str(existing), '--run']
                message += '\nCONTINUE_ARGV: ' + json.dumps(command, ensure_ascii=False)
                message += f'\nNEXT_COMMAND: "{sys.executable}" "{resume_script}" "{existing}" --run'
            else:
                message += f'\nORIGINAL SKILL UNAVAILABLE: {resume_root}\nRestore that Skill copy before resuming this workbench; do not substitute another version or reset the existing build.'
            raise SystemExit(message + '\nUse --force-new-workbench only when the user explicitly requested an independent rebuild.')
    if args.days < 1:
        raise SystemExit('--days must be positive')
    budget = brief.get('budget') if isinstance(brief.get('budget'), dict) else {}
    decisions = {'schema_version': 1, 'flight': {'status': 'pending'}, 'stay': {'status': 'pending'}, 'budget_plan': {'level': brief.get('budget_level', budget.get('level', '')), 'total_trip': brief.get('budget_total', budget.get('total_trip', '')), 'local_per_person_day': brief.get('local_daily_budget', budget.get('local_per_person_day', ''))}, 'updated_at': now()}
    root.mkdir(parents=True, exist_ok=True)
    (root / 'travel-brief.json').write_text(json.dumps(brief, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (root / DECISIONS_NAME).write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    approval_record = {
        'status': 'approved' if args.itinerary_approved else 'discussion_waived',
        'user_statement': user_statement,
        'recorded_at': now(),
    }
    (root / 'itinerary-approval.json').write_text(json.dumps(approval_record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    state = {'schema_version': 2, 'destination': args.destination.strip(), 'country': args.country.strip(), 'start_date': args.start_date, 'days': args.days, 'quality_mode': 'standard', 'status': 'in_progress', 'flight_decision': 'pending', 'stay_decision': 'pending', 'itinerary_gate': approval_record, 'stage': 'research_required', 'next_required_action': f"Run init_research_workspace.py {root} --destination {args.destination!r} --country {args.country or '<country>'} --start-date {args.start_date} --days {args.days}, then follow research_status.py in bounded batches.", 'handoff_allowed': False, 'final_response_allowed': False, 'continuation_required': True, 'user_input_required': False, 'active_workbench': str(root), 'skill_root': str(skill_root), 'checks': {}, 'evidence': {}, 'created_at': now(), 'updated_at': now()}
    save(root, state)
    if args.cold_start:
        (root/'cold-start.json').write_text(json.dumps({'requested':True,'user_statement':user_statement,'created_at':now(),'policy':'Fresh research, media, maps and QA; reusable Skill code/template only.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print_state(state)
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
