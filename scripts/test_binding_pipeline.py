#!/usr/bin/env python3
"""Regression test for profile -> bindings -> canonical workbench rendering."""
from __future__ import annotations

import argparse
import copy
from contextlib import nullcontext
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def image(name: str) -> dict:
    return {"file": name, "source_type": "official", "source_page": "https://example.com", "download_url": "https://example.com/image.jpg", "source_identity_bound": True, "visually_confirmed": False, "watermark_checked": False, "subject_verified": False}


def place(pid: str, ptype: str, images: int = 3) -> dict:
    sample_names = {"experience-1": "日归温泉结构样卡一", "experience-2": "城市温泉结构样卡二", "experience-3": "海滨温泉结构样卡三", "experience-4": "传统文化结构样卡一", "experience-5": "传统文化结构样卡二", "experience-6": "传统文化结构样卡三", "experience-7": "水岸体验结构样卡一", "experience-8": "水岸体验结构样卡二", "experience-9": "水岸体验结构样卡三", "shop-1": "鞋履与运动品牌结构样卡", "shop-2": "药妆与生活杂货结构样卡", "shop-3": "动漫与角色商品结构样卡"}
    record_no = int(pid.split("-")[-1]) if "-" in pid and pid.split("-")[-1].isdigit() else 1
    data = {"id": pid, "type": ptype, "display_name": sample_names.get(pid, pid.title()), "map_query": pid, "source_url": "https://example.com", "latitude": 35.68 + record_no * 0.003, "longitude": 139.69 + record_no * 0.004, "description": "这是用于结构回归测试的完整地点说明，包含现场能看到什么、为什么值得加入、适合哪些旅行者、建议停留时间以及怎样顺路安排，避免使用没有信息量的占位短句。", "area": "Central", "hours": "09:00–18:00", "closed_days": "none", "images": [image(f"assets/{pid}-{n}.jpg") for n in range(images)]}
    if ptype == "shop":
        data.update({"category": "商场", "buying_tip": "按楼层和品牌清单集中购买", "brand_highlights": "鞋履、药妆、生活杂货与当地设计品牌", "scheduled_label": "可顺路加入"})
    google_rating = round(4.1 + (record_no % 5) * 0.1, 1)
    google_reviews = 700 + record_no * 137
    if ptype in {"sight", "restaurant"}:
        data.update({"rating": google_rating, "review_count": google_reviews, "rating_source": "Google", "ratings": [{"platform": "Google", "status": "verified", "rating": google_rating, "review_count": google_reviews, "source_url": f"https://example.com/google/{pid}", "verified_at": "2026-08-25"}], "duration_minutes": 60, "scheduled_label": "可选"})
    if ptype == "restaurant":
        cuisine_no = (int(pid.split("-")[-1]) - 1) % 4 + 1
        data.update({"local_name": f"構造試験食堂{record_no}", "english_name": f"Regression Restaurant {record_no}", "cuisine": f"local-{cuisine_no}", "signature_dishes": "炭火烤鱼与当季蔬菜套餐", "price_per_person": "约¥2,000–3,500", "category": "restaurant", "ratings": [{"platform": "Google", "status": "verified", "rating": google_rating, "review_count": google_reviews, "source_url": f"https://example.com/google/{pid}", "verified_at": "2026-08-25"}]})
    if ptype == "souvenir":
        data.update({"category": "当地食品", "why_buy": "具有明确的当地风味和稳定口碑，包装方便比较，也适合作为旅行记忆。", "best_for": "家人、同事与喜欢地方风味的朋友", "where_to_buy": "车站百货、机场官方商店", "buying_tip": "比较保质期、独立包装和携带温度后再购买。"})
    if ptype == "experience":
        data["experience_type"] = "wellness" if record_no <= 3 else ("culture" if record_no <= 6 else "nature")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        help="Keep the generated regression fixture in this directory for browser QA.",
    )
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    if args.output:
        output = args.output.resolve()
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)
        workspace = nullcontext(str(output))
    else:
        workspace = tempfile.TemporaryDirectory(prefix="travel-bindings-")
    with workspace as temp:
        root = Path(temp)
        workbench = root / "workbench"
        places = (
            [place(f"sight-{n}", "sight", 1) for n in range(1, 9)]
            + [place(f"shop-{n}", "shop") for n in range(1, 9)]
            + [place(f"souvenir-{n}", "souvenir") for n in range(1, 7)]
            + [place(f"experience-{n}", "experience") for n in range(1, 10)]
            + [place(f"food-{n}", "restaurant") for n in range(1, 17)]
            + [place("support-1", "other", 0)]
        )
        profile = {"ui_system": "canonical",
            "destination": "Example City UI Regression", "display_name": "示例城结构测试", "navigation_brand": "EXAMPLE CITY QA", "country": "Testland", "local_rating_platform": "Google", "year": "2026", "aliases": ["Example City"], "test_fixture": True,
            "trip": {"start_date": "2026-01-01", "end_date": "2026-01-01", "days": 1, "rhythm": "standard", "travelers": "two", "interests": [], "constraints": [], "experience_mode": "expanded"},
            "cover": {"kicker": "EXAMPLE CITY QA GUIDE", "title": "示例城结构测试", "summary": "用于验证版式、组件与数据合同，不作为旅行推荐。", "image": "assets/cover.jpg", "tags": ["1 day"], "source_type": "generated-fixture", "source_page": "local-regression-fixture", "source_identity_bound": True},
            "transport": {"status": "pending", "legs": []}, "stays": [{"status": "pending", "place_id": None, "check_in": None, "check_out": None, "notes": "pending"}], "journey_phases": [],
            "itinerary": [{"date": "2026-01-01", "theme": "城市初见", "summary": "从中央车站进入核心街区，串联三处城市地标后以顺路购物收尾。", "periods": {"morning": {"title": "车站与城市入口", "description": "上午从中央车站步行到 Sight-1，完成城市方向辨认后停留参观，并预留短暂休息。"}, "afternoon": {"title": "核心街区串联", "description": "下午依次前往 Sight-2 与 Sight-3，按相邻街区顺序游览，中途安排简短午餐和步行缓冲。"}, "evening": {"title": "商店与晚餐收尾", "description": "傍晚前往 Shop-1 集中购买所需物品，随后在车站周边用餐并按闭店时间返回。"}}, "stops": [{"place_id": pid, "arrival_time": f"{10+i*2:02d}:00", "dwell_minutes": 60 if i < 3 else 45, "transport_mode": "步行", "transfer_minutes": 15 if i < 3 else 20, "distance_km": 1 if i < 3 else 1.5, "estimated_cost": "0", "practical_note": f"在 {pid.title()} 先看核心空间和主要景观，再根据现场人流选择支线，避免重复折返。", "time_guard": f"{11+i*2:02d}:10 前离开，排队超过 20 分钟就跳过"} for i, pid in enumerate(("sight-1", "sight-2", "sight-3", "shop-1"))]}],
            "module_groups": {
                "shopping": [{"title": "城市购物", "subtitle": "商场与店铺", "items": [{"place_id": f"shop-{n}"} for n in range(1, 9)]}],
                "experiences": [{"title": "温泉与泡汤体验", "items": [{"place_id": f"experience-{n}"} for n in range(1, 4)]}, {"title": "传统文化体验", "items": [{"place_id": f"experience-{n}"} for n in range(4, 7)]}, {"title": "水岸与自然体验", "items": [{"place_id": f"experience-{n}"} for n in range(7, 10)]}],
                "food": {"menu_guide": {"kicker": "READING A LOCAL MENU", "title": "先看懂菜单，再决定怎么点。", "intro": "先确认菜品结构、份量、过敏原和结账规则，再进入常见菜名词典。", "cards": [{"title": f"点餐判断 {n}", "note": "这是用于验证菜单导读卡片层级、信息密度和两列排版的完整说明文字，不能退化为一行纯文本。"} for n in range(1, 5)]}, "menu_primer": [{"term": f"menu {n}", "meaning": "menu expression", "note": "用于说明这项当地菜单表达在点单时的实际含义与使用场景。"} for n in range(8)], "dedicated_trip": [{"place_id": f"food-{n}"} for n in range(1, 9)], "reliable_chains": [{"place_id": f"food-{n}"} for n in range(9, 13)]},
                "preparation": {"essentials": [{"item": f"必备事项 {n}", "detail": "出发前准备说明"} for n in range(12)], "confirm_ahead": [{"item": f"确认事项 {n}", "detail": "出发前确认说明"} for n in range(12)], "visa": {"traveler_nationality": "中国普通护照", "status": "visa_required", "application_channel": "authorized_agent", "channel_summary": "须通过所属领区日本使领馆指定旅行社办理。", "channel_evidence_url": "https://example.com/authorized-agents", "jurisdiction_basis": "按申请人长期居住地所属领区", "title": "日本签证与入境准备", "summary": "按实际旅行频率选择适合的申请路径。", "official_source_url": "https://example.com/visa", "checked_at": "2026-08-31", "options": [{"label": label, "title": title, "summary": "结构测试签证选项说明。", "economic_reference": "结构测试经济条件说明，不代表实际政策。", "economic_reference_kind": "market", "economic_source_url": "https://example.com/economic", "requirements": ["护照与申请表", "身份与居住证明", "收入或资产证明"]} for label, title in (("偶尔赴日", "单次签证"), ("未来常去", "三年多次"), ("高频旅行", "五年多次"))], "items": [{"title": f"签证事项{n}", "note": "按官方材料清单准备并在递交前复核。"} for n in range(1, 5)]}},
                "language": {"local_label": "日语与罗马音", "keyword_groups": [{"title": f"关键词场景 {g}", "items": [{"term": f"term {g}-{n}", "reading": f"reading {g}-{n}", "meaning": "meaning"} for n in range(5)]} for g in range(5)], "phrase_groups": [{"title": f"句子场景 {g}", "items": [{"sentence": f"sentence {g}-{n}", "reading": f"reading {g}-{n}", "meaning": "meaning"} for n in range(5)]} for g in range(5)], "english_keyword_groups": [{"title": f"英语关键词场景 {g}", "items": [{"term": f"English term {g}-{n}", "meaning": "中文含义"} for n in range(5)]} for g in range(5)], "english_phrase_groups": [{"title": f"英语句子场景 {g}", "items": [{"sentence": f"English sentence {g}-{n}", "meaning": "中文含义"} for n in range(5)]} for g in range(5)]},
                "travel_notes": [{"category": category, "title": f"当地贴士 {g}", "summary": "这段摘要说明目的地现场判断、常见例外和实际应对方式，帮助旅行者提前作出准备。", "items": [{"title": f"现场决策 {g}-{n}", "note": "抵达现场后先根据当天开放情况和人流判断是否按原计划行动。遇到关闭或拥挤时，立即使用同区域替代方案并保留返程时间。"} for n in range(4)]} for g, category in enumerate(("climate", "etiquette", "transport", "safety", "payment"))]
            },
            "places": places, "render_bindings_file": "render-bindings.json"
        }
        profile["module_groups"]["food"]["local_snacks"] = [{"name": f"小吃{n}", "local_name": f"郷土菓子{n}", "english_name": f"Local snack {n}", "description": "当地常见的小吃结构样例，用于验证展示。", "why_try": "能快速理解地方口味与食材。", "where_to_find": "车站、市场与老店。"} for n in range(1, 5)]
        profile["itinerary"][0]["shopping_advice"] = {"title": "今天顺路买", "description": "只安排路线附近的商店。", "url": "#shops", "link_label": "查看购物指南"}
        profile["itinerary"][0]["photo_advice"] = {"title": "城市街景人像", "lighting": "傍晚利用建筑阴影和街道纵深拍摄。", "suitable_shots": ["车站立面与通勤人流", "河岸步道与城市天际线"], "portrait_tip": "人物站在阴影边缘，用街道线条形成纵深，不靠近仪式或影响通行。", "shooting_plan": [{"time": "10:20", "title": "Sight-1·建筑纵深", "note": "手机用1×镜头平视取景并下调曝光；相机用35mm、f/5.6保持建筑与人物清晰。"}, {"time": "15:40", "title": "Shop-1·街角动态", "note": "手机连拍过街动作；相机用50mm和1/250秒凝固人物，拍摄前确认店内规则。"}], "samples": []}
        profile["itinerary"][0]["photo_advice"]["outfit_advice"] = {"women": "外套叠穿上衣和长裤，配步行鞋适应河岸路线。", "men": "针织衫叠穿轻便外套、长裤和运动鞋，保持活动方便。", "practical_note": "沿河风大时加外层，按当天预报增减衣物。"}
        profile_path = root / "profile.json"
        profile_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        fraudulent = copy.deepcopy(profile)
        fraudulent.pop("test_fixture", None)
        for record in fraudulent["places"]:
            if record.get("type") == "restaurant":
                record["ratings"] = [
                    {"platform": "Google", "rating": 4.3, "review_count": 13742, "source_url": "https://example.com/google", "verified_at": "2026-08-25"},
                    {"platform": "Tabelog", "rating": 3.3, "review_count": 120, "source_url": "https://example.com/tabelog", "verified_at": "2026-08-25"},
                ]
        fraudulent_path = root / "fraudulent-profile.json"
        fraudulent_path.write_text(json.dumps(fraudulent, ensure_ascii=False), encoding="utf-8")
        fraudulent_result = subprocess.run([sys.executable, str(scripts / "validate_destination_data.py"), str(fraudulent_path)], capture_output=True, text=True, encoding='utf-8')
        if fraudulent_result.returncode == 0 or "repeat one identical score/review pair" not in fraudulent_result.stdout:
            print("FAIL validator did not block repeated production-looking restaurant ratings")
            return 2
        too_few_sights = copy.deepcopy(profile)
        too_few_sights["places"] = [record for record in too_few_sights["places"] if record.get("id") != "sight-8"]
        too_few_path = root / "too-few-sights.json"
        too_few_path.write_text(json.dumps(too_few_sights, ensure_ascii=False), encoding="utf-8")
        too_few_result = subprocess.run([sys.executable, str(scripts / "validate_destination_data.py"), str(too_few_path)], capture_output=True, text=True, encoding='utf-8')
        if too_few_result.returncode == 0 or "at least 8 sights" not in too_few_result.stdout:
            print("FAIL validator did not enforce the eight-sight destination floor")
            return 2
        commands = [
            [sys.executable, str(scripts / "validate_destination_data.py"), str(profile_path), "--allow-test-fixture"],
            [sys.executable, str(scripts / "install_ui_system.py"), str(workbench), "--system", "canonical"],
            [sys.executable, str(scripts / "build_render_bindings.py"), str(profile_path), str(root / "render-bindings.json")],
            [sys.executable, str(scripts / "render_destination.py"), str(profile_path), str(workbench)],
        ]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            if result.returncode:
                print(result.stdout + result.stderr)
                return result.returncode
        rendered = (workbench / "index.html").read_text(encoding="utf-8")
        if "{'title':" in rendered or "&#x27;title&#x27;" in rendered or "车站与城市入口" not in rendered or "上午从中央车站步行到 Sight-1" not in rendered:
            print("FAIL structured itinerary periods leaked as raw object text")
            return 2
        required = ("示例城结构测试", "01.01—01", "1 天", "城市初见", "Sight-1", "Sight-8", "城市购物", "商场与店铺", "温泉与泡汤体验", "日归温泉结构样卡一", "shop-brands", "Food-1", "menu-editorial", "menu-guide-grid", "menu-dictionary", "必备事项 0", "出发前准备说明", "确认事项 0", "出发前确认说明", "关键词场景 0", "当地贴士 0", "英语备用", "示例城结构测试 · 2026", "把这次示例城结构测试旅行", "mobile-section-fold experience-category")
        missing = [token for token in required if token not in rendered]
        if missing:
            print("FAIL rendered fixture missing: " + ", ".join(missing))
            return 2
        if "visa-module" in rendered or "visa-materials" in rendered or "VISA & ENTRY" in rendered:
            print("FAIL removed visa module leaked into the rendered handbook")
            return 2
        route_source = rendered[rendered.find('id="route"'):rendered.find('id="sights"')]
        if "SHOPPING TODAY" in route_source or "shopping-today" in route_source:
            print("FAIL shopping guidance belongs in Trip Mode, not the main itinerary")
            return 2
        for token in ("photo-note-head", "photo-note-grid", "适合拍摄", "人物拍摄提示", "城市街景人像"):
            if token not in route_source:
                print("FAIL canonical text-led photography note missing: " + token)
                return 2
        sight_source = rendered[rendered.find('id="sights"'):rendered.find('id="shops"')]
        if "Tabelog" in sight_source or sight_source.count('aria-hidden="true">★') != 8 or sight_source.count("<small>约 ") != 8:
            print("FAIL sight ratings must use the compact Google-only canonical stack")
            return 2
        food_source = rendered[rendered.find('id="food"'):rendered.find('id="booking"')]
        if "当地小吃推荐" not in food_source or food_source.count('class="snack-card"') != 4:
            print("FAIL local snacks must render as a dedicated food family")
            return 2
        if food_source.count("<b>Google ") != 12 or "Tabelog" in food_source or food_source.count("<small>约 ") < 12:
            print("FAIL Standard-mode restaurant cards need Google-only scores with subordinate review counts")
            return 2
        dedicated_source = food_source[food_source.find("值得专程去"):food_source.find("本地连锁安心选")]
        if dedicated_source.count('<article class="restaurant"') != 8:
            print("FAIL dedicated-trip food family must render eight restaurant cards")
            return 2
        if food_source.count("Tabelog 3.3") >= 6 or food_source.count("约 120 条") >= 6:
            print("FAIL fixture ratings repeat suspicious production-looking Tabelog values")
            return 2
        interface_css = (workbench / "better-interface.css").read_text(encoding="utf-8")
        for selector in (".shop-row .shop-brands", ".movement-card .movement-visual", ".restaurant-rating>span small", ".vocab-items small"):
            if selector not in interface_css:
                print("FAIL canonical responsive visual rule missing: " + selector)
                return 2
        theme_css = (workbench / "theme-switcher.css").read_text(encoding="utf-8")
        if "#booking .packing-checklist,#booking .booking-checklist" not in theme_css or "grid-template-columns:repeat(2,minmax(0,1fr))" not in theme_css:
            print("FAIL both preparation checklist families must render in two columns")
            return 2
        if re.search(r"data-handbook-theme[^\n{]*\.trip-", theme_css):
            print("FAIL handbook theme overrides Trip Mode's fixed high-contrast field palette")
            return 2
        runtime_text = "\n".join((workbench / name).read_text(encoding="utf-8") for name in ("handbook-enhancements.js", "itinerary-customizer.js", "trip-mode.js", "better-interface.css"))
        if 'pending ? "住宿待确认" : "住宿与出行位置"' not in runtime_text:
            print("FAIL pending stay summary must be state-aware")
            return 2
        trip_runtime = (workbench / "trip-mode.js").read_text(encoding="utf-8")
        if "只安排路线附近的商店" not in trip_runtime or "海岛行程" in trip_runtime or "SHOP_PLAN" in trip_runtime:
            print("FAIL Trip Mode shopping did not use destination-day data or retained island copy")
            return 2
        if "小红书找人像样片" in trip_runtime or "trip-stop-xhs" not in trip_runtime:
            print("FAIL generic portrait XHS action must be removed while exact-place stop actions remain")
            return 2
        for token in ("trip-day-map", "trip-time-guard", "travel-handbook-trip-companion-v2", "data-trip-provider", "shooting_plan", "trip-mode-dock"):
            if token not in trip_runtime:
                print("FAIL Trip Mode v2 runtime missing: " + token)
                return 2
        trip_css = (workbench / "trip-mode.css").read_text(encoding="utf-8")
        for token in ("#164f43", "#0a362f", "#f1b388", "#d4e3de", "#f8f4eb"):
            if token not in trip_css:
                print("FAIL Trip Mode demo palette token missing: " + token)
                return 2
        if "transport-decision-summary" in (scripts / "build_render_bindings.py").read_text(encoding="utf-8"):
            print("FAIL handbook transport must not append the commercial decision prose block")
            return 2
        forbidden = ("BALI · 2026", "BALI 2026", "九月的巴厘岛", "瑜伽、健身、舞蹈与 SPA", "乌布市中心", "佩尼达西线", "巴厘岛攻略修改申请")
        residue = [token for token in forbidden if token in rendered or token in runtime_text]
        if residue:
            print("FAIL rendered fixture retained destination reference UI: " + ", ".join(residue))
            return 2

        no_rating = copy.deepcopy(profile)
        no_rating["render_bindings_file"] = "no-rating-bindings.json"
        for record in no_rating["places"]:
            record.pop("rating", None)
            record.pop("review_count", None)
            record.pop("rating_source", None)
            record.pop("ratings", None)
        no_rating_path = root / "no-rating-profile.json"
        no_rating_bindings = root / "no-rating-bindings.json"
        no_rating_workbench = root / "no-rating-workbench"
        no_rating_path.write_text(json.dumps(no_rating, ensure_ascii=False), encoding="utf-8")
        no_rating_commands = [
            [sys.executable, str(scripts / "validate_destination_data.py"), str(no_rating_path), "--allow-test-fixture"],
            [sys.executable, str(scripts / "install_ui_system.py"), str(no_rating_workbench), "--system", "canonical"],
            [sys.executable, str(scripts / "build_render_bindings.py"), str(no_rating_path), str(no_rating_bindings)],
            [sys.executable, str(scripts / "render_destination.py"), str(no_rating_path), str(no_rating_workbench)],
        ]
        for command in no_rating_commands:
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            if result.returncode:
                print("FAIL no-rating regression: " + result.stdout + result.stderr)
                return result.returncode
        no_rating_html = (no_rating_workbench / "index.html").read_text(encoding="utf-8")
        if "评分暂不展示" in no_rating_html or "未取得可核实数据" in no_rating_html or 'aria-hidden="true">★' in no_rating_html:
            print("FAIL missing optional ratings must leave no placeholder or empty score UI")
            return 2
        if "Sight-8" not in no_rating_html or "Food-12" not in no_rating_html or "Google Maps 导航" not in no_rating_html:
            print("FAIL no-rating guide lost required place cards or map actions")
            return 2
        print("PASS destination profile generated bindings and rendered all registered product families")
        if args.output:
            print(f"OUTPUT {workbench}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
