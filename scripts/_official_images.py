"""Extract candidate HTML images; identity hints never constitute visual verification."""
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin, urlsplit

# Match UI filename tokens, not venue/product words such as Navigation Museum.
UI_FILENAME = re.compile(r'(?:^|[/_.-])(?:snav|gnavi|globalnavi|nav|navi|icon|btn|button|spacer|loading|sprite|favicon|ttl|title)(?:\d*|[_-][^/]*)?(?:\.|/|$)', re.I)

def is_ui_image(url):
    return bool(UI_FILENAME.search(urlsplit(url).path))


class ImageHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []
        self.links = []
        self.anchor = None
        self.jsonld = None
        self.jsonld_blocks = []
        self.picture = None

    def handle_starttag(self, tag, attrs):
        a = {key: value for key, value in attrs if value is not None}
        if tag == "picture":
            self.picture = {"context": ""}
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self.jsonld = []
        if tag == "a":
            self.anchor = {"href": a.get("href", ""), "text": a.get("title", "")}
            self.links.append(self.anchor)
        if tag in {"img", "source"}:
            context = " ".join(a.get(key, "") for key in ("alt", "title", "aria-label"))
            if self.picture is not None and context.strip():
                self.picture["context"] = context
            for key in ("data-src", "data-original", "data-lazy-src", "data-lazy", "src"):
                if a.get(key):
                    self.images.append({"raw_url": a[key], "metadata_key": f"body:{key}", "context": context, "anchor": self.anchor, "picture": self.picture})
            for key in ("srcset", "data-srcset", "data-lazy-srcset"):
                options = []
                for option in a.get(key, "").split(","):
                    parts = option.strip().split()
                    if not parts:
                        continue
                    try:
                        weight = float(parts[-1].rstrip("wx")) if len(parts) > 1 else 1
                    except ValueError:
                        weight = 1
                    options.append((weight, parts[0]))
                if options:
                    self.images.append({"raw_url": max(options)[1], "metadata_key": f"body:{key}", "context": context, "anchor": self.anchor, "picture": self.picture})
        if a.get("style"):
            for url in re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", a["style"], re.I):
                self.images.append({"raw_url": url.strip(), "metadata_key": "inline_css_background", "context": " ".join(a.get(key, "") for key in ("aria-label", "title", "data-product-name")), "anchor": self.anchor})

    def handle_endtag(self, tag):
        if tag == "picture":
            self.picture = None
        if tag == "a":
            self.anchor = None
        if tag == "script" and self.jsonld is not None:
            self.jsonld_blocks.append("".join(self.jsonld))
            self.jsonld = None

    def handle_data(self, data):
        if self.jsonld is not None:
            self.jsonld.append(data)
        elif self.anchor is not None:
            self.anchor["text"] += data


def jsonld_images(value):
    if isinstance(value, list):
        for item in value:
            yield from jsonld_images(item)
    elif isinstance(value, dict):
        if "image" in value:
            images = value["image"] if isinstance(value["image"], list) else [value["image"]]
            for image in images:
                url = image if isinstance(image, str) else image.get("url") or image.get("contentUrl") if isinstance(image, dict) else None
                if url:
                    yield {"raw_url": url, "metadata_key": "jsonld:image", "context": str(value.get("name", "")), "jsonld_type": value.get("@type")}
        for key, child in value.items():
            if key != "image":
                yield from jsonld_images(child)


def extract_images(text, base):
    parser = ImageHTML()
    parser.feed(text)
    images = parser.images
    for raw in parser.jsonld_blocks:
        try:
            images.extend(jsonld_images(json.loads(raw)))
        except (ValueError, TypeError):
            pass
    unique = {}
    for image in images:
        url = urljoin(base, image.pop("raw_url"))
        if urlsplit(url).scheme != "https":
            continue
        anchor = image.pop("anchor", None)
        picture = image.pop("picture", None)
        if picture:
            image["context"] = (image.get("context", "") + " " + picture["context"]).strip()
        if anchor:
            image["context"] = (image["context"] + " " + anchor["text"]).strip()
        existing = unique.get(url)
        image = {"url": url, **image, "status": "candidate", "subject_verified": False}
        if existing is None or len(image.get("context", "")) > len(existing.get("context", "")):
            unique[url] = image
    return list(unique.values()), [{"url": urljoin(base, link["href"]), "text": link["text"].strip()} for link in parser.links if link["href"]]


def matching(term, text):
    normalize = lambda value: re.sub(r"[\s\W_]+", "", str(value).casefold())
    wanted = normalize(term)
    return len(wanted) >= 2 and wanted in normalize(text)
