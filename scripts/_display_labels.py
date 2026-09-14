"""Destination-neutral display labels; keep research enums unchanged."""
def transport_label(value):
    labels = {'walk':'步行','walking':'步行','train':'轨道交通','metro':'地铁','subway':'地铁','bus':'公交','taxi':'出租车','car':'驾车','drive':'驾车','ferry':'渡轮','flight':'飞机','bike':'骑行','transit':'公共交通','public_transit':'公共交通'}
    text = str(value or '').strip()
    return labels.get(text.lower(), text)

def route_note(day):
    if day.get('route_note'):
        return str(day['route_note'])
    if any(s.get('distance_basis') == 'coordinate_straight_line' for s in day.get('stops', [])):
        return '距离为坐标间直线估算，不是实走距离；交通时间为含候车缓冲的计划值，实际以导航为准。'
    return ''
