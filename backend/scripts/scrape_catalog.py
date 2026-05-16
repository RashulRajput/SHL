from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.shl.com"
CATALOG_URL = f"{BASE_URL}/products/product-catalog/"
USER_AGENT = "Mozilla/5.0 (compatible; SHLAssessmentRecommender/1.0)"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "catalog.json"
SEED_INPUT = Path(__file__).resolve().parents[1] / "data" / "catalog.seed.json"


def request_with_retry(session: requests.Session, url: str, attempts: int = 4) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def parse_catalog_page(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for candidate in soup.find_all("table"):
        if "Individual Test Solutions" in candidate.get_text(" ", strip=True):
            table = candidate
            break
    if table is None:
        return []

    rows: list[dict[str, Any]] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        link = cells[0].find("a", href=True)
        if link is None:
            continue
        types = [span.get_text(strip=True) for span in cells[3].select(".product-catalogue__key")]
        rows.append(
            {
                "id": row.get("data-entity-id") or re.sub(r"\W+", "-", link.get_text(strip=True).lower()),
                "name": link.get_text(" ", strip=True),
                "url": urljoin(BASE_URL, link["href"]),
                "remote_testing": bool(cells[1].select_one(".catalogue__circle.-yes")),
                "adaptive_irt": bool(cells[2].select_one(".catalogue__circle.-yes")),
                "test_types": types,
            }
        )
    return rows


def parse_detail_page(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    details: dict[str, Any] = {}
    for row in soup.select(".product-catalogue-training-calendar__row"):
        heading = row.find("h4")
        if heading is None:
            continue
        key = heading.get_text(" ", strip=True).lower()
        paragraph = row.find("p")
        value = paragraph.get_text(" ", strip=True) if paragraph else ""
        if key == "description":
            details["description"] = value
        elif key == "job levels":
            details["job_levels"] = split_csvish(value)
        elif key == "languages":
            details["languages"] = split_csvish(value)
        elif key == "assessment length":
            details["duration"] = value.replace("Approximate Completion Time in minutes =", "").strip()
            detail_types = [span.get_text(strip=True) for span in row.select(".product-catalogue__key")]
            if detail_types:
                details["test_types"] = detail_types
            remote = row.select_one(".catalogue__circle.-yes")
            if remote is not None:
                details["remote_testing"] = True
        elif key == "downloads":
            details["downloads"] = [
                link.get("href", "")
                for link in row.select("a[href]")
                if link.get("href", "").startswith("http")
            ]
    return details


def split_csvish(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_seed_details() -> dict[str, dict[str, Any]]:
    if not SEED_INPUT.exists():
        return {}
    payload = json.loads(SEED_INPUT.read_text(encoding="utf-8"))
    return {item["url"]: item for item in payload.get("assessments", []) if item.get("url")}


def with_defaults(row: dict[str, Any], seed_details: dict[str, dict[str, Any]]) -> dict[str, Any]:
    seed = seed_details.get(row["url"], {})
    merged = {**seed, **row, "source": "shl_catalog"}
    merged.setdefault("description", seed.get("description", ""))
    merged.setdefault("duration", seed.get("duration", ""))
    merged.setdefault("job_levels", seed.get("job_levels", []))
    merged.setdefault("languages", seed.get("languages", []))
    merged.setdefault("downloads", seed.get("downloads", []))
    return merged


def scrape(output: Path, workers: int = 8, include_details: bool = True) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    seed_details = load_seed_details()

    listed: dict[str, dict[str, Any]] = {}
    start = 0
    while True:
        url = f"{CATALOG_URL}?start={start}&type=1"
        rows = parse_catalog_page(request_with_retry(session, url).text)
        if not rows:
            break
        before = len(listed)
        for row in rows:
            listed[row["url"]] = row
        if len(listed) == before:
            break
        start += 12
        time.sleep(0.2)

    def enrich(row: dict[str, Any]) -> dict[str, Any] | None:
        local_session = requests.Session()
        local_session.headers.update({"User-Agent": USER_AGENT})
        try:
            details = parse_detail_page(request_with_retry(local_session, row["url"]).text)
            return with_defaults({**row, **details}, seed_details)
        except Exception as exc:
            print(f"Skipping {row['url']} due to error: {exc}")
            return None

    if include_details:
        assessments: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(enrich, row) for row in listed.values()]
            for index, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                if result:
                    assessments.append(result)
                if index % 25 == 0:
                    print(f"Enriched {index}/{len(listed)} detail pages")
    else:
        assessments = [with_defaults(row, seed_details) for row in listed.values()]

    assessments.sort(key=lambda item: item["name"].lower())
    payload = {
        "source": CATALOG_URL,
        "scope": "Individual Test Solutions",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(assessments),
        "assessments": assessments,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape SHL Individual Test Solutions catalog.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--list-only", action="store_true", help="Scrape catalog list pages without slow detail pages.")
    args = parser.parse_args()
    payload = scrape(args.output, workers=args.workers, include_details=not args.list_only)
    print(f"Wrote {payload['count']} assessments to {args.output}")


if __name__ == "__main__":
    main()
