#!/usr/bin/env python3
"""Generate canonical travel-handbook component fragments from a destination profile."""
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
from pathlib import Path


def e(value) -> str:
    if isinstance(value, (list, tuple)):
        return " · ".join(e(item) for item in value if item is not None and item != "")
    if isinstance(value, dict):
        raise ValueError("Display field must be text or a text list, not an object")
    return html.escape(str(value if value is not None else ""), quote=True)


def map_url(place: dict) -> str:
    return str(place.get("map_url") or ("https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(str(place.get("map_query", place.get("display_name", ""))))))


def image_files(place: dict) -> list[str]:
    result = []
    for image in place.get("images", []):
        if isinstance(image, dict) and image.get("file"):
            result.append(str(image["file"]))
        elif isinstance(image, str):
            result.append(image)
    return result


def source_link(place: dict) -> str:
    url = place.get("official_url") or place.get("source_url")
    label = "官网" if place.get("official_url") else "来源"
    return f'<a href="{e(url)}" target="_blank" rel="noreferrer">{label} ↗</a>'


def gallery(place: dict, label: str = "") -> str:
    files = image_files(place)
    figures = "".join(
        f'<figure><img src="{e(file)}" alt="{e(place.get("display_name"))} 参考图 {index}" loading="lazy">'
        + (f'<span>{e(label)}</span>' if index == 1 and label else "") + '</figure>'
        for index, file in enumerate(files, 1)
    )
    if len(files) < 2:
        return f'<div class="gallery-wrap is-static"><div class="photo-strip">{figures}</div></div>'
    controls = '<button class="gallery-arrow prev" aria-label="上一张">←</button><button class="gallery-arrow next" aria-label="下一张">→</button>'
    return f'<div class="gallery-wrap"><div class="photo-strip">{figures}</div>{controls}<div class="gallery-count">01 / {len(files):02d}</div></div>'


def place_index(profile: dict) -> dict[str, dict]:
    return {str(item["id"]): item for item in profile.get("places", []) if isinstance(item, dict) and item.get("id")}


def bind_schedule_labels(profile: dict, places: dict[str, dict]) -> None:
    scheduled: dict[str, int] = {}
    for day_number, day in enumerate(profile.get("itinerary", []), 1):
        for stop in day.get("stops", []):
            if isinstance(stop, dict) and stop.get("place_id"):
                scheduled[str(stop["place_id"])] = day_number
    for place_id, place in places.items():
        if place_id in scheduled:
            place["scheduled_label"] = f'第 {scheduled[place_id]} 天 · 已安排'
        elif not place.get("scheduled_label"):
            suggested_day = place.get("suggested_day")
            place["scheduled_label"] = f'备选 · 建议加入第 {suggested_day} 天' if suggested_day else '备选 · 按区域顺路加入'


def heading(number: str, eyebrow: str, title: str, summary: str = "") -> str:
    return f'<div class="section-heading"><span class="section-no">{e(number)}</span><div><p class="eyebrow">{e(eyebrow)}</p><h2>{e(title)}</h2>' + (f'<p>{e(summary)}</p>' if summary else '') + '</div></div>'


def contents(profile: dict) -> str:
    experience_groups = profile.get("module_groups", {}).get("experiences", [])
    experience_summary = "、".join(str(group.get("title", "")) for group in experience_groups[:2] if group.get("title")) or "当地值得体验的项目"
    entries = (
        ("01", "stay", "行程", "酒店、路线、时间与停留"),
        ("02", "sights", "景点指南", "已安排与可选"),
        ("03", "shops", "购物", "店铺、集市与伴手礼"),
        ("04", "move", "当地特色体验", experience_summary),
        ("05", "food", "餐饮指南", "当地小吃、专程餐厅与安心连锁"),
        ("06", "booking", "出发前准备", "预约、确认与行李清单"),
        ("07", "words", "语言随行锦囊", "高频词与现场表达"),
        ("08", "tips", "旅游贴士", "健康、安全与文化"),
    )
    links = "".join(
        f'<a href="#{anchor}"><span>{number}</span><b>{e(label)}</b><em>{e(summary)}</em></a>'
        for number, anchor, label, summary in entries
    )
    return (
        '<div class="shell"><div class="contents-head"><p class="eyebrow">CONTENTS · 随时跳转</p>'
        '<h2>从这里，翻到旅途的任意一页。</h2></div>'
        f'<div class="contents-grid">{links}</div></div>'
    )


def mobile_menu(profile: dict) -> str:
    entries = (
        ("01", "route", "行程"), ("02", "sights", "景点指南"),
        ("03", "shops", "购物"), ("04", "move", "当地特色<br>体验"),
        ("05", "food", "餐饮指南"), ("06", "booking", "出发前准备"),
        ("07", "words", "语言锦囊"), ("08", "tips", "旅游贴士"),
    )
    links = "".join(
        f'<a href="#{anchor}" tabindex="-1"><b>{number}</b><span>{label}</span><i>↗</i></a>'
        for number, anchor, label in entries
    )
    return (
        f'<header><small>{e(profile["display_name"])} · {e(profile.get("year", ""))}</small>'
        '<strong>想翻到哪一页？</strong><button type="button" aria-label="关闭目录">×</button></header>'
        f'<div class="mobile-menu-grid">{links}</div>'
    )


def footer(profile: dict) -> str:
    line = profile.get("footer_line") or f'把这次{profile["display_name"]}旅行，好好带回家。'
    return f'<div class="shell"><p>{e(line)}</p><a href="#top">回到顶部 ↑</a></div>'


def hero(profile: dict) -> str:
    cover = profile["cover"]
    title_lines = [cover.get("title", profile["display_name"]), "ITINERARY"]
    title_class = "cover-cn-title" if any(re.search(r"[\u3400-\u9fff]", str(line)) for line in title_lines) else "cover-en-title"
    def compact_date(value: str) -> str:
        parts = str(value or "").split("-")
        return ".".join(parts[-2:]) if len(parts) >= 3 else str(value or "")
    start_date = compact_date(profile["trip"].get("start_date", ""))
    end_date = compact_date(profile["trip"].get("end_date", ""))
    dates = cover.get("date_label") or ("日期待定" if not start_date or not end_date or "pending" in (start_date, end_date) else (f'{start_date}—{end_date.split(".")[-1]}' if start_date[:2] == end_date[:2] else f'{start_date}—{end_date}'))
    nights = profile["trip"].get("nights")
    duration = f'{e(profile["trip"].get("days", ""))} 天' + (f'<br>{e(nights)} 晚' if nights is not None else '')
    route_label = cover.get("route_label") or profile.get("route_title", profile["display_name"])
    includes = cover.get("includes") or "住宿 · 餐饮 · 探索"
    image = cover.get("image", "")
    summary_html = f'<p class="lede">{e(cover["summary"])}</p>' if cover.get("show_summary", True) else '<p class="lede" hidden></p>'
    anchors = profile.get("time_anchors", [])[:4]
    anchor_html = ""
    if anchors:
        cards = "".join(
            f'<a href="{e(item.get("href", "#route"))}"><time>{e(item.get("time", "待确认"))}</time><b>{e(item.get("title", "行程确认"))}</b><small>{e(item.get("note", "出发前再次确认"))}</small></a>'
            for item in anchors
        )
        anchor_html = f'<div class="audit-hard-times"><h3>出行时间锚点</h3><div>{cards}</div></div>'
    return (
        f'<img class="jungle-cover-image" src="{e(image)}" alt="{e(profile["display_name"])}旅行封面" fetchpriority="high"><div class="jungle-cover-shade" aria-hidden="true"></div>'
        f'<nav class="nav shell"><a class="brand" href="#top">{e(profile["display_name"])}旅行手册</a></nav>'
        f'<div class="hero-inner shell jungle-cover-copy"><p class="jungle-cover-kicker">{e(cover["kicker"])}</p><h1 class="{title_class}"><span>{e(title_lines[0])}</span><em>{e(title_lines[1])}</em></h1>'
        f'{summary_html}</div>'
        f'<div class="jungle-cover-bottom shell"><div class="jungle-cover-dates"><strong>{e(dates)}</strong><span>{duration}</span></div>'
        f'<div><small>旅行路线</small><b>{e(route_label)}</b></div><div><small>内容包含</small><b>{e(includes)}</b></div></div>{anchor_html}'
    )


def transport(profile: dict) -> str:
    transport = profile["transport"]
    if transport["status"] == "pending":
        legs = [
            {"direction": "去程待确认", "date": "—", "service_number": "待确认", "origin": "出发地", "destination": profile["display_name"], "departure_time": "—", "arrival_time": "—"},
            {"direction": "回程待确认", "date": "—", "service_number": "待确认", "origin": profile["display_name"], "destination": "返回地", "departure_time": "—", "arrival_time": "—"},
        ]
        title = f'出发地 → {profile["display_name"]} · 交通待确认'
        fine = "补充具体航班、车次、日期、机场或车站后，本页会同步更新全部交通卡与说明。"
    else:
        legs = transport["legs"]
        title = transport.get("headline") or f'前往{profile["display_name"]}'
        fine = transport.get("fineprint", "所有时刻以电子客票和出发日前复核为准。")
    cards = ''.join(
        '<div class="flight-card' + (' return-flight' if leg.get("direction", "").startswith("回") else '') + '">'
        f'<div><b>{e(leg.get("service_number"))}</b><small>{e(leg.get("direction"))} · {e(leg.get("date"))}</small></div>'
        f'<div><strong>{e(leg.get("departure_time"))}</strong><span>{e(leg.get("origin"))}</span></div><i>→</i>'
        f'<div><strong>{e(leg.get("arrival_time"))}</strong><span>{e(leg.get("destination"))}</span></div></div>'
        for leg in legs
    )
    return f'<div class="shell flight-grid"><div><span class="section-no">01</span><p class="eyebrow">TRANSPORT</p><h2>{e(title)}</h2></div>{cards}<p class="fineprint">{e(fine)}</p></div>'


def trip_pulse(profile: dict, places: dict[str, dict]) -> str:
    stay = next((item for item in profile.get("stays", []) if item.get("status") == "confirmed" and item.get("place_id")), None)
    if stay and str(stay["place_id"]) in places:
        stay_place = places[str(stay["place_id"])]
        stay_href = map_url(stay_place)
        stay_target = ' target="_blank" rel="noreferrer"'
        stay_label = stay_place["display_name"]
    else:
        stay_href = "#stay"
        stay_target = ""
        stay_label = "住宿待确认"
    return (
        '<div class="shell pulse-grid"><div class="pulse-status">'
        f'<span>TRIP COMPANION · {e(profile.get("year", ""))}</span><small>旅程概览</small>'
        f'<strong>{e(profile.get("trip", {}).get("days", ""))} 天</strong>'
        f'<p>{e(profile["display_name"])}的行程、住宿、餐饮与出发准备，都可以从这里继续。</p></div>'
        '<nav class="pulse-actions" aria-label="旅途快捷入口">'
        '<a href="#route"><b>每日行程</b><span>打开路线</span></a>'
        f'<a href="{e(stay_href)}"{stay_target}><b>住宿</b><span>{e(stay_label)}</span></a>'
        '<a href="#food"><b>吃什么</b><span>餐厅与安心连锁</span></a></nav></div>'
    )


def stays(profile: dict, places: dict[str, dict]) -> str:
    cards = []
    for stay in profile["stays"]:
        if stay["status"] == "pending":
            cards.append('<article class="hotel-card stay-pending"><div class="hotel-copy"><p class="eyebrow">STAY · 待确认</p><h3>住宿待确认</h3><p>酒店尚未确定。确认后将补充准确地址、交通定位和精确物业图片。</p></div></article>')
            continue
        place = places[str(stay["place_id"])]
        dates = f'{stay.get("check_in", "")}—{stay.get("check_out", "")}'
        cards.append(
            f'<article class="hotel-card" data-place-id="{e(place["id"])}"><div class="hotel-visual">{gallery(place, dates)}</div>'
            f'<div class="hotel-copy"><p class="eyebrow">CONFIRMED STAY</p><h3>{e(place["display_name"])}</h3>'
            f'<p class="hotel-fullname">{e(place.get("english_name", ""))}</p><p>{e(place.get("area", ""))} · {e(place.get("description", stay.get("notes", "")))}</p>'
            f'<dl><div><dt>入住</dt><dd>{e(dates)}</dd></div><div><dt>地址</dt><dd>{e(place.get("address", ""))}</dd></div><div><dt>出行</dt><dd>{e(place.get("transport_note", ""))}</dd></div></dl>'
            + (f'<p class="hotel-selected-price"><b>已选价格</b> ¥{e(place["selection_price"].get("nightly_price_cny"))}/间夜 · 全程 ¥{e(place["selection_price"].get("total_price_cny"))}<small>{e(place["selection_price"].get("room"))} · 快照 {e(place["selection_price"].get("snapshot_at"))}</small></p>' if place.get("selection_price") else '')
            + f'<div class="hotel-links"><a href="{e(map_url(place))}" target="_blank" rel="noreferrer">Google Maps ↗</a><a href="{e(place.get("source_url"))}" target="_blank" rel="noreferrer">住宿资料 ↗</a></div></div></article>'
        )
    return '<div class="shell">' + heading('STAY', 'WHERE TO STAY', profile.get('stay_title', '住宿与旅行基地'), profile.get('stay_summary', '')) + ''.join(cards) + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


from _display_labels import transport_label, route_note
from _outfit_advice import outfit_html
from _route_screenshots import screenshots_html

def route_stop(stop: dict, place: dict, index: int) -> str:
    return (
        f'<a class="route-stop" data-place-id="{e(place["id"])}" href="{e(map_url(place))}" target="_blank" rel="noreferrer">'
        f'<i>{index:02d}</i><strong>{e(place["display_name"])}</strong><time>{e(stop.get("arrival_time"))}</time>'
        f'<small class="route-dwell">逗留：{e(stop.get("dwell_minutes"))} 分钟</small><em>地图 ↗</em></a>'
    )


def route(profile: dict, places: dict[str, dict]) -> str:
    days_html = []
    for day_index, day in enumerate(profile["itinerary"], 1):
        stop_parts = []
        stops = day["stops"]
        for index, stop in enumerate(stops, 1):
            place = places[str(stop["place_id"])]
            stop_parts.append('<div class="route-map-segment">' + route_stop(stop, place, index))
            if index < len(stops):
                leg = stops[index]  # Incoming leg belongs to the next stop.
                stop_parts.append(f'<div class="route-leg"><span>{e(transport_label(leg.get("transport_mode")))}</span><b>{e(leg.get("transfer_minutes"))} 分钟</b><small>{e(leg.get("distance_km"))} km · {e(leg.get("estimated_cost"))}</small></div>')
            stop_parts.append('</div>')
        periods = day["periods"]
        def render_period(label: str, key: str) -> str:
            value = periods[key]
            if isinstance(value, dict):
                return f'<strong>{label}</strong><p><b>{e(value.get("title"))}</b><span>{e(value.get("description"))}</span></p>'
            return f'<strong>{label}</strong><p>{e(value)}</p>'
        detail = ''.join(render_period(label, key) for label, key in (("上午", "morning"), ("下午", "afternoon"), ("晚上", "evening")))
        mini = (
            f'<details class="day-route-map"><summary class="route-mobile-summary"><span class="route-title"><small>MINI ROUTE</small><b>{e(day["theme"])}</b></span>'
            '<span class="route-glass-button"><span class="route-open-label">查看路线</span><span class="route-close-label">收起路线</span><i>＋</i></span></summary>'
            f'<div class="route-map-content"><div class="route-map-head"><span>MINI ROUTE</span><div><b>{e(day["theme"])}</b><small>时间、顺序、交通与停留</small></div></div>'
            + (f'<p class="route-distance-note">{e(route_note(day))}</p>' if route_note(day) else '')
            + screenshots_html(day) + f'<div class="route-map-track">{"".join(stop_parts)}</div></div></details>'
        )
        photo = day.get("photo_advice", {})
        suitable = ''.join(f'<li>{e(item)}</li>' for item in photo.get("suitable_shots", []))
        photo_block = (
            '<aside class="photo-note"><div class="photo-note-head"><span>PHOTO NOTES</span><div>'
            f'<b>{e(photo.get("title"))}</b><small>{e(photo.get("lighting"))}</small></div></div>'
            '<div class="photo-note-grid"><div><strong>适合拍摄</strong>'
            f'<ul>{suitable}</ul></div><div><strong>人物拍摄提示</strong><p>{e(photo.get("portrait_tip"))}</p></div></div>'
            + outfit_html(photo) + '</aside>'
        )
        days_html.append(
            f'<details class="day"><summary><span class="day-index">{day_index:02d}</span><span><small>{e(day.get("date"))} · {e(day.get("area", ""))}</small>'
            f'<b>{e(day["theme"])}</b><em>{e(day.get("summary", ""))}</em></span><i>＋</i></summary><div class="day-detail">{detail}</div>{mini}{photo_block}</details>'
        )
    blocks = []
    phases = profile.get("journey_phases")
    if phases and len(phases) > 1:
        for phase in phases:
            selected = [days_html[i-1] for i in phase.get("day_numbers", []) if 1 <= i <= len(days_html)]
            blocks.append(f'<div class="journey-block"><p class="journey-label">{e(phase.get("kicker", "ITINERARY"))}</p><h3>{e(phase["title"])}</h3><div class="days">{"".join(selected)}</div></div>')
    else:
        blocks.append(f'<div class="journey-block journey-block-single"><div class="days">{"".join(days_html)}</div></div>')
    return '<div class="shell">' + heading('01', 'THE ROUTE', profile.get('route_title', f'{profile["trip"]["days"]} 天行程'), profile.get('route_summary', '')) + ''.join(blocks) + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def sight_card(place: dict) -> str:
    marker = place.get("scheduled_label", "可选")
    ratings = [item for item in place.get("ratings", []) if isinstance(item, dict) and item.get("status", "verified") == "verified"]
    if not ratings and place.get("rating") not in (None, ""):
        ratings = [{"platform": place.get("rating_source", "Google"), "rating": place.get("rating"), "review_count": place.get("review_count")}]
    google = next((item for item in ratings if str(item.get("platform", "")).lower() == "google"), None)
    review_html = f'<small>约 {e(google.get("review_count"))} 条</small>' if google and google.get("review_count") not in (None, "") else ''
    rating_html = f'<div class="sight-rating"><strong><b><span aria-hidden="true">★</span>{e(google.get("rating"))}</b>{review_html}</strong></div>' if google else ''
    return (
        f'<article class="sight-card has-visual" data-place-id="{e(place["id"])}">{gallery(place, place.get("area", ""))}<div class="sight-copy">'
        f'<span>{e(place.get("area", ""))}</span><div class="sight-title-row"><h3>{e(place["display_name"])}</h3>{rating_html}</div>'
        f'<b>{e(marker)}</b><div class="sight-facts"><span>建议停留 {e(place.get("duration_minutes"))} 分钟</span></div><p>{e(place.get("description", ""))}</p>'
        f'<p class="hours-line"><b>开放</b>{e(place.get("hours"))} · {e(place.get("closed_days"))}</p>'
        f'<a href="{e(map_url(place))}" target="_blank" rel="noreferrer">Google Maps ↗</a>{source_link(place)}</div></article>'
    )


def sights(profile: dict, places: dict[str, dict]) -> str:
    cards = ''.join(sight_card(place) for place in places.values() if place.get("type") == "sight")
    content = heading('02', 'SIGHTS', profile.get('sights_title', '景点指南'), profile.get('sights_summary', ''))
    content += f'<details class="mobile-section-fold" open><summary><b>查看全部景点</b><i>＋</i></summary><div class="sights-grid">{cards}</div></details>'
    return '<div class="shell">' + content + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def shop_card(place: dict) -> str:
    return (
        f'<article class="shop-row" data-shopping-card data-place-id="{e(place["id"])}"><div class="shop-visual">{gallery(place, place.get("area", ""))}</div><div class="shop-copy">'
        f'<span>{e(place.get("area", ""))} · {e(place.get("category", ""))}</span><h3>{e(place["display_name"])}</h3><strong>{e(place.get("scheduled_label", place.get("route_fit", "备选 · 按区域顺路加入")))}</strong><p>{e(place.get("description", ""))}</p>'
        f'<p class="shop-brands"><b>值得逛 / 买</b>{e(place.get("brand_highlights", ""))}</p>'
        f'<small>{e(place.get("buying_tip", ""))}</small><small>开放：{e(place.get("hours"))} · {e(place.get("closed_days"))}</small></div><div class="shop-actions"><a href="{e(map_url(place))}" target="_blank">地图 ↗</a>{source_link(place)}</div></article>'
    )


def shops(profile: dict, places: dict[str, dict]) -> str:
    groups = []
    for group in profile["module_groups"]["shopping"]:
        cards = ''.join(shop_card(places[str(item["place_id"])]) for item in group["items"])
        groups.append(f'<details class="shop-region"><summary><b>{e(group["title"])}</b><span>{e(group.get("subtitle", "商场与店铺"))}</span><i>＋</i></summary><div class="shop-list">{cards}</div></details>')
    souvenirs = [place for place in places.values() if place.get("type") == "souvenir"]
    souvenir_cards = ''.join(
        f'<article class="shop-row souvenir-card" data-shopping-card data-place-id="{e(place["id"])}"'+ (' style="display:block"' if not image_files(place) else '') + '>'
        + (f'<div class="shop-visual">{gallery(place)}</div>' if image_files(place) else '')
        + f'<div class="shop-copy"><span>{e(place.get("category", "当地产品"))}</span><h3>{e(place["display_name"])}</h3>'
        f'<p>{e(place.get("description", ""))}</p><p class="shop-brands"><b>为什么值得买</b>{e(place.get("why_buy", ""))}</p><p><b>适合送给</b>{e(place.get("best_for", ""))}</p>'
        f'<small>哪里买：{e(place.get("where_to_buy", ""))}</small><small>{e(place.get("buying_tip", ""))}</small></div></article>' for place in souvenirs
    )
    souvenir = f'<details class="shop-region souvenir-section" data-souvenir-list><summary><b>{e(profile.get("souvenir_title", "伴手礼与值得带走的东西"))}</b><span>{len(souvenirs)} 项可比较</span><i>＋</i></summary><div class="shop-list souvenir-shop-list">{souvenir_cards}</div></details>'
    return '<div class="shell">' + heading('03', 'SHOPPING', profile.get('shopping_title', '购物与当地好物'), profile.get('shopping_summary', '')) + ''.join(groups) + souvenir + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def experience_card(place: dict) -> str:
    risk = f'<p class="experience-risk"><b>风险评估</b>{e(place.get("risk_assessment"))}</p>' if place.get("hazardous") else ''
    first_image = (place.get("images") or [{}])[0]
    media_class = str(first_image.get("media_class", "")) if isinstance(first_image, dict) else ""
    brand_class = " is-brand-asset" if media_class == "official_brand_asset" else ""
    return (
        f'<article class="movement-card has-visual{brand_class}" data-experience-card data-place-id="{e(place["id"])}"><div class="movement-visual">{gallery(place, place.get("area", ""))}</div><div class="movement-copy"><span>{e(place.get("area", ""))} · {e(place.get("category", ""))}</span>'
        f'<h3>{e(place["display_name"])}</h3><strong>{e(place.get("scheduled_label", place.get("distance_from_stay", "")))}</strong><p>{e(place.get("description", ""))}</p>{risk}'
        f'<p class="hours-line"><b>开放</b>{e(place.get("hours"))} · {e(place.get("closed_days"))}</p><div><a href="{e(map_url(place))}" target="_blank">Google Maps ↗</a>{source_link(place)}</div></div></article>'
    )


def experiences(profile: dict, places: dict[str, dict]) -> str:
    groups = []
    for group in profile["module_groups"]["experiences"]:
        cards = ''.join(experience_card(places[str(item["place_id"])]) for item in group["items"])
        groups.append(f'<details class="mobile-section-fold experience-category"><summary><b>{e(group["title"])}</b><i>展开 ＋</i></summary><div class="movement-grid">{cards}</div></details>')
    return '<div class="shell">' + heading('04', 'LOCAL EXPERIENCES', profile.get('experiences_title', '试试真正属于当地的体验'), profile.get('experiences_summary', '')) + ''.join(groups) + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def restaurant_card(place: dict) -> str:
    ratings = [item for item in place.get("ratings", []) if isinstance(item, dict) and item.get("status", "verified") == "verified"]
    if not ratings and place.get("rating") not in (None, ""):
        ratings = [{"platform": place.get("rating_source", "Google"), "rating": place.get("rating"), "review_count": place.get("review_count")}]
    rating_html = ''.join(f'<span><b>{e(item.get("platform"))} {e(item.get("rating"))}</b>' + (f'<small>约 {e(item.get("review_count"))} 条</small>' if item.get("review_count") not in (None, "") else '') + '</span>' for item in ratings)
    rating_block = f'<div class="restaurant-rating">{rating_html}</div>' if rating_html else ''
    street_view = any(isinstance(image, dict) and image.get("source_type") == "google_street_view" for image in place.get("images", []))
    visual_label = "门店街景 · 位置参考" if street_view else place.get("area", "")
    return (
        f'<article class="restaurant" data-place-id="{e(place["id"])}">{gallery(place, visual_label)}<div class="restaurant-body">'
        f'<div class="restaurant-top"><h3><span>{e(place.get("local_name", place["display_name"]))}</span><small>{e(place.get("english_name", ""))}</small></h3>{rating_block}</div><p class="cuisine">{e(place.get("cuisine", ""))} · {e(place.get("area", ""))}</p>'
        f'<p>招牌：{e(place.get("signature_dishes", ""))}</p><p class="restaurant-day">{e(place.get("scheduled_label", place.get("route_fit", "备选 · 按区域顺路加入")))}</p>'
        f'<p class="restaurant-why"><b>为什么值得去</b>{e(place.get("description", ""))}</p><p class="hours-line"><b>营业</b>{e(place.get("hours"))} · {e(place.get("closed_days"))}</p>'
        f'<div class="restaurant-actions"><a class="map-link" href="{e(map_url(place))}" target="_blank">Google Maps 导航 ↗</a><a href="{e(place.get("source_url"))}" target="_blank">官网 / 来源 ↗</a></div>'
        f'<div class="restaurant-foot"><strong>{e(place.get("price_per_person", ""))} / 人</strong><span>距离与开放时间以出发前复核为准</span></div></div></article>'
    )


def food(profile: dict, places: dict[str, dict]) -> str:
    model = profile["module_groups"]["food"]
    dining_items = profile.get("dining_plan", [])
    dining_plan = ""
    if dining_items:
        dining_rows = "".join(
            f'<article class="dining-day"><div class="dining-when"><time>{e(item.get("date"))}</time><span>{e(item.get("meal"))}</span></div>'
            f'<div class="dining-copy"><b>{e(item.get("title"))}</b><div class="dining-meta"><span>{e(item.get("category", ""))}</span><strong>{e(item.get("budget", ""))}</strong></div>'
            f'<p>{e(item.get("note", ""))}</p></div></article>'
            for item in dining_items
        )
        dining_note = profile.get("dining_plan_note", "预算为每人估算；动态价格、酒水、税费与服务费以现场为准。")
        dining_plan = (
            '<details class="audit-current-focus dining-plan"><summary><b>本次餐厅</b><span>展开 ＋</span></summary>'
            '<div class="dining-plan-body"><header><a href="#booking">查看预约 <span aria-hidden="true">↗</span></a></header>'
            f'<div class="dining-days">{dining_rows}</div><p class="dining-footnote">{e(dining_note)}</p></div></details>'
        )
    primer = ''.join(f'<div><b>{e(item.get("term"))}</b><span>{e(item.get("meaning"))}</span><p>{e(item.get("note", ""))}</p></div>' for item in model["menu_primer"])
    guide = model["menu_guide"]
    guide_cards = ''.join(f'<article><h4>{e(item.get("title"))}</h4><p>{e(item.get("note"))}</p></article>' for item in guide["cards"])
    chapters = [
        '<details class="food-chapter menu-primer" open><summary><b>菜单与点餐提示</b><i>＋</i></summary>'
        f'<div class="menu-editorial"><p class="eyebrow">{e(guide.get("kicker"))}</p><h3>{e(guide.get("title"))}</h3><p class="menu-intro">{e(guide.get("intro"))}</p>'
        f'<div class="menu-guide-grid">{guide_cards}</div><details class="menu-dictionary"><summary><b>常见菜名与菜单表达</b><span>{len(model["menu_primer"])} 项</span><i>＋</i></summary><div class="menu-primer-grid">{primer}</div></details></div></details>'
    ]
    snacks = model.get("local_snacks", [])
    if snacks:
        snack_cards = ''.join(
            f'<article class="snack-card"><h3>{e(item.get("name") or item.get("local_name"))}</h3><small>{e(item.get("local_name", ""))}</small>'
            f'<p>{e(item.get("description"))}</p><dl><div><dt>为什么要试</dt><dd>{e(item.get("why_try"))}</dd></div><div><dt>哪里找</dt><dd>{e(item.get("where_to_find"))}</dd></div></dl></article>'
            for item in snacks
        )
        chapters.append(f'<details class="food-chapter local-snacks"><summary><b>当地小吃推荐</b><i>＋</i></summary><div class="snack-grid">{snack_cards}</div></details>')
    for key, title in (("dedicated_trip", "值得专程去"), ("reliable_chains", "本地连锁安心选")):
        items = model.get(key, [])
        if not items:
            continue
        cards = ''.join(restaurant_card(places[str(item["place_id"])]) for item in items)
        chapters.append(f'<details class="food-chapter"><summary><b>{title}</b><i>＋</i></summary><div class="restaurant-grid">{cards}</div></details>')
    return '<div class="shell">' + heading('05', 'FOOD GUIDE', profile.get('food_title', '餐饮指南'), profile.get('food_summary', '')) + dining_plan + ''.join(chapters) + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def checklist(items: list, css: str) -> str:
    rows = ''
    for index, item in enumerate(items, 1):
        title = item.get("item") or item.get("title") or ""
        timing = item.get("timing") or ""
        note = item.get("detail") or item.get("note") or ""
        timing_html = f'<em>{e(timing)}</em>' if timing else ''
        note_html = f'<small>{e(note)}</small>' if note else ''
        priority = item.get('priority', '建议')
        level = {'必须': 'must', '建议': 'recommended', '随缘': 'optional'}.get(priority, 'recommended')
        badge = f'<em class="packing-priority is-{level}">{e(priority)}</em>'
        rows += f'<li><label><input type="checkbox"><span>{index:02d}</span><div><b>{e(title)}</b>{badge}{timing_html}{note_html}</div></label></li>'
    return f'<ol class="{css}">{rows}</ol>'


def booking(profile: dict) -> str:
    model = profile["module_groups"]["preparation"]
    model = dict(model, confirm_ahead=sorted(model["confirm_ahead"], key=lambda item: {"必须": 0, "建议": 1, "随缘": 2}.get(item.get("priority"), 1)))
    blocks = (
        f'<div class="prepare-block"><div class="prepare-heading"><span>01</span><div><h3>必备物品</h3><p>按必须、建议、随缘排序，依次准备。</p></div></div>{checklist(sorted(model["essentials"], key=lambda item: {"必须": 0, "建议": 1, "随缘": 2}.get(item.get("priority"), 1)), "packing-checklist")}</div>'
        f'<div class="prepare-block"><div class="prepare-heading"><span>02</span><div><h3>需要预约与确认</h3><p>按必须、建议、随缘排序，依次确认。</p></div></div>{checklist(model["confirm_ahead"], "booking-checklist")}</div>'
    )
    return '<div class="shell">' + heading('06', 'BEFORE DEPARTURE', profile.get('preparation_title', '出发前准备'), profile.get('preparation_summary', '')) + blocks + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def words(profile: dict) -> str:
    model = profile["module_groups"]["language"]
    def language_set(keyword_groups: list, phrase_groups: list, label: str) -> str:
        def item_record(item, primary):
            if isinstance(item, dict):
                return item
            left, separator, right = str(item).partition("｜")
            return {primary: left.strip(), "meaning": right.strip() if separator else ""}
        vocab = []
        for group in keyword_groups:
            items = ''.join(f'<div><b>{e(record.get("term"))}</b>' + (f'<small>{e(record.get("reading"))}</small>' if record.get("reading") else '') + f'<span>{e(record.get("meaning"))}</span></div>' for record in (item_record(item, "term") for item in group["items"]))
            vocab.append(f'<details class="vocab"><summary><h3>{e(group["title"])}</h3><span>{len(group["items"])} 词</span><i>＋</i></summary><div class="vocab-items">{items}</div></details>')
        phrases = []
        for group_index, group in enumerate(phrase_groups, 1):
            items = ''.join(f'<div><span>{index:02d}</span><p><b>{e(record.get("sentence"))}</b>' + (f'<small>{e(record.get("reading"))}</small>' if record.get("reading") else '') + f'<em>{e(record.get("meaning"))}</em></p></div>' for index, record in enumerate((item_record(item, "sentence") for item in group["items"]), 1))
            phrases.append(f'<details class="phrase-group"><summary><span>{group_index:02d}</span><b>{e(group["title"])}</b><em>{len(group["items"])} 句</em><i>＋</i></summary><div class="phrase-grid">{items}</div></details>')
        return f'<div class="language-edition"><h3>{e(label)}</h3><div class="vocab-grid">{"".join(vocab)}</div><div class="phrase-title"><p class="eyebrow">HIGH-FREQUENCY PHRASES</p><h3>现场高频句</h3></div><div class="phrase-groups">{"".join(phrases)}</div></div>'
    content = language_set(model["keyword_groups"], model["phrase_groups"], model.get("local_label", "当地语言"))
    if model.get("english_keyword_groups") and model.get("english_phrase_groups"):
        content += language_set(model["english_keyword_groups"], model["english_phrase_groups"], "英语备用")
    return '<div class="shell">' + heading('07', 'LANGUAGE COMPANION', profile.get('language_title', '语言随行锦囊'), profile.get('language_summary', '')) + content + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def tips(profile: dict) -> str:
    folds = []
    for group in profile["module_groups"]["travel_notes"]:
        topics = ''.join(f'<div data-tip-priority="{e(item.get("priority", ""))}"><h4>{e(item.get("title"))}</h4><p>{e(item.get("note"))}</p></div>' for item in group["items"])
        folds.append(f'<details class="tips-page tips-fold"><summary><span><small>{e(group.get("kicker", "LOCAL NOTES"))}</small><b>{e(group["title"])}</b><em>{e(group.get("summary", ""))}</em></span><i>＋</i></summary><div class="tips-fold-content"><div class="tips-grid">{topics}</div></div></details>')
    return '<div class="shell">' + heading('08', 'LOCAL TRAVEL NOTES', profile.get('notes_title', '到了当地，心里有数'), profile.get('notes_summary', '')) + ''.join(folds) + '<a class="back-to-contents" href="#contents">↑ 回到目录</a></div>'


def adapt_runtimes(profile: dict, canonical_root: Path) -> list[dict]:
    destination = str(profile["display_name"])
    slug = re.sub(r'[^a-z0-9]+', '-', str(profile["destination"]).lower()).strip('-') or 'travel'
    experience_groups = profile.get("module_groups", {}).get("experiences", [])
    experience_summary = "、".join(str(group.get("title", "")) for group in experience_groups[:2] if group.get("title")) or "当地值得体验的项目"
    labels = [
        ["#stay", "01", "行程", "酒店、路线、时间与停留"],
        ["#sights", "02", "景点指南", "已安排与可选"],
        ["#shops", "03", "购物", "店铺、集市与伴手礼"],
        ["#move", "04", "当地特色体验", experience_summary],
        ["#food", "05", "餐饮指南", "当地小吃、专程餐厅与安心连锁"],
        ["#booking", "06", "出发前准备", "预约、确认与行李清单"],
        ["#words", "07", "语言随行锦囊", "高频词与现场表达"],
        ["#tips", "08", "旅游贴士", "健康、安全与文化"],
    ]
    day_themes = [str(day.get("theme", f"第 {index} 天")) for index, day in enumerate(profile.get("itinerary", []), 1)]
    place_lookup = place_index(profile)
    trip_mode_days = []
    for day in profile.get("itinerary", []):
        trip_stops = []
        day_stops = day.get("stops", [])
        for stop_index, stop in enumerate(day_stops):
            # Source transfers arrive at a stop; Trip Mode shows them after it.
            next_stop = day_stops[stop_index + 1] if stop_index + 1 < len(day_stops) else {}
            place = place_lookup.get(str(stop.get("place_id")), {})
            coordinates = place.get("coordinates")
            latitude = place.get("latitude")
            longitude = place.get("longitude")
            if isinstance(coordinates, dict):
                latitude = coordinates.get("latitude", coordinates.get("lat", latitude))
                longitude = coordinates.get("longitude", coordinates.get("lng", coordinates.get("lon", longitude)))
            elif isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
                latitude, longitude = coordinates[0], coordinates[1]
            trip_stops.append({
                "place_id": stop.get("place_id"),
                "name": place.get("display_name", stop.get("place_id", "")),
                "time": stop.get("arrival_time", ""),
                "dwell_minutes": stop.get("dwell_minutes", 0),
                "transport_mode": transport_label(next_stop.get("transport_mode", "")),
                "transfer_minutes": next_stop.get("transfer_minutes"),
                "distance_km": next_stop.get("distance_km"),
                "estimated_cost": stop.get("estimated_cost", ""),
                "practical_note": stop.get("practical_note", ""),
                "time_guard": stop.get("time_guard", ""),
                "map_query": place.get("map_query", place.get("display_name", "")),
                "map_url": map_url(place) if place else "",
                "latitude": latitude,
                "longitude": longitude,
            })
        time_range = ""
        if trip_stops:
            time_range = f'{trip_stops[0].get("time", "")}–{trip_stops[-1].get("time", "")}'
        trip_mode_days.append({
            "date": day.get("date", ""), "theme": day.get("theme", ""), "summary": day.get("summary", ""),
            "time_range": day.get("time_range", time_range), "pace_label": day.get("pace_label", "按时推进"),
            "stops": trip_stops, "shopping_advice": day.get("shopping_advice", {}),
            "photo_advice": day.get("photo_advice", {}),
        })
    result = []
    for name in ("trip-mode.js", "itinerary-customizer.js", "checklist-memory.js", "better-interface.css"):
        source = (canonical_root / name).read_text(encoding="utf-8")
        source = source.replace("bali-trip-companion", slug + "-trip-companion").replace("bali-trip-day", slug + "-trip-day").replace("bali-packing-2026", slug + "-packing")
        source = source.replace("2026 巴厘岛双人旅行手册", f'{profile.get("year", "")} {destination}旅行手册').replace("巴厘岛 人像 拍照 机位", destination + " 人像 拍照 机位")
        source = source.replace("巴厘岛旅行手册-Agent可补全-", destination + "旅行手册-Agent可补全-")
        source = source.replace("巴厘岛攻略修改申请-", destination + "攻略修改申请-")
        source = source.replace("新增景点、餐厅、购物、瑜伽健身舞蹈或 SPA 时须进入相应介绍。", "新增景点、餐厅、购物或当地特色体验时须进入相应介绍。")
        if name == "itinerary-customizer.js":
            source = re.sub(r'var titles=\[.*?\];', 'var titles=' + json.dumps(day_themes, ensure_ascii=False, separators=(",", ":")) + ';', source, count=1, flags=re.S)
        if name == "trip-mode.js":
            payload = json.dumps(trip_mode_days, ensure_ascii=False, separators=(",", ":"))
            if "var TRIP_MODE_DATA=[];" not in source:
                raise ValueError("trip-mode.js missing stable TRIP_MODE_DATA injection marker")
            source = source.replace("var TRIP_MODE_DATA=[];", "var TRIP_MODE_DATA=" + payload + ";", 1)
        if name == "better-interface.css":
            source = re.sub(r'VOL\. 01\s*/\s*BALI 2026', f'VOL. 01 / {destination} {profile.get("year", "")}', source)
            source = source.replace('cover-location.jpg', str(profile.get("cover", {}).get("image", "")))
        result.append({"path": name, "content": source})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    places = place_index(profile)
    bind_schedule_labels(profile, places)
    system = profile.get("ui_system", "current-system")
    if system not in {"current-system", "canonical"}:
        raise SystemExit("unknown UI system")
    canonical = Path(__file__).resolve().parent.parent / "assets" / system / "product"
    fragments = {
        ".hero": hero(profile), ".trip-pulse": trip_pulse(profile, places), "#contents": contents(profile), ".flight-band": transport(profile), "#stay": stays(profile, places),
        "#route": route(profile, places), "#sights": sights(profile, places), "#shops": shops(profile, places),
        "#move": experiences(profile, places), "#food": food(profile, places), "#booking": booking(profile),
        "#words": words(profile), "#tips": tips(profile), ".mobile-menu-panel": mobile_menu(profile), "body > footer": footer(profile),
    }
    if system == "current-system":
        from _current_system_adapter import runtime_bindings, preparation_html
        fragments["#booking"] = preparation_html(profile, fragments["#booking"])
        runtime = runtime_bindings(profile)
    else:
        runtime = adapt_runtimes(profile, canonical)
    bindings = {"ui_system": system, "html": [{"selector": key, "inner_html": value} for key, value in fragments.items()], "runtime_files": runtime}
    args.output.write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS generated {len(fragments)} canonical component families and {len(bindings['runtime_files'])} destination runtimes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
