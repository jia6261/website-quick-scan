#!/usr/bin/env python3
"""Check sitemap pages and video resources referenced by those pages."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
import os
import sys

SITEMAP_URL = os.getenv("SITEMAP_URL", "https://trbo.jiagar.us.kg/sitemap.xml")
TIMEOUT = float(os.getenv("TIMEOUT", "15"))
WORKERS = int(os.getenv("WORKERS", "16"))
USER_AGENT = "website-quick-scan/1.1"
VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4v", ".m3u8", ".mpd")


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            quote(parts.path, safe="/%:@()[]!$&'*,;=~._-"),
            quote(parts.query, safe="=&/?%@:+()[]!$'*,;=~._-"),
            "",
        )
    )


def load_urls():
    request = Request(SITEMAP_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT) as response:
        root = ET.fromstring(response.read())
    urls = [element.text.strip() for element in root.iter() if element.tag.endswith("loc") and element.text]
    if not urls:
        raise RuntimeError("sitemap contains no URLs")
    return urls


class VideoParser(HTMLParser):
    """Find video resources declared in HTML video/source tags and video links."""

    def __init__(self, page_url):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        values = []
        if tag.lower() in {"video", "source"}:
            values += [attributes.get("src"), attributes.get("data-src"), attributes.get("data-video")]
        if tag.lower() in {"a", "link"}:
            values += [attributes.get("href")]
        for value in values:
            if not value or value.startswith(("data:", "blob:", "javascript:", "#")):
                continue
            target = urljoin(self.page_url, value.strip())
            path = urlsplit(target).path.lower()
            if path.endswith(VIDEO_EXTENSIONS) or ".m3u8" in target.lower() or ".mpd" in target.lower():
                self.urls.add(target)


def discover_videos(page_url):
    request = Request(safe_url(page_url), headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            content_type = response.getheader("content-type", "")
            if "html" not in content_type.lower():
                return set(), None
            body = response.read()
        parser = VideoParser(page_url)
        parser.feed(body.decode("utf-8", errors="replace"))
        return parser.urls, None
    except Exception as error:
        return set(), str(error)


def check(url: str):
    target = safe_url(url)
    try:
        request = Request(target, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=TIMEOUT) as response:
            return url, response.status, response.getheader("content-type", "")
    except Exception as first_error:
        try:
            request = Request(target, headers={"Range": "bytes=0-0", "User-Agent": USER_AGENT})
            with urlopen(request, timeout=TIMEOUT) as response:
                return url, response.status, response.getheader("content-type", "")
        except Exception as second_error:
            status = getattr(second_error, "code", None) or getattr(first_error, "code", None) or "ERR"
            return url, status, str(second_error)


def check_many(urls):
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(check, url) for url in urls]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: item[0])


def status_ok(status):
    return isinstance(status, int) and 200 <= status < 400


def render_table(results):
    lines = ["| Status | URL | Detail |", "|---:|---|---|"]
    failed = []
    for url, status, detail in results:
        ok = status_ok(status)
        if not ok:
            failed.append((url, status, detail))
        icon = "✅" if ok else "❌"
        detail = str(detail).replace("|", "\\|").replace("\n", " ")[:160]
        lines.append(f"| {icon} {status} | {url} | {detail} |")
    return lines, failed


def main():
    pages = load_urls()
    page_results = check_many(pages)

    video_urls = set()
    discovery_errors = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(discover_videos, page): page for page in pages}
        for future in as_completed(futures):
            page = futures[future]
            found, error = future.result()
            video_urls.update(found)
            if error:
                discovery_errors.append((page, error))
    video_results = check_many(sorted(video_urls)) if video_urls else []

    page_table, page_failed = render_table(page_results)
    video_table, video_failed = render_table(video_results)
    total_failed = page_failed + video_failed
    lines = [
        "## Website quick scan",
        "",
        f"- Sitemap: `{SITEMAP_URL}`",
        f"- Pages checked: **{len(page_results)}**",
        f"- Videos discovered: **{len(video_results)}**",
        f"- Page result: **{len(page_results) - len(page_failed)} passed, {len(page_failed)} failed**",
        f"- Video result: **{len(video_results) - len(video_failed)} passed, {len(video_failed)} failed**",
        "",
        "### Pages",
        *page_table,
    ]
    if video_results:
        lines += ["", "### Videos", *video_table]
    else:
        lines += ["", "### Videos", "No video resources were found in the sitemap pages."]
    if discovery_errors:
        lines += ["", f"Video discovery warnings: {len(discovery_errors)} page(s) could not be fetched for video extraction."]
        lines += [f"- `{page}`: {error}" for page, error in discovery_errors[:20]]
    lines += ["", f"**Overall result: {len(page_results) + len(video_results) - len(total_failed)} passed, {len(total_failed)} failed.**"]

    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if total_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
