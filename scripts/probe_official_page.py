#!/usr/bin/env python3
"""Fetch HTML metadata using only Python's standard library; no shell one-liners."""
import argparse
import codecs
from datetime import datetime, timezone
from email.message import Message
from html.parser import HTMLParser
from _network_policy import address_allowed
import json
from pathlib import Path
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from _official_images import extract_images, matching

MAX_BYTES = 1_500_000


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.title_parts = []
        self.in_title = False
        self.charset = None
        self.base = None

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): v for k, v in attrs if v is not None}
        if tag == "title":
            self.in_title = True
        if tag == "base" and self.base is None:
            self.base = attrs.get("href")
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key and attrs.get("content"):
                self.meta.setdefault(key, []).append(attrs["content"])
            if attrs.get("charset"):
                self.charset = attrs["charset"]
            elif attrs.get("http-equiv", "").lower() == "content-type":
                header = Message()
                header["content-type"] = attrs.get("content", "")
                self.charset = header.get_content_charset() or self.charset

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)


def validate_url(url, resolve=True):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("URL must use public HTTPS")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("URL must not contain credentials or a nonstandard port")
    if any(ord(char) < 32 for char in url):
        raise ValueError("URL contains control characters")
    if resolve:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        ips = [row[4][0] for row in addresses]
        if not ips or any(not address_allowed(ip, parsed.hostname) for ip in ips):
            raise ValueError("URL resolves to a non-public address")
    return url


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def decode_html(payload, content_type):
    hint = Metadata()
    hint.feed(payload[:8192].decode("latin-1"))
    header = Message()
    header["content-type"] = content_type
    encoding = "utf-8-sig" if payload.startswith(codecs.BOM_UTF8) else "utf-16" if payload.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else header.get_content_charset() or hint.charset or "utf-8"
    warning = None
    try:
        text = payload.decode(encoding)
    except (LookupError, UnicodeError):
        text = payload.decode("utf-8", errors="replace")
        warning = f"Could not decode declared encoding {encoding}; UTF-8 replacement used"
        encoding = "utf-8-replacement"
    return text, encoding, warning


def parse_metadata(payload, page_url, content_type="text/html", product_name=None):
    text, encoding, warning = decode_html(payload, content_type)
    parsed = Metadata()
    parsed.feed(text)
    first = lambda key: next(iter(parsed.meta.get(key, [])), None)
    images = []
    base = urllib.parse.urljoin(page_url, parsed.base or "")
    for key in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"):
        for raw in parsed.meta.get(key, []):
            url = urllib.parse.urljoin(base, raw.strip())
            try:
                validate_url(url, resolve=False)
            except ValueError:
                continue
            if url not in [image["url"] for image in images]:
                images.append({"url": url, "metadata_key": key, "context": first("og:image:alt") or "", "status": "candidate", "subject_verified": False})
    body_images, links = extract_images(text, base)
    for image in body_images:
        if image["url"] not in [row["url"] for row in images]:
            images.append(image)
    page_title = first("og:title") or " ".join(parsed.title_parts).strip()
    priority_names = [name for name in (product_name, page_title.split("|")[0].strip()) if name]
    images.sort(key=lambda image: any(matching(name, image.get("context", "")) for name in priority_names), reverse=True)
    return {"status": "ok" if images else "no_image", "title": first("og:title") or " ".join(parsed.title_parts).strip(), "description": first("og:description") or first("description"), "images": images[:24], "product_links": [link for link in links if product_name and matching(product_name, link["text"]) and urllib.parse.urlsplit(link["url"]).hostname == urllib.parse.urlsplit(page_url).hostname][:2], "encoding": encoding, "encoding_warning": warning, "official_identity_verified": False}


def probe(url, timeout=10, product_name=None):
    result = {"requested_url": url, "checked_at": datetime.now(timezone.utc).isoformat(), "images": []}
    try:
        validate_url(url)
        opener = urllib.request.build_opener(PublicRedirect())
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 travel-handbook-metadata/1.0", "Accept": "text/html,application/xhtml+xml"})
        with opener.open(request, timeout=timeout) as response:
            result["final_url"] = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            result["content_type"] = content_type
            if content_type.split(";", 1)[0].strip().lower() not in {"text/html", "application/xhtml+xml", ""}:
                return {**result, "status": "not_html", "error": "Response is not an HTML page"}
            payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            return {**result, "status": "too_large", "error": "HTML exceeds 1.5 MB limit"}
        return {**result, **parse_metadata(payload, result["final_url"], content_type, product_name)}
    except urllib.error.HTTPError as error:
        return {**result, "status": "http_error", "http_status": error.code, "error": str(error)}
    except (TimeoutError, socket.timeout) as error:
        return {**result, "status": "timeout", "error": str(error) or "Request timed out"}
    except urllib.error.URLError as error:
        return {**result, "status": "timeout" if isinstance(error.reason, TimeoutError) else "network_error", "error": str(error.reason)}
    except ValueError as error:
        return {**result, "status": "invalid_url", "error": str(error)}
    except OSError as error:
        return {**result, "status": "network_error", "error": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--product-name", help="Prioritize body/JSON-LD images and same-site links carrying this exact product name")
    parser.add_argument("--timeout", type=float, default=10, help="Per-request socket timeout, 1-30 seconds; no automatic retries")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 30:
        parser.error("--timeout must be between 1 and 30 seconds")
    result = probe(args.url, args.timeout, args.product_name)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
        except OSError as error:
            parser.exit(2, f"METADATA OUTPUT FAILED: {error}\n")
        print(json.dumps({"output_file": str(args.output.resolve()), **result}, ensure_ascii=False, indent=2))
    else:
        print(encoded)
    return 0 if result["status"] in {"ok", "no_image"} else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
