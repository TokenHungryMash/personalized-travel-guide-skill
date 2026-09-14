#!/usr/bin/env python3
"""Early, local research-pack contract check with conservative syntax repair."""
from __future__ import annotations
import argparse, json, re, sys, math
from _content_integrity import content_failures
from _outfit_advice import outfit_errors
from pathlib import Path

CONTRACT_PATH = Path(__file__).resolve().parent.parent / "assets" / "research-pack-contract.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

PACKS = {
    "framing": (dict, ("destination","display_name","country","trip","cover","transport","stays","render_bindings_file")),
    "itinerary": (list, ()), "places-core": (dict, ("sights","support")),
    "places-shopping": (dict, ("shops","souvenirs")), "places-experiences": (list, ()),
    "places-food": (list, ()), "modules-discovery": (dict, ("shopping","experiences")),
    "modules-practical": (dict, ("food","preparation")),
    "modules-language-notes": (dict, ("language","travel_notes")),
}

def pointer(parts):
    return "/" + "/".join(str(p).replace("~","~0").replace("/","~1") for p in parts)

def safe_text_repair(text):
    value = text.lstrip("\ufeff").strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, re.I | re.S)
    if fence: value = fence.group(1)
    return re.sub(r",\s*([}\]])", r"\1", value)

def required(obj, fields, base=()):
    errors=[]
    for field in fields:
        if field not in obj or obj[field] in (None,"",[],{}):
            errors.append({"pointer":pointer((*base,field)),"code":"required","message":"missing or empty required field"})
    return errors

def present(obj, fields, base=()):
    return [{"pointer":pointer((*base,field)),"code":"required","message":"missing required field"}
            for field in fields if field not in obj]

def required_paths(obj, paths, base=()):
    errors=[]
    for raw in paths:
        value=obj; parts=raw.split("."); missing=False
        for part in parts:
            if not isinstance(value,dict) or part not in value:
                missing=True; break
            value=value[part]
        if missing or value in (None, "", {}):
            errors.append({"pointer":pointer((*base,*parts)),"code":"required","message":"missing required contract path"})
    return errors

def validate(pack_id, data):
    errors=[]; expected, fields = PACKS.get(pack_id, (None,()))
    if expected and not isinstance(data, expected):
        return [{"pointer":"/","code":"container_type","message":f"expected {expected.__name__}, got {type(data).__name__}"}]
    if isinstance(data, dict):
        errors += required(data, tuple(field for field in fields if not (pack_id == 'places-core' and field == 'support')))
        if pack_id == 'places-core':
            if not isinstance(data.get('support'), list):
                errors.append({'pointer':'/support','code':'container_type','message':'expected support array; empty is valid when transport and stay are pending'})
    if pack_id == "framing" and isinstance(data,dict):
        errors += required_paths(data, CONTRACT["packs"]["framing"]["required_paths"])
        trip=data.get("trip"); cover=data.get("cover"); transport=data.get("transport")
        if isinstance(trip,dict): errors += present(trip,("start_date","end_date","days","rhythm","travelers","interests","constraints"),("trip",))
        if isinstance(cover,dict): errors += required(cover,("kicker","title","summary","image","tags"),("cover",))
        if isinstance(cover,dict) and not isinstance(cover.get("image"),str):
            errors.append({"pointer":"/cover/image","code":"display_type","message":"expected file path string; keep download_url and source_page beside image"})
        if isinstance(transport,dict): errors += present(transport,("status","legs"),("transport",))
        if not isinstance(data.get("stays"),list) or not data.get("stays"):
            errors.append({"pointer":"/stays","code":"count","message":"expected at least one stay status record"})
    if pack_id == "itinerary" and isinstance(data, list):
        for i, day in enumerate(data):
            if not isinstance(day, dict): errors.append({"pointer":pointer((i,)),"code":"item_type","message":"day must be object"}); continue
            errors += required(day, ("date","theme","summary","periods","stops"),(i,))
            errors += required_paths(day, CONTRACT["packs"]["itinerary"]["item_required_paths"], (i,))
            advice = day.get('shopping_advice')
            errors += outfit_errors(day.get('photo_advice'), pointer((i,'photo_advice')))
            if isinstance(advice,dict):
                errors += required(advice,('title','description'),(i,'shopping_advice'))
            periods=day.get("periods")
            if isinstance(periods,dict): errors += required(periods,("morning","afternoon","evening"),(i,"periods"))
    if pack_id == "itinerary" and isinstance(data, list):
        errors += [{"pointer":"/stops", "code":"timeline", "message":message} for message in content_failures({"itinerary":data})]
    if pack_id.startswith("places-"):
        families = data.items() if isinstance(data,dict) else [(None,data)]
        for family_name, family in families:
            if not isinstance(family,list): continue
            for i, place in enumerate(family):
                if not isinstance(place,dict): continue
                base = (i,) if family_name is None else (family_name,i)
                errors += required(place,("id","type","display_name","map_query","source_url"),base)
                for image_index, image in enumerate(place.get('images', []) if isinstance(place.get('images'), list) else []):
                    if isinstance(image, dict) and image.get('source_type') in {'unresolved', 'placeholder'}:
                        errors.append({'pointer':pointer((*base,'images',image_index)), 'code':'image_unresolved', 'message':'image source is unresolved; complete the exact official/listing source or allowed brand artwork before marking this pack complete'})
                expected_type = {'sights':'sight','shops':'shop','souvenirs':'souvenir'}.get(family_name) or {'places-food':'restaurant','places-experiences':'experience'}.get(pack_id)
                if expected_type and place.get('type') != expected_type:
                    errors.append({'pointer':pointer((*base,'type')), 'code':'enum', 'message':f'this pack family requires type={expected_type}; use subtype for semantic categories'})
                if place.get('type') == 'souvenir':
                    errors += required(place, ('why_buy','best_for','where_to_buy','buying_tip'), base)
                if place.get("type") != "souvenir":
                    for field, limit in (("latitude", 85), ("longitude", 180)):
                        value = place.get(field)
                        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > limit:
                            errors.append({"pointer":pointer((*base,field)),"code":"coordinates","message":"supply numeric verified exact-place coordinates before pack completion; confirm branch on map, never use a city centroid"})
                if place.get("type") == "sight":
                    errors += required(place, ("duration_minutes", "scheduled_label"), base)
                if place.get("type") in {"sight", "shop", "experience"}:
                    errors += required(place, ("hours", "closed_days"), base)
                if place.get("type") == "shop":
                    errors += present(place, ("closed_days",), base)
                    errors += required(place, ("category", "buying_tip", "brand_highlights", "scheduled_label"), base)
                if place.get("type") in {"sight", "restaurant"} and len(str(place.get("description", "")).strip()) < 45:
                    errors.append({"pointer":pointer((*base,"description")),"code":"content","message":"expected useful description of at least 45 characters, matching final validation"})
                if place.get("type") == "experience" and len(str(place.get("description", "")).strip()) < 60:
                    errors.append({"pointer":pointer((*base,"description")),"code":"content","message":"expected at least 60 characters covering the activity, local relevance and traveler fit, matching final validation"})
                if place.get("type") == "restaurant" and not isinstance(place.get("signature_dishes"), str):
                    errors.append({"pointer":pointer((*base,"signature_dishes")),"code":"display_type","message":"signature_dishes must be researched text, not an array"})
                for field in ("closed_days", "brand_highlights"):
                    value = place.get(field)
                    if value is not None and not (isinstance(value,str) or isinstance(value,list) and all(isinstance(x,str) for x in value)):
                        errors.append({"pointer":pointer((*base,field)),"code":"display_type","message":"expected text or a list of text"})
    if pack_id == "modules-discovery" and isinstance(data,dict):
        for key in ("shopping","experiences"):
            if key in data and not isinstance(data[key],list): errors.append({"pointer":pointer((key,)),"code":"container_type","message":"expected array of groups"})
        experiences=data.get("experiences")
        if isinstance(experiences,list):
            option_count=sum(len(group.get("items",[])) for group in experiences if isinstance(group,dict))
            experience_mode=str(data.get("experience_mode","standard")).lower()
            if experience_mode=="standard" and (len(experiences)!=3 or option_count!=6): errors.append({"pointer":"/experiences","code":"count","message":f"Standard mode expects exactly 3 groups and 6 options, got {len(experiences)} groups and {option_count} options"})
            if experience_mode=="constrained" and (len(experiences)!=2 or option_count!=4): errors.append({"pointer":"/experiences","code":"count","message":f"Constrained mode expects exactly 2 groups and 4 options, got {len(experiences)} groups and {option_count} options"})
            if experience_mode=="expanded" and (len(experiences)<3 or option_count<6): errors.append({"pointer":"/experiences","code":"count","message":f"Expanded mode expects at least 3 groups and 6 options, got {len(experiences)} groups and {option_count} options"})
    if pack_id == "modules-practical" and isinstance(data,dict):
        prep = data.get("preparation", {})
        if isinstance(prep, dict):
            for family in ("essentials", "confirm_ahead"):
                items = prep.get(family)
                if not isinstance(items, list) or not items:
                    errors.append({"pointer":pointer(("preparation",family)),"code":"count","message":"checklist family must be a nonempty array"})
                for i, item in enumerate(items if isinstance(items,list) else []):
                    base = ('preparation',family,i)
                    if not isinstance(item,dict):
                        errors.append({'pointer':pointer(base),'code':'container_type','message':'expected checklist object'})
                        continue
                    if not (item.get('item') or item.get('title')) or not (item.get('detail') or item.get('note')):
                        errors.append({'pointer':pointer(base),'code':'content','message':'checklist needs title/item and note/detail'})
                    if item.get('priority') not in {'必须','建议','随缘'}:
                        errors.append({'pointer':pointer((*base,'priority')),'code':'enum','message':'use 必须, 建议 or 随缘'})
            if sum(len(prep.get(k,[])) for k in ("essentials","confirm_ahead") if isinstance(prep.get(k),list)) < 24:
                errors.append({"pointer":"/preparation","code":"count","message":"expected at least 24 preparation items across both families"})
        for key in ("food","preparation"):
            if key in data and not isinstance(data[key],dict): errors.append({"pointer":pointer((key,)),"code":"container_type","message":"expected object"})
        food=data.get("food")
        if isinstance(food,dict):
            errors += required(food,("menu_guide","menu_primer","local_snacks","dedicated_trip","reliable_chains"),("food",))
            for i, item in enumerate(food.get("menu_primer", []) if isinstance(food.get("menu_primer"), list) else []):
                base = ("food", "menu_primer", i)
                if not isinstance(item, dict):
                    errors.append({"pointer":pointer(base),"code":"container_type","message":"expected object with term, meaning, note; not a string"})
                else:
                    errors += required(item, ("term", "meaning", "note"), base)
            snacks = food.get("local_snacks")
            if not isinstance(snacks, list) or len(snacks) != 4:
                errors.append({"pointer":"/food/local_snacks","code":"count","message":"expected exactly four snacks"})
            for i, snack in enumerate(snacks if isinstance(snacks, list) else []):
                if not isinstance(snack, dict):
                    errors.append({"pointer":pointer(("food","local_snacks",i)),"code":"container_type","message":"expected snack object"})
                else:
                    errors += required(snack, ("name","local_name","description","why_try","where_to_find"), ("food","local_snacks",i))
            dedicated = food.get('dedicated_trip')
            reliable = food.get('reliable_chains')
            if not isinstance(dedicated, list) or len(dedicated) < 6:
                errors.append({'pointer':'/food/dedicated_trip','code':'count','message':'expected at least 6 dedicated-trip restaurant references'})
            if not isinstance(reliable, list) or not 2 <= len(reliable) <= 4:
                errors.append({'pointer':'/food/reliable_chains','code':'count','message':'expected 2 to 4 reliable-chain restaurant references; use 4 by default'})
            for family_name, items in (('dedicated_trip', dedicated), ('reliable_chains', reliable)):
                for i, item in enumerate(items if isinstance(items, list) else []):
                    if not isinstance(item, dict) or not str(item.get('place_id', '')).strip():
                        errors.append({'pointer':pointer(('food',family_name,i,'place_id')),'code':'required','message':'restaurant references must be wrapped as {"place_id":"stable-id"}'})
            guide=food.get("menu_guide")
            if isinstance(guide,dict):
                errors += required(guide,("kicker","title","intro","cards"),("food","menu_guide"))
                cards=guide.get("cards")
                if isinstance(cards,list) and len(cards)<4: errors.append({"pointer":"/food/menu_guide/cards","code":"count","message":f"expected at least 4 cards, got {len(cards)}"})
                for i, card in enumerate(cards if isinstance(cards,list) else []):
                    base=('food','menu_guide','cards',i)
                    if not isinstance(card,dict):
                        errors.append({'pointer':pointer(base),'code':'container_type','message':'expected card object'})
                    elif not card.get('title') or len(str(card.get('note','')).strip()) < 30:
                        errors.append({'pointer':pointer(base),'code':'content','message':'menu card requires title and note of at least 30 characters; description is not the rendering field'})
    if pack_id == "modules-language-notes" and isinstance(data,dict):
        language=data.get("language")
        if isinstance(language,dict):
            for family_name in ("keyword_groups","phrase_groups","english_keyword_groups","english_phrase_groups"):
                for i,group in enumerate(language.get(family_name,[]) if isinstance(language.get(family_name,[]),list) else []):
                    if isinstance(group,dict) and not re.search(r"[\u3400-\u9fff]",str(group.get("title",""))):
                        errors.append({"pointer":pointer(("language",family_name,i,"title")),"code":"language","message":"group title must be Chinese; bilingual text belongs inside cards"})
            for family_name in ('keyword_groups','phrase_groups','english_keyword_groups','english_phrase_groups'):
                field = 'sentence' if family_name == 'english_phrase_groups' else 'term'
                for i, group in enumerate(language.get(family_name, []) if isinstance(language.get(family_name), list) else []):
                    for j, item in enumerate(group.get('items', []) if isinstance(group, dict) else []):
                        base = ('language',family_name,i,'items',j)
                        if not isinstance(item,dict):
                            errors.append({'pointer':pointer(base),'code':'container_type','message':'language item must be an object'})
                            continue
                        errors += required(item,(field,'meaning'),base)
                        if 'roman' in item and not item.get('reading'):
                            errors.append({'pointer':pointer((*base,'reading')),'code':'field_name','message':'use reading, not roman, for pronunciation'})
                        if not family_name.startswith('english_') and re.search(r'[\u3040-\u30ff]',str(item.get(field,''))):
                            errors += required(item,('reading',),base)
        notes=data.get("travel_notes")
        if not isinstance(notes,list):
            errors.append({"pointer":"/travel_notes","code":"container_type","message":"expected array of five groups, not an object wrapping groups"})
        if isinstance(notes,list) and len(notes)!=5: errors.append({"pointer":"/travel_notes","code":"count","message":f"expected exactly 5 groups, got {len(notes)}"})
        for i, group in enumerate(notes if isinstance(notes,list) else []):
            if isinstance(group,dict) and group.get("category") not in {"climate","etiquette","transport","safety","payment"}:
                errors.append({"pointer":pointer(("travel_notes",i,"category")),"code":"enum","message":"use climate, etiquette, transport, safety or payment"})
            items=group.get("items") if isinstance(group,dict) else None
            if isinstance(items,list) and len(items)!=4: errors.append({"pointer":pointer(("travel_notes",i,"items")),"code":"count","message":f"expected exactly 4 topics, got {len(items)}"})
            for j, item in enumerate(items if isinstance(items,list) else []):
                if not isinstance(item,dict) or item.get('priority') not in ('必须','建议','随缘'):
                    errors.append({"pointer":pointer(("travel_notes",i,"items",j,"priority")),"code":"enum","message":"explicit priority required: 必须, 建议 or 随缘; never infer from title"})
                title = item.get("title") if isinstance(item,dict) else None
                if not isinstance(title,str) or not title.strip() or re.search(r"[，,、：:]$", title.strip()):
                    errors.append({"pointer":pointer(("travel_notes",i,"items",j,"title")),"code":"title","message":"expected a complete nonempty topic title; dangling punctuation is invalid"})
                note = str(item.get("note", "")) if isinstance(item, dict) else ""
                if len(note.strip()) < 34 or len(re.findall(r"[。！？!?]", note)) < 2:
                    errors.append({"pointer":pointer(("travel_notes",i,"items",j,"note")),"code":"content","message":"write two compact practical sentences, at least 34 characters"})
    return errors

def scaffold(pack_id):
    place = {"id": None, "type": None, "display_name": None, "local_name": None, "english_name": None, "map_query": None, "source_url": None, "description": None, "hours": None, "closed_days": [], "latitude": None, "longitude": None, "images": []}
    shapes = {
        "framing": {"destination": None, "display_name": None, "country": None, "year": None, "trip": {"start_date": None, "end_date": None, "days": None, "rhythm": None, "travelers": None, "interests": [], "constraints": []}, "cover": {"kicker": None, "title": None, "summary": None, "image": None, "tags": []}, "transport": {"status": "pending", "legs": []}, "stays": [{"status": "pending", "place_id": None, "check_in": None, "check_out": None, "notes": None}], "render_bindings_file": "render-bindings.json"},
        "itinerary": [{"date": None, "theme": None, "summary": None, "periods": {"morning": {"title": None, "description": None}, "afternoon": {"title": None, "description": None}, "evening": {"title": None, "description": None}}, "stops": [{"place_id": None, "arrival_time": None, "dwell_minutes": None, "transport_mode": None, "transfer_minutes": None, "distance_km": None, "estimated_cost": None, "practical_note": None, "time_guard": None}], "shopping_advice": {"title": None, "description": None}, "photo_advice": {"title": None, "lighting": None, "suitable_shots": [], "portrait_tip": None, "shooting_plan": [], "outfit_advice": {"women": None, "men": None, "practical_note": None}}}],
        "places-core": {"sights": [{**place, "type": "sight", "duration_minutes": None, "scheduled_label": None}], "support": []},
        "places-shopping": {"shops": [{**place, "type": "shop", "category": None, "buying_tip": None, "brand_highlights": [], "scheduled_label": None}], "souvenirs": [{**place, "type": "souvenir", "why_buy": None, "best_for": None, "where_to_buy": None, "buying_tip": None}]},
        "places-experiences": [{**place, "type": "experience", "experience_type": None, "category": None, "scheduled_label": None, "hazardous": False}],
        "places-food": [{**place, "type": "restaurant", "cuisine": None, "signature_dishes": None, "price_per_person": None}],
        "modules-discovery": {"experience_mode": "standard", "shopping": [{"title": None, "subtitle": None, "items": [{"place_id": None}]}], "experiences": [{"title": None, "items": [{"place_id": None}]}]},
        "modules-practical": {"food": {"menu_guide": {"kicker": None, "title": None, "intro": None, "cards": [{"title": None, "note": None}, {"title": None, "note": None}, {"title": None, "note": None}, {"title": None, "note": None}]}, "menu_primer": [{"term": None, "meaning": None, "note": None}], "local_snacks": [{"name": None, "local_name": None, "english_name": None, "description": None, "why_try": None, "where_to_find": None}], "dedicated_trip": [{"place_id": None}], "reliable_chains": [{"place_id": None}]}, "preparation": {"essentials": [{"title": None, "note": None, "priority": None}], "confirm_ahead": [{"title": None, "note": None, "priority": None}]}},
        "modules-language-notes": {"language": {"keyword_groups": [], "phrase_groups": [], "english_keyword_groups": [], "english_phrase_groups": []}, "travel_notes": []},
    }
    shapes["modules-practical"]["food"]["menu_primer"] = [{"term": None, "meaning": None, "note": None}]
    shapes['modules-practical']['food']['menu_guide']['cards'] = [{'title':None,'note':None} for _ in range(4)]
    snack = {"name": None, "local_name": None, "english_name": None, "description": None, "why_try": None, "where_to_find": None}
    shapes['modules-practical']['food']['local_snacks'] = [dict(snack) for _ in range(4)]
    shapes['modules-practical']['food']['dedicated_trip'] = [{'place_id':None} for _ in range(6)]
    shapes['modules-practical']['food']['reliable_chains'] = [{'place_id':None} for _ in range(4)]
    for family in ('essentials','confirm_ahead'):
        shapes['modules-practical']['preparation'][family] = [{'title':None,'note':None,'priority':None} for _ in range(12)]
    for family in ('keyword_groups','phrase_groups','english_keyword_groups','english_phrase_groups'):
        field = 'sentence' if family == 'english_phrase_groups' else 'term'
        entry = {field:None, 'meaning':None}
        if not family.startswith('english_'): entry['reading'] = None
        shapes['modules-language-notes']['language'][family] = [{'title':None,'items':[dict(entry) for _ in range(5)]} for _ in range(5)]
    shapes["modules-language-notes"]["travel_notes"] = [
        {"category": category, "title": title, "items": [{"title": None, "note": None, "priority": None} for _ in range(4)]}
        for category, title in (("climate", "天气与穿着"), ("etiquette", "文化与礼仪"), ("transport", "当地交通"), ("safety", "安全与应急"), ("payment", "支付与现金"))
    ]
    return shapes[pack_id]

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("pack_id", nargs="?", choices=sorted(PACKS)); p.add_argument("path",nargs="?",type=Path); p.add_argument("--scaffold",choices=sorted(PACKS)); p.add_argument("--output",type=Path); p.add_argument("--repair-safe",action="store_true"); p.add_argument("--errors",type=Path); args=p.parse_args()
    if args.scaffold:
        rendered=json.dumps(scaffold(args.scaffold),ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered,encoding="utf-8"); print(f"SCAFFOLD WROTE {args.scaffold}: {args.output}")
        else: print(rendered,end="")
        return 0
    if not args.pack_id or not args.path: p.error("pack_id and path are required unless --scaffold is used")
    try:
        raw=args.path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        code = "input_missing" if isinstance(error, FileNotFoundError) else "input_unreadable"
        report = {"pack_id": args.pack_id, "path": str(args.path), "errors": [{"pointer": "/", "code": code, "message": str(error)}]}
        if args.errors:
            args.errors.parent.mkdir(parents=True, exist_ok=True)
            args.errors.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(f"PACK INVALID {args.pack_id}: {code}: {args.path}; save the source JSON before validation")
        return 2
    try: data=json.loads(raw); repaired=False
    except json.JSONDecodeError as first:
        candidate=safe_text_repair(raw)
        try: data=json.loads(candidate)
        except json.JSONDecodeError:
            report={"pack_id":args.pack_id,"path":str(args.path),"errors":[{"pointer":"/","code":"json_syntax","message":str(first)}]}
            if args.errors: args.errors.parent.mkdir(parents=True,exist_ok=True); args.errors.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print(f"PACK INVALID {args.pack_id}: JSON syntax"); return 2
        repaired=True
        if args.repair_safe: args.path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    errors=validate(args.pack_id,data); report={"pack_id":args.pack_id,"path":str(args.path),"safe_syntax_repair_available":repaired and not args.repair_safe,"errors":errors}
    if args.errors: args.errors.parent.mkdir(parents=True,exist_ok=True); args.errors.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if errors: print(f"PACK INVALID {args.pack_id}: {len(errors)} errors; first={errors[0]['pointer']} {errors[0]['message']}"); return 2
    print(f"PACK VALID {args.pack_id}" + ("; safe syntax repaired" if repaired and args.repair_safe else "")); return 0

if __name__ == "__main__": sys.exit(main())
