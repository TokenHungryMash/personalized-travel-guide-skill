"""Minimum authored content shared by the builder and standalone audit."""
import re


def chinese_length(value):
    return len(re.findall(r"[\u3400-\u9fff]", value)) if isinstance(value, str) else 0


def prose_report(item, keys):
    counts = {key: chinese_length(item.get(key, '')) for key in keys}
    missing = [key for key in keys if not isinstance(item.get(key), str) or not item[key].strip()]
    return sum(counts.values()), ', '.join(f'{key}={count}' for key, count in counts.items()), missing


def audit_content(guide):
    places = {place['id']: place for place in guide['places']}
    errors = []
    for index, day in enumerate(guide['days']):
        route = {stop[1] for stop in day['stops']}
        for value in day.get('shopping', []):
            if value in places:
                errors.append(f"{day['id']}: shopping 要写购买判断，不是地点 ID: {value}")
        if day.get('periods') == [day.get('lead'), day.get('move'), day.get('guard')]:
            errors.append(f"{day['id']}: periods 不能用全天 lead/move/guard 冒充早中晚安排")
        for place_id in route:
            place = places.get(place_id, {})
            count, detail, missing = prose_report(place, ('desc', 'walk', 'tip'))
            if missing:
                errors.append(f"{day['id']} / {place_id}: 地点正文缺少字段={missing}")
            fields=[place.get(k,'').strip() for k in ('desc','walk','tip')]
            if not missing and len(set(fields))<3:
                errors.append(f"{day['id']} / {place_id}: 介绍、走法、条件不可重复同一段正文")
        # Exceptions must preserve the user's actual instruction for editorial review.
        exempt = bool(day.get('photoExceptionReason', '').strip())
        shots = day.get('photoPlan', [])
        sightseeing = any(places.get(pid, {}).get('kind') != '交通' for pid in route)
        edge_day = index in (0, len(guide['days']) - 1)
        minimum = 0 if exempt or not sightseeing else 1
        if len(shots) < minimum:
            errors.append(f"{day['id']}: 至少需要 {minimum} 条摄影方案")
        seen = set()
        fingerprints = set()
        for shot_index, shot in enumerate(shots):
            required = ('time', 'placeId', 'title', 'light', 'composition', 'portrait', 'settings')
            label = f"{day['id']}.photoPlan[{shot_index}] ({shot.get('placeId', '?')} / {shot.get('title', '?')})"
            missing = [key for key in required if not isinstance(shot.get(key), str) or not shot[key].strip()]
            if missing:
                errors.append(f"{label}: 缺少字段={missing}")
            if shot.get('placeId') not in route:
                errors.append(f"{label}: 摄影地点不在当天路线")
            seen.add(shot.get('placeId'))
            fingerprint = tuple(shot.get(k, '').strip() for k in ('light', 'composition', 'portrait', 'settings'))
            if fingerprint in fingerprints:
                errors.append(f"{label}: 重复摄影正文，换标题或地点不算新方案")
            fingerprints.add(fingerprint)
    return errors
