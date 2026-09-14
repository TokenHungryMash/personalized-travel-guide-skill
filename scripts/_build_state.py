"""Shared build-state and release-gate helpers for travel handbooks."""
from __future__ import annotations
import json
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
STATE_NAME = '.travel-build-state.json'
DECISIONS_NAME = 'trip-decisions.json'
QA_NAME = 'browser-qa.json'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
STAGES = ('research_required', 'research_in_progress', 'profile_required', 'profile_invalid', 'workbench_required', 'render_required', 'assets_required', 'assets_invalid', 'maps_required', 'visual_review_required', 'automated_gates_required', 'browser_qa_required', 'offline_export_required', 'offline_qa_required', 'complete')
DECISION_STATUSES = {'booked', 'selected', 'skipped', 'pending'}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def run(script: Path, *args: str) -> tuple[bool, str]:
    result = subprocess.run([sys.executable, str(script), *args], text=True, encoding='utf-8', errors='replace', capture_output=True)
    output = '\n'.join((part.strip() for part in (result.stdout, result.stderr) if part.strip()))
    return (result.returncode == 0, output)

def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ''

def evaluation_fingerprint(root: Path) -> str:
    """Bind cached status to actual inputs, including media and validator code."""
    excluded = {STATE_NAME, '.validation-cache.json', 'build-command-timings.jsonl'}
    ignored_dirs = {'__pycache__', '.git'}
    skill = Path(__file__).resolve().parent.parent
    result = hashlib.sha256()
    profile = load_json(root / 'destination-profile.json')
    system = profile.get('ui_system', 'current-system')
    if system not in {'current-system', 'canonical'}:
        system = 'current-system'
    product = skill / 'assets' / system / 'product'
    for base in (root, skill / 'scripts', product, skill / 'references'):
        result.update(str(base.resolve()).encode('utf-8'))
        for path in sorted(base.rglob('*')):
            relative = path.relative_to(base)
            if not path.is_file() or path.name in excluded or ignored_dirs.intersection(relative.parts):
                continue
            if base == product and (relative.parts[0] in {'media', 'audit-routes'} or path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}):
                continue
            if path.suffix in {'.pyc', '.jsonl'}:
                continue
            result.update(str(relative).encode('utf-8'))
            result.update(digest(path).encode('ascii'))
    for path in [skill / 'SKILL.md', *sorted((skill / 'assets').glob('*.json'))]:
        result.update(str(path).encode('utf-8'))
        result.update(digest(path).encode('ascii'))
    receipt = load_json(root / 'offline-export.json')
    if isinstance(receipt.get('file'), str):
        artifact = Path(receipt['file'])
        result.update(str(artifact).encode('utf-8'))
        result.update(digest(artifact).encode('ascii'))
    return result.hexdigest()

def qa_is_complete(root: Path) -> tuple[bool, list[str]]:
    qa = load_json(root / QA_NAME)
    failures: list[str] = []
    profile = load_json(root / 'destination-profile.json')
    representative_qa = True
    has_gallery = any((len(p.get('images', [])) > 1 for p in profile.get('places', []) if isinstance(p, dict)))
    validation_mode = qa.get('validation_mode')
    if validation_mode == 'manual_representative':
        from _manual_qa import validate_manual_qa
        return validate_manual_qa(root, qa, representative_qa)
    representative_qa = representative_qa and validation_mode != 'publication_depth'
    if validation_mode not in {'representative', 'publication_depth'}:
        failures.append('browser QA needs validation_mode representative or publication_depth')
    if validation_mode in {'representative', 'publication_depth'}:
        from _manual_qa import build_fingerprint
        if qa.get('build_fingerprint') != build_fingerprint(root):
            failures.append('browser QA build changed or fingerprint missing; verify the current build')
    if validation_mode == 'representative' and (not representative_qa):
        samples = qa.get('samples', {})
        for key in (('sight_gallery',) if has_gallery else ()) + ('disclosure', 'mini_route', 'trip_mode_day', 'adjust_itinerary', 'theme'):
            if not isinstance(samples, dict) or not str(samples.get(key, '')).strip():
                failures.append(f'representative browser QA needs sampled ID/state: {key}')
    for viewport in ('desktop', 'mobile'):
        record = qa.get(viewport, {})
        if not isinstance(record, dict) or record.get('passed') is not True:
            failures.append(f'{viewport} QA not passed')
            continue
        width = record.get('inner_width')
        height = record.get('inner_height')
        if not isinstance(width, (int, float)) or not isinstance(height, (int, float)) or width <= 0 or (height <= 0):
            failures.append(f'{viewport} QA needs measured inner_width and inner_height')
        elif viewport == 'desktop' and width < 1180:
            failures.append('desktop QA viewport is narrower than 1180px')
        elif viewport == 'mobile' and width > 480:
            failures.append('mobile QA viewport is wider than 480px')
        if record.get('horizontal_overflow') is not False:
            failures.append(f'{viewport} QA must explicitly report horizontal_overflow false')
        if viewport == 'mobile' and record.get('match_media_mobile') is not True:
            failures.append('mobile QA did not activate the mobile media query')
    interactions = qa.get('interactions', {})
    required = ('disclosures', 'galleries', 'mini_routes', 'trip_mode', 'adjust_itinerary', 'checklist_memory', 'theme_picker')
    if representative_qa:
        required = ('disclosures', 'trip_mode')
    for key in required:
        if key == 'galleries' and (not has_gallery) and (interactions.get(key) == 'not_applicable'):
            continue
        if not isinstance(interactions, dict) or interactions.get(key) is not True:
            failures.append(f'interaction not verified: {key}')
    screenshots = qa.get('screenshots', [])
    evidence = qa.get('visual_observations', [])
    expected = {'desktop_cover', 'mobile_sight'} if representative_qa else {'desktop_cover', 'desktop_contents', 'mobile_cover', 'mobile_gallery' if has_gallery else 'mobile_sight'}
    observed = {r.get('state') for r in evidence if isinstance(r, dict) and r.get('observed') is True and str(r.get('tool_reference', '')).strip() and str(r.get('note', '')).strip()}
    evidence_fallback = validation_mode == 'representative' and bool(qa.get('screenshot_save_limitation')) and (expected <= observed)
    if not evidence_fallback:
        minimum_screenshots = 2 if representative_qa else 4
        if not isinstance(screenshots, list) or len(screenshots) < minimum_screenshots:
            failures.append(f'{minimum_screenshots} saved QA screenshots or documented representative visual observations required')
        else:
            for raw in screenshots:
                candidate = Path(str(raw))
                if not candidate.is_absolute():
                    candidate = root / candidate
                if not candidate.is_file():
                    failures.append(f'missing QA screenshot: {raw}')
    return (not failures, failures)

def next_instruction(root: Path, stage: str) -> str:
    scripts = Path(__file__).resolve().parent
    profile = root / 'destination-profile.json'
    mapping = {'research_required': f'Run init_research_workspace.py for {root}, then process only the bounded batch printed by research_status.py. If an unsigned legacy destination-profile.json is present, treat it as read-only clues: do not validate, render or promote it; the official compiler will replace it after the new packs are complete.', 'research_in_progress': f'Run research_status.py {root}, complete its next bounded batch, and repeat until compile_destination_profile.py can run.', 'profile_required': f'Compile the completed research packs into {profile} with compile_destination_profile.py.', 'profile_invalid': f"Read the failing field IDs, fix their owning files under {root / 'research'}, rerun compile_destination_profile.py, then validate the regenerated {profile}. Never patch the compiled profile or old export directly.", 'workbench_required': f"Run: {sys.executable} {scripts / 'install_ui_system.py'} {root}", 'render_required': 'Build render bindings, render all destination records using the already verified final assets, and remove ADAPTATION_REQUIRED.json only after the renderer has completed every record family.', 'assets_required': 'Fetch final declared images concurrently and create asset-manifest.json. Run machine preflight and inspect the batch contact sheet; open ambiguous assets individually and preserve genuine source observations.', 'assets_invalid': 'Replace or repair failed image records and rerun verify_assets.py; one bad source is not a blocker.', 'visual_review_required': 'Open the batch contact sheet, inspect all cards once, then open only flagged/unclear images at full size. Save evidence and update the manifest; if no visual surface works, keep PREVIEW READY and report the host limitation without claiming final handoff.', 'automated_gates_required': 'Fix strict audit/forward-test failures and rerun advance_build.py; do not hand off yet.', 'browser_qa_required': f'Perform desktop/mobile interaction QA and save evidence as {root / QA_NAME}, then run check_handoff.py.', 'complete': 'All release gates pass. A final handoff is allowed.'}
    mapping.update({'offline_export_required': 'Run check_handoff.py to export the current build before final QA.', 'offline_qa_required': 'Open the exported HTML, test chapter navigation, disclosures, Trip Mode, day switching and map viewer; write offline-qa.json bound to offline-export.json sha256, then run check_handoff.py.'})
    mapping['maps_required'] = 'Follow references/screenshot-map-workflow.md: prepare one overview per day, capture with the authorized browser, inspect the real images and import. Then recompile changed itinerary packs and resume advance_build.py. Reuse valid captures and existing coordinates; do not render or repeat destination research while maps are incomplete.'
    return mapping[stage]

def next_command(root: Path, stage: str) -> str:
    """Return the narrow deterministic command that should be run next."""
    scripts = Path(__file__).resolve().parent
    commands = {'research_required': f'''"{sys.executable}" "{scripts / 'advance_build.py'}" "{root}" --run''', 'research_in_progress': f'''"{sys.executable}" "{scripts / 'research_status.py'}" "{root}"''', 'profile_required': f'''"{sys.executable}" "{scripts / 'advance_build.py'}" "{root}" --run''', 'workbench_required': f'''"{sys.executable}" "{scripts / 'advance_build.py'}" "{root}" --run''', 'render_required': f'''"{sys.executable}" "{scripts / 'advance_build.py'}" "{root}" --run''', 'assets_required': f'''"{sys.executable}" "{scripts / 'advance_build.py'}" "{root}" --run''', 'browser_qa_required': f'''"{sys.executable}" "{scripts / 'check_handoff.py'}" "{root}"''', 'complete': ''}
    if stage in {'offline_export_required', 'offline_qa_required'}:
        return '"{}" "{}" "{}"'.format(sys.executable, scripts / 'check_handoff.py', root)
    return commands.get(stage, '')

def next_action_kind(stage: str) -> str:
    if stage == 'complete':
        return 'handoff'
    if stage in {'research_required', 'profile_required', 'workbench_required', 'render_required', 'assets_required'}:
        return 'deterministic_command'
    if stage == 'browser_qa_required':
        return 'browser_qa'
    return 'bounded_agent_work'

def evaluate(root: Path, *, run_gates: bool) -> dict:
    root = root.resolve()
    scripts = Path(__file__).resolve().parent
    profile = root / 'destination-profile.json'
    manifest = root / 'asset-manifest.json'
    index = root / 'index.html'
    marker = root / 'ADAPTATION_REQUIRED.json'
    render_report = load_json(root / 'RENDER_REPORT.json')
    state = load_json(root / STATE_NAME)
    original_skill_root = str(state.get('skill_root', '')).strip()
    if original_skill_root and Path(original_skill_root).resolve() != scripts.parent:
        raise SystemExit('SKILL ROOT CONFLICT: resume this workbench with scripts from '
                         + original_skill_root + '; do not mix installed and supplied versions.')
    if not run_gates and state.get('evaluation_fingerprint') == evaluation_fingerprint(root):
        return state
    decisions = load_json(root / DECISIONS_NAME)
    flight_status = str(decisions.get('flight', {}).get('status', 'pending')) if isinstance(decisions.get('flight'), dict) else 'pending'
    stay_status = str(decisions.get('stay', {}).get('status', 'pending')) if isinstance(decisions.get('stay'), dict) else 'pending'
    invalid_decisions = [status for status in (flight_status, stay_status) if status not in DECISION_STATUSES]
    incomplete_selected = [family for family in ('flight', 'stay') if isinstance(decisions.get(family), dict) and decisions[family].get('status') == 'selected' and (not isinstance(decisions[family].get('selected_record'), dict))]
    checks: dict[str, object] = {'index_exists': index.is_file(), 'profile_exists': profile.is_file(), 'manifest_exists': manifest.is_file(), 'adaptation_marker_absent': not marker.exists(), 'trip_decisions_recorded': (root / DECISIONS_NAME).is_file() and (not invalid_decisions), 'official_render_report': bool(render_report), 'canonical_template_hash_verified': render_report.get('canonical_template_hash_verified') is True, 'custom_page_builder_detected': render_report.get('custom_page_builder_detected') is not False}
    evidence: dict[str, str] = {}
    if invalid_decisions or incomplete_selected:
        evidence['trip_decisions'] = f'invalid imported record ignored; flight={flight_status}; stay={stay_status}'
        flight_status = 'pending' if flight_status not in DECISION_STATUSES or 'flight' in incomplete_selected else flight_status
        stay_status = 'pending' if stay_status not in DECISION_STATUSES or 'stay' in incomplete_selected else stay_status
    plan = root / 'research-plan.json'
    provenance = root / 'RESEARCH_PROVENANCE.json'
    if not plan.is_file():
        stage = 'research_required'
        if profile.is_file():
            checks['legacy_unsigned_profile_ignored'] = True
            evidence['legacy_migration'] = 'Unsigned legacy destination-profile.json ignored; rebuild current research packs and let compile_destination_profile.py replace it.'
    elif not profile.is_file() or not provenance.is_file():
        research_status_ok, evidence['research_status'] = run(scripts / 'research_status.py', str(root))
        stage = 'profile_required' if research_status_ok else 'research_in_progress'
        if profile.is_file() and (not provenance.is_file()):
            checks['legacy_unsigned_profile_ignored'] = True
            evidence['legacy_migration'] = 'Existing profile has no current RESEARCH_PROVENANCE.json and is excluded from production validation.'
    else:
        research_ok, evidence['research_provenance'] = run(scripts / 'verify_research_provenance.py', str(root))
        checks['research_pass'] = research_ok
        profile_ok, evidence['profile_preflight'] = run(scripts / 'validate_destination_data.py', str(profile))
        checks['profile_preflight_pass'] = profile_ok
        if not research_ok and any((marker in evidence.get('research_provenance', '') for marker in ('research plan changed after compilation', 'research pack changed after compilation'))):
            stage = 'profile_required'
            evidence['automatic_recompile'] = 'Research sources changed after compilation; regenerate the signed profile before continuing.'
        elif not research_ok:
            stage = 'profile_invalid'
        elif not profile_ok:
            stage = 'profile_invalid'
        elif not manifest.is_file():
            stage = 'assets_required'
        else:
            assets_ok, evidence['asset_preflight'] = run(scripts / 'verify_assets.py', str(profile), str(manifest), str(root), '--machine-only', '--write')
            checks['asset_machine_preflight'] = assets_ok
            from _route_screenshots import verify_captures
            map_failures = verify_captures(root, load_json(profile)) if assets_ok else []
            if assets_ok:
                checks['maps_verified'] = not map_failures
                if map_failures:
                    evidence['route_maps'] = '\n'.join(map_failures)
            if not assets_ok:
                stage = 'assets_invalid'
            elif map_failures:
                stage = 'maps_required'
            elif not index.is_file() and not (root / '.index.template.html').is_file():
                stage = 'workbench_required'
            elif marker.exists() or render_report.get('profile_sha256') != digest(profile) or (not render_report.get('bindings_sha256')):
                if render_report and render_report.get('profile_sha256') != digest(profile):
                    evidence['stale_render'] = 'destination-profile.json changed after the last official render'
                stage = 'render_required'
            else:
                visual_ok, evidence['asset_verification'] = run(scripts / 'verify_assets.py', str(profile), str(manifest), str(root))
                checks['assets_verified'] = visual_ok
                checks['media_pass'] = visual_ok
                audit_args = (str(root), '--strict', '--standard-fast')
                audit_ok, evidence['strict_audit'] = run(scripts / 'audit_product.py', *audit_args) if visual_ok else (False, 'strict audit waits for visual review')
                forward_ok, evidence['forward_test'] = run(scripts / 'quick_forward_test.py', str(root))
                checks['strict_audit_pass'] = audit_ok
                checks['forward_test_pass'] = forward_ok
                checks['structure_pass'] = audit_ok and forward_ok
                if not visual_ok:
                    stage = 'visual_review_required'
                elif not (audit_ok and forward_ok):
                    stage = 'automated_gates_required'
                else:
                    qa_ok, qa_failures = qa_is_complete(root)
                    checks['browser_qa_pass'] = qa_ok
                    evidence['interaction_qa_method'] = load_json(root / QA_NAME).get('validation_mode', 'pending')
                    if qa_failures:
                        evidence['browser_qa'] = '\n'.join(qa_failures)
                    stage = 'browser_qa_required'
                    if qa_ok:
                        from _offline_qa import export_state
                        stage, evidence['offline_qa'], _ = export_state(root)
                        checks['offline_qa_pass'] = stage == 'complete'
    profile_data = load_json(profile) if profile.is_file() and (root / 'RESEARCH_PROVENANCE.json').is_file() else {}
    trip_data = profile_data.get('trip', {}) if isinstance(profile_data.get('trip'), dict) else {}
    if profile_data:
        state.update({'destination': profile_data.get('destination') or state.get('destination', ''), 'country': profile_data.get('country') or state.get('country', ''), 'start_date': trip_data.get('start_date') or state.get('start_date', 'pending'), 'end_date': trip_data.get('end_date') or state.get('end_date', 'pending'), 'days': trip_data.get('days') or state.get('days'), 'flight_decision': flight_status, 'stay_decision': stay_status})
    else:
        state.update({'flight_decision': flight_status, 'stay_decision': stay_status})
    state.update({'schema_version': 2, 'status': 'complete' if stage == 'complete' else 'in_progress', 'stage': stage, 'next_required_action': next_instruction(root, stage), 'handoff_allowed': stage == 'complete', 'preview_ready': bool(index.is_file() and checks.get('profile_preflight_pass') and checks.get('asset_machine_preflight')), 'final_response_allowed': stage == 'complete', 'continuation_required': stage != 'complete', 'final_response_guard': 'allowed' if stage == 'complete' else 'forbidden_until_handoff_or_real_user_blocker', 'recoverable_failure_policy': 'inspect_context_retry_smallest_step_revalidate_then_continue', 'user_input_required': False, 'active_workbench': str(root), 'next_action_kind': next_action_kind(stage), 'next_command': next_command(root, stage), 'audit_dimensions': {'structure': bool(checks.get('structure_pass')), 'research': bool(checks.get('research_pass')), 'media': bool(checks.get('media_pass'))}, 'checks': checks, 'evidence': evidence, 'render_method': render_report.get('render_method', 'missing'), 'updated_at': now()})
    state['review_ready'] = stage in {'browser_qa_required', 'complete'}
    state['response_state'] = 'complete' if stage == 'complete' else 'in_progress'
    if stage == 'browser_qa_required':
        from _manual_qa import build_fingerprint
        qa = load_json(root / QA_NAME)
        current_evidence = qa.get('build_fingerprint') == build_fingerprint(root)
        manual_wait = qa.get('validation_mode') == 'manual_representative' and qa.get('user_authorized') is True and (qa.get('status') == 'pending')
        limitation = qa.get('host_limitation', {})
        unavailable = qa.get('validation_mode') == 'unavailable' and qa.get('status') == 'pending' and isinstance(limitation, dict) and all((isinstance(limitation.get(key), str) and limitation[key].strip() for key in ('reason', 'tool_reference', 'checked_at')))
        if current_evidence and (manual_wait or unavailable):
            state.update({'response_state': 'waiting_for_review', 'final_response_allowed': True, 'final_response_guard': 'preview_response_only_qa_pending', 'user_input_required': True, 'continuation_required': False, 'next_action_kind': 'human_qa' if manual_wait else 'user_preview', 'next_command': '', 'next_required_action': 'Automatic gates passed. Await actual user QA results; consent is not a pass.' if manual_wait else 'Automatic gates passed. Show the current page for user review; browser QA remains pending.'})
    if stage == 'offline_qa_required':
        from _offline_qa import export_state
        _, _, unavailable = export_state(root)
        if unavailable:
            state.update({'response_state':'waiting_for_review','final_response_allowed':True,'final_response_guard':'preview_response_only_export_qa_pending','continuation_required':False,'user_input_required':True,'next_action_kind':'user_preview','next_command':'','next_required_action':'Show the exported artifact and disclose the recorded host limitation. Full handoff remains pending; do not bypass an explicit denial.'})
    state['evaluation_fingerprint'] = evaluation_fingerprint(root)
    return state

def save(root: Path, state: dict) -> Path:
    path = root.resolve() / STATE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path

def print_state(state: dict) -> None:
    print(json.dumps(state, ensure_ascii=False, indent=2))
    if state.get('preview_ready') and (not state.get('handoff_allowed')):
        print('PREVIEW_READY: true — content and local assets can be previewed; publication verification is still pending')
    if not state.get('handoff_allowed'):
        print(f"FINAL_RESPONSE_ALLOWED: {str(bool(state.get('final_response_allowed'))).lower()}")
        print(f"FINAL_RESPONSE_GUARD: {state.get('final_response_guard')}")
        print(f"USER_INPUT_REQUIRED: {str(bool(state.get('user_input_required'))).lower()}")
        print(f"CONTINUE_IN_SAME_WORKBENCH: {state.get('active_workbench', '')}")
        print(f"NEXT_ACTION_KIND: {state.get('next_action_kind', 'bounded_agent_work')}")
        if state.get('next_command'):
            print(f"NEXT_COMMAND: {state['next_command']}")
        print(f"CONTINUE: {state.get('next_required_action')}")
        if state.get('continuation_required'):
            print('RECOVERABLE_FAILURES: inspect the actual error, repair the smallest step, revalidate and continue')
            print('REQUIRED_BEHAVIOR: execute the next action in this workbench')
        else:
            print('REVIEW RESPONSE ALLOWED: provide the preview; full handoff remains pending')
