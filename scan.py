#!/usr/bin/env python3
"""Quickly check every URL in a sitemap and emit a GitHub Actions summary."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
import os
import sys

SITEMAP_URL = os.getenv("SITEMAP_URL", "https://trbo.jiagar.us.kg/sitemap.xml")
TIMEOUT = float(os.getenv("TIMEOUT", "15"))
WORKERS = int(os.getenv("WORKERS", "16"))


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@"), quote(parts.query, safe="=&/?%@:+"), ""))


def load_urls():
    request = Request(SITEMAP_URL, headers={"User-Agent": "website-quick-scan/1.0"})
    with urlopen(request, timeout=TIMEOUT) as response:
        root = ET.fromstring(response.read())
    urls = [element.text.strip() for element in root.iter() if element.tag.endswith("loc") and element.text]
    if not urls:
        raise RuntimeError("sitemap contains no URLs")
    return urls


def check(url: str):
    target = safe_url(url)
    try:
        request = Request(target, method="HEAD", headers={"User-Agent": "website-quick-scan/1.0"})
        with urlopen(request, timeout=TIMEOUT) as response:
            return url, response.status, response.getheader("content-type", "")
    except Exception as first_error:
        try:
            request = Request(target, headers={"Range": "bytes=0-0", "User-Agent": "website-quick-scan/1.0"})
            with urlopen(request, timeout=TIMEOUT) as response:
                return url, response.status, response.getheader("content-type", "")
        except Exception as second_error:
            status = getattr(second_error, "code", None) or getattr(first_error, "code", None) or "ERR"
            return url, status, str(second_error)


def main():
    urls = load_urls()
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(check, url) for url in urls]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item[0])

    failed = []
    lines = ["## Website quick scan", "", f"- Sitemap: `{SITEMAP_URL}`", f"- URLs checked: **{len(results)}**", ""]
    lines.append("| Status | URL | Detail |")
    lines.append("|---:|---|---|")
    for url, status, detail in results:
        ok = isinstance(status, int) and 200 <= status < 400
        if not ok:
            failed.append((url, status, detail))
        icon = "✅" if ok else "❌"
        detail = str(detail).replace("|", "\\|").replace("\n", " ")[:160]
        lines.append(f"| {icon} {status} | {url} | {detail} |")
    lines += ["", f"**Result: {len(results) - len(failed)} passed, {len(failed)} failed.**"]

    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
