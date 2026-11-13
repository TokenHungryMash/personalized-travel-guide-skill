"""Render shared preparation and language content; travel tools reuse these nodes."""
from html import escape as E


def source_links(ids, sources):
    if not ids:
        return ''
    return '<p class="editorial-source-links">' + ''.join(
        '<a href="' + E(sources[key]['url'], quote=True) + '" target="_blank" rel="noopener">'
        + E(sources[key]['title']) + ' ↗</a>' for key in ids) + '</p>'


def preparation_html(editorial):
    groups = editorial.get('preparation')
    if groups is None:
        groups, counter = [], 0
        for title, texts in editorial['checklist'].items():
            items = []
            for text in texts:
                items.append(dict(id=f'c{counter}', title=text, detail='', priority=''))
                counter += 1
            groups.append(dict(title=title, items=items))
    html = '<div id="preparation-content"><div class="check-summary"><p id="check-count" data-check-count aria-live="polite"></p><button id="checks-clear" data-clear-checks>清空勾选</button></div><div class="preparation-stages">'
    for index, group in enumerate(groups):
        html += '<section class="preparation-stage"><header><span>' + str(index + 1).zfill(2) + '</span><h3>' + E(group['title']) + '</h3></header>'
        for task in group['items']:
            html += '<article class="preparation-task"><label class="check-row"><input type="checkbox" data-check="' + E(task['id']) + '"><span>' + E(task['title']) + '</span>' + ('<small>' + E(task['priority']) + '</small>' if task.get('priority') else '') + '</label>'
            if task.get('detail'):
                html += '<div class="preparation-detail"><p>' + E(task['detail']) + '</p>' + source_links(task.get('sources', []), editorial.get('editorial_sources', {})) + '</div>'
            html += '</article>'
        html += '</section>'
    return html + '</div></div>'


def language_scenes(editorial):
    """Explicit scene relations for new editions; keep all older groups reachable."""
    if editorial.get('languageScenes'):
        return editorial['languageScenes']
    scenes = []
    used = set()
    for index, title in enumerate(editorial.get('phrases', {})):
        glossary = '常备 · ' + title
        scenes.append(dict(id=f'scene-{index}', label=title, phrases=title,
                           replies=title if title in editorial.get('words', {}) else '',
                           glossary=glossary if glossary in editorial.get('words', {}) else ''))
        used.update([title, glossary])
    for title in editorial.get('words', {}):
        if title not in used:
            scenes.append(dict(id=f'scene-{len(scenes)}', label=title.removeprefix('常备 · '),
                               **{'glossary' if title.startswith('常备 · ') else 'replies': title}))
    return scenes


def language_row(item, fallback=''):
    return item if isinstance(item, dict) else dict(local=item[0], zh=item[1], roman='', id=fallback)


def language_text(row, language, tag='span'):
    local = '<' + tag + ' data-language-text="local" lang="' + E(language) + '">' + E(row['local']) + '</' + tag + '>'
    if language.lower().split('-')[0] == 'en':
        return local
    return local + '<' + tag + ' data-language-text="english" lang="en" hidden>' + E(row.get('english', '')) + '</' + tag + '>'


def phrase_field(owner, row, language):
    field = owner['input']
    key = 'phrase:' + owner['id'] + ':' + field['key']
    subject = field['label'].split('（')[0]
    html = '<details class="phrase-fields"><summary>填写' + E(subject) + '</summary><div class="phrase-input">'
    html += '<label>选择' + E(subject) + '<select data-phrase-choice><option value="">选择常用项，或在下方填写</option>'
    for option in field.get('options', []):
        html += '<option value="' + E(option['value'], quote=True) + '" data-english="' + E(option.get('english', ''), quote=True) + '">' + E(option['label']) + '</option>'
    html += '</select></label>'
    for mode, label, placeholder, note in [('local', field['label'], field.get('placeholder', ''), key),
                                         ('english', field.get('englishLabel', '具体内容（英语）'), field.get('englishPlaceholder', ''), key + ':english')]:
        if mode == 'english' and language.lower().split('-')[0] == 'en':
            continue
        html += '<label data-language-text="' + mode + '"' + (' hidden' if mode == 'english' else '') + '>' + E(label) + '<input data-phrase-input="' + mode + '" data-note="' + E(note, quote=True) + '" maxlength="80" placeholder="' + E(placeholder, quote=True) + '"' + (' required' if field.get('required') else '') + '></label>'
    if row.get('roman'):
        html += '<p class="phrase-field-note" data-language-text="local" lang="en">' + E(row['roman']) + '</p>'
    if row.get('note'):
        html += '<p class="phrase-field-note">' + E(row['note']) + '</p>'
    return html + '</div></details>'


def phrase_card(row, language, owners):
    html = '<article class="phrase-card" data-phrase-card="' + E(row['id']) + '">'
    html += '<button class="phrase" data-jp="' + E(row['local'], quote=True) + '" data-en="' + E(row.get('english', row['local'] if language.lower().split('-')[0] == 'en' else ''), quote=True) + '" data-rom="' + E(row.get('roman', ''), quote=True) + '" data-zh="' + E(row['zh'], quote=True) + '"><span class="phrase-intent">' + E(row['zh']) + '</span><small class="phrase-action">出示 ↗</small><span class="phrase-target">' + language_text(row, language) + '</span></button>'
    owner = row if row.get('input') else owners.get(row.get('subjectFrom'))
    if owner:
        html += phrase_field(owner, row, language)
    elif row.get('roman') or row.get('note'):
        html += '<details class="phrase-help"><summary>读音与用法</summary>'
        if row.get('roman'):
            html += '<p data-language-text="local" lang="en">' + E(row['roman']) + '</p>'
        if row.get('note'):
            html += '<p>' + E(row['note']) + '</p>'
        html += '</details>'
    return html + '</article>'


def language_html(editorial, language, language_name=None):
    scenes = language_scenes(editorial)
    owners = {row['id']: row for rows in editorial['phrases'].values() for row in rows if isinstance(row, dict)}
    all_rows = [language_row(row) for groups in (editorial['phrases'], editorial.get('words', {})) for rows in groups.values() for row in rows]
    has_english = language.lower().split('-')[0] != 'en' and all_rows and all(row.get('english') for row in all_rows)
    language_name = language_name or {'ja': '日语', 'en': '英语', 'id': '印尼语', 'th': '泰语', 'ko': '韩语'}.get(language, '当地语言')
    html = '<section id="language-content" class="language-workbench" data-language-workbench data-language="local"><header id="reader-language" class="lwb-head"><div><h3>随身语言锦囊</h3><p>认菜单、问路，或把句子放大给对方看。</p></div>'
    if has_english:
        html += '<div class="lwb-languages" role="group" aria-label="沟通语言"><button data-language-mode="local" aria-pressed="true">' + E(language_name) + '</button><button data-language-mode="english" aria-pressed="false">备用英语</button></div>'
    html += '</header><div class="lwb-layout"><nav class="lwb-scenes" aria-label="语言场景">'
    for index, scene in enumerate(scenes):
        html += '<button data-language-scene="' + E(scene['id']) + '" aria-pressed="' + str(index == 0).lower() + '">' + E(scene['label']) + '<span aria-hidden="true">↗</span></button>'
    html += '</nav><div class="lwb-content">'
    labels = {'phrases': '现场会话', 'glossary': '词语速查', 'replies': '常见回答'}
    for index, scene in enumerate(scenes):
        groups = {kind: (editorial['phrases'] if kind == 'phrases' else editorial.get('words', {})).get(scene.get(kind), []) for kind in labels}
        groups = {kind: rows for kind, rows in groups.items() if rows}
        first = next(iter(groups), '')
        html += '<section data-language-panel="' + E(scene['id']) + '" aria-label="' + E(scene['label']) + '"' + (' hidden' if index else '') + '><div class="lwb-views" role="group" aria-label="查询内容">'
        for kind, rows in groups.items():
            html += '<button data-language-view="' + kind + '" aria-pressed="' + str(kind == first).lower() + '">' + labels[kind] + '<small>' + str(len(rows)) + '</small></button>'
        html += '</div>'
        for kind, rows in groups.items():
            html += '<div data-language-pane="' + kind + '"' + (' hidden' if kind != first else '') + '>'
            if kind == 'phrases':
                html += '<div class="lwb-phrases">' + ''.join(phrase_card(language_row(item, f'phrase-{index}-{i}'), language, owners) for i, item in enumerate(rows)) + '</div>'
            else:
                html += '<dl class="lwb-terms ' + ('lwb-replies' if kind == 'replies' else 'lwb-glossary') + '">'
                for item in rows:
                    row = language_row(item)
                    html += '<div class="lwb-term"><dt>' + language_text(row, language) + '</dt><dd>' + E(row['zh']) + '</dd></div>'
                html += '</dl>'
            html += '</div>'
        html += '</section>'
    return html + '</div></div></section>'
