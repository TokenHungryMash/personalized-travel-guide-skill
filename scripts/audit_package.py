"""Read-only checks of portable template assets and skill-local references."""
from pathlib import Path
import hashlib,json,re,importlib.util,sys

def main():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'assets/reference-manifest.json').read_text(encoding='utf-8'))
    assert manifest['version']=='4.0.0' and manifest['cover']=='static-photo'
    for name,digest in manifest['files'].items():
        p=(root/name).resolve()
        assert p.is_relative_to(root),name
        assert p.is_file(),name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,'Asset changed: '+name
    for md in [root/'SKILL.md',*sorted((root/'references').glob('*.md'))]:
        text=md.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in link or link.startswith('#'):continue
            p=(md.parent/link.split('#')[0]).resolve()
            assert p.is_relative_to(root) and p.exists(),f'{md.name}: {link}'
    template=root/'assets/fukuoka-reference'
    build=(template/'build.py').read_text(encoding='utf-8')
    assert '<video' not in build and 'film-toggle' not in build and 'src="film.js"' not in build
    assert not any(p.suffix.lower() in {'.mp4','.webm','.ogv','.mov'} for p in (root/'assets').rglob('*'))
    for file in ['check-editorial.cjs','check-cascade.cjs']:
        assert 'C:/Users/' not in (template/file).read_text(encoding='utf-8')
    data=json.loads((template/'content.json').read_text(encoding='utf-8'))
    ids={p['id'] for p in data['places']}
    for day in data['days']:
        assert all(stop[1] in ids for stop in day['stops'])
        assert all(stop[1] in day['schedules']['standard'] for stop in day['stops'])
    current=root/'assets/destination-reference'
    sys.path.insert(0, str(current))
    renderer=(current/'edition-renderer.py').read_text(encoding='utf8')
    for name in ['directory.css','ledger.css','travel-readability.css','ledger-ui.js','ledger-demo.js','travel-interior.css','map-layout.js','map-polish.css','magazine-polish.css','editorial-premium.css','photo-overprint.css','reader-density.css','mobile-travel.css','reader-context.js','member-avatars.js','travel-alternatives.js','travel-alternatives.css']:
        assert (current/name).is_file() and name in renderer, 'Unwired current engine asset: '+name
    app=(current/'app.js').read_text(encoding='utf8')
    assert 'MagazineLedger.submit' in app and 'photoPlanMarkup' in app
    for name in ('travel-reference.js', 'travel-reference.css'):
        assert (current/name).is_file() and name in renderer, 'Unwired shared reference module: '+name
    assert (current/'reader_reference.py').is_file() and 'from reader_reference import' in renderer
    assert 'TravelReference.dining' in app and 'TravelReference.showPhrase' in app
    assert 'budget:G.edition.budget' in app
    assert 'TravelAlternatives.render' in app and 'MemberAvatars.valid' in app and 'dayContinuation()' in app
    assert 'MagazineReader?.update' in (current/'motion.js').read_text(encoding='utf8')
    assert '--dock-days' in (current/'mobile-travel.css').read_text(encoding='utf8')
    assert 'G.days.length>7' in (current/'reader-context.js').read_text(encoding='utf8')
    spec=importlib.util.spec_from_file_location('validate_current',current/'validate_edition.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    load=lambda name:json.loads((current/name).read_text(encoding='utf8'))
    module.validate(load('content.json'),load('edition.json'),load('editorial-content.json'),load('edition-photos.json')|load('place-photos.json'))
    from audit_maps import audit as audit_maps
    map_report = audit_maps(current)
    assert not map_report['errors'], '\n'.join(map_report['errors'])
    assert (root/'scripts/browser_runtime.cjs').is_file()
    assert (root/'scripts/audit_destination.py').is_file()
    assert (root/'scripts/check_current_engine.cjs').is_file()
    for name in ('fetch_photos.py', 'download_photos.py', 'package_skill.py', 'portable_files.py', 'workbench_input.py', 'check_directory_pagination.cjs', 'test_node_diagnostics.cjs'):
        assert (root/'scripts'/name).is_file(), 'Missing portable helper: '+name
    for name in ('schema_check.py', 'content.schema.json', 'editorial-content.schema.json', 'place-photos.schema.json', 'directory-plan.schema.json', 'offline_images.py', 'offline-image-pool.js', 'preflight.py', 'language_fields.py', 'font_audit.py'):
        assert (current/name).is_file(), 'Missing authoring/build dependency: '+name
    assert (root/'assets/authoring-examples.jsonc').is_file()
    assert '给第 ${state.day+1} 天存几张' not in app
    intake=(root/'assets/intake-questionnaire/index.html').read_text(encoding='utf8')
    assert 'build-personalized-travel-guide-open-source' in intake and 'routeApproved=false' in intake
    assert 'validDates' in intake and 'downloadBrief' in intake and 'photoStyle' not in intake
    assert 'journal-masthead' in intake and 'brief-sidebar' in intake and 'data:font/woff2;base64,' in intake
    assert 'travel-build-id' in renderer and 'build-manifest.json' in renderer
    assert (root/'scripts/audit_browser.cjs').is_file()
    print(f'PASS: {len(manifest["files"])} asset hashes, local links, static cover, portable checks and schedule/place references')

if __name__=='__main__':main()
