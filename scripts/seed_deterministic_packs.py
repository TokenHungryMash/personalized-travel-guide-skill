#!/usr/bin/env python3
"""Seed reusable practical-content drafts without inventing destination facts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ESSENTIALS = [
    "护照与证件复印件", "银行卡与少量当地现金", "境外医疗与行程保险", "手机与充电器", "充电宝",
    "数据网络或 eSIM", "常用药与处方证明", "防晒用品", "雨具", "舒适步行鞋", "轻便外套", "替换衣物",
    "洗护与护肤用品", "化妆品与卸妆用品", "眼镜或隐形护理用品", "纸巾与湿巾", "水杯", "折叠购物袋",
]
CONFIRM = [
    "核对证件有效期与入境要求", "确认往返交通", "确认住宿订单", "预约热门餐厅", "预约限流景点或体验",
    "核对机场与车站名称", "保存离线地图和酒店地址", "确认支付与取现方案", "查看天气与行李额度", "向家人共享行程与紧急联系人",
]


def write_if_missing(path: Path, value: object) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbench", type=Path)
    args = parser.parse_args()
    root = args.workbench.resolve()
    brief = json.loads((root / "travel-brief.json").read_text(encoding="utf-8"))
    destination = brief["display_name"]
    country = str(brief.get("country", "")).lower()
    created = 0
    preparation = {
        "_draft": True,
        "_review_required": f"核对并补充 {destination} 的插头、现金、网络、天气和预约项目后，将 _draft 改为 false。",
        "essentials": [{"title": text, "note": "出发前逐项确认并按个人情况调整。"} for text in ESSENTIALS],
        "confirm_ahead": [{"title": text, "note": "确认后保存订单、凭证或离线截图。"} for text in CONFIRM],
    }
    language = {
        "_draft": True,
        "_review_required": f"为 {destination} 填入当地语言；保留五类结构并满足 25 词、25 句及读音要求后，将 _draft 改为 false。",
        "keyword_groups": [{"title": title, "items": []} for title in ("交通与定位", "餐厅与菜单", "购物与支付", "住宿与设施", "求助与紧急情况")],
        "phrase_groups": [{"title": title, "items": []} for title in ("问路与乘车", "点餐与忌口", "购物与退税", "住宿沟通", "求助与紧急情况")],
    }
    reference_root = Path(__file__).resolve().parent.parent / "references"
    template_path = reference_root / "language-local-templates.json"
    fallback_path = reference_root / "english-fallback-library.json"
    if template_path.exists():
        templates = json.loads(template_path.read_text(encoding="utf-8"))
        template_key = "japanese" if country in {"japan", "日本"} else ""
        if template_key and template_key in templates:
            language.update(templates[template_key])
            language["_review_required"] = f"已载入可复用语言模板；只需把交通、地名、菜名和礼仪表达核对并差异化为 {destination} 后，将 _draft 改为 false。"
    if fallback_path.exists():
        fallback = json.loads(fallback_path.read_text(encoding="utf-8"))
        language["english_keyword_groups"] = fallback["english_keyword_groups"]
        language["english_phrase_groups"] = fallback["english_phrase_groups"]
    notes = {
        "_draft": True,
        "_review_required": f"把主题改写为 {destination} 的具体规则、风险与生活习惯；保留五组且每组四项后将 _draft 改为 false。",
        "groups": [{"category": category, "title": title, "summary": "待补充目的地具体说明", "items": []} for category, title in (("climate", "天气与穿着"), ("etiquette", "文化与礼仪"), ("transport", "当地交通"), ("safety", "安全与应急"), ("payment", "支付与现金"))],
    }
    compact_plan = any(item.get("id") == "modules-language-notes" for item in json.loads((root / "research-plan.json").read_text(encoding="utf-8")).get("packs", []))
    if compact_plan:
        created += write_if_missing(root / "research/modules/practical.json", {"_draft": True, "food": {}, "preparation": preparation})
        created += write_if_missing(root / "research/modules/language-notes.json", {"_draft": True, "language": language, "travel_notes": notes["groups"]})
    else:
        created += write_if_missing(root / "research/modules/preparation.json", preparation)
        created += write_if_missing(root / "research/modules/language.json", language)
        created += write_if_missing(root / "research/modules/travel_notes.json", notes)
    print(f"PASS seeded {created} deterministic practical drafts; drafts remain pending until destination review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
