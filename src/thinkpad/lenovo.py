"""Official Lenovo document discovery helpers for the M1 HMM spike."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

LENOVO_BASE_URL = "https://pcsupport.lenovo.com"
LENOVO_DOWNLOAD_HOST = "download.lenovo.com"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; ThinkPadServiceCopilotMCP/0.1; +https://github.com/kevinhimself711)"
)


@dataclass(frozen=True)
class M1ManualTarget:
    """A representative ThinkPad HMM target used by the M1 spike."""

    manual_id: str
    title: str
    models: list[str]
    generations: list[str]
    machine_types: list[str]
    product_page_url: str
    local_pdf_path: str
    year: int | None = None


@dataclass(frozen=True)
class LenovoManualCandidate:
    """A document candidate returned by Lenovo's support APIs."""

    title: str
    url: str
    docid: str | None = None
    language: str | None = None
    updated: str | None = None
    source_bucket: str | None = None

    @property
    def is_hmm(self) -> bool:
        """Return True when the candidate looks like a Hardware Maintenance Manual."""

        title = self.title.lower()
        url = self.url.lower()
        return "hardware maintenance manual" in title or "_hmm_" in url or url.endswith("_hmm_en.pdf")


M1_MANUAL_TARGETS: list[M1ManualTarget] = [
    M1ManualTarget(
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        title="ThinkPad P14s Gen 2, T14 Gen 2 Hardware Maintenance Manual",
        models=["ThinkPad T14 Gen 2", "ThinkPad P14s Gen 2"],
        generations=["Gen 2"],
        machine_types=["20W0", "20W1"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-t-series-laptops/thinkpad-t14-gen-2-type-20w0-20w1/20w1/"
            "selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/t14_gen2_p14s_gen2_hmm_en.pdf",
        year=2021,
    ),
    M1ManualTarget(
        manual_id="thinkpad_t14_gen3_p14s_gen3_hmm",
        title="ThinkPad T14 Gen 3 and P14s Gen 3 Hardware Maintenance Manual",
        models=["ThinkPad T14 Gen 3", "ThinkPad P14s Gen 3"],
        generations=["Gen 3"],
        machine_types=["21AH", "21AJ"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-t-series-laptops/thinkpad-t14-gen-3-type-21ah-21aj/21ah/"
            "selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/t14_gen3_p14s_gen3_hmm_en.pdf",
        year=2022,
    ),
    M1ManualTarget(
        manual_id="thinkpad_t480_hmm",
        title="ThinkPad T480 Hardware Maintenance Manual",
        models=["ThinkPad T480"],
        generations=["T480"],
        machine_types=["20L5", "20L6"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-t-series-laptops/thinkpad-t480-type-20l5-20l6/20l5/"
            "selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/t480_hmm_en.pdf",
        year=2018,
    ),
    M1ManualTarget(
        manual_id="thinkpad_t490_hmm",
        title="ThinkPad T490 Hardware Maintenance Manual",
        models=["ThinkPad T490"],
        generations=["T490"],
        machine_types=["20N2", "20N3"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-t-series-laptops/thinkpad-t490-type-20n2-20n3/20n2/"
            "selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/t490_hmm_en.pdf",
        year=2019,
    ),
    M1ManualTarget(
        manual_id="thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
        title="ThinkPad X1 Carbon Gen 9, X1 Yoga Gen 6 Hardware Maintenance Manual",
        models=["ThinkPad X1 Carbon Gen 9", "ThinkPad X1 Yoga Gen 6"],
        generations=["Gen 9", "Gen 6"],
        machine_types=["20XW", "20XX"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-x-series-laptops/thinkpad-x1-carbon-9th-gen-type-20xw-20xx/"
            "20xw/selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf",
        year=2021,
    ),
    M1ManualTarget(
        manual_id="thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
        title="ThinkPad X1 Carbon Gen 10, X1 Yoga Gen 7 Hardware Maintenance Manual",
        models=["ThinkPad X1 Carbon Gen 10", "ThinkPad X1 Yoga Gen 7"],
        generations=["Gen 10", "Gen 7"],
        machine_types=["21CB", "21CC"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-x-series-laptops/thinkpad-x1-carbon-10th-gen-type-21cb-21cc/"
            "21cb/selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/x1_carbon_gen10_x1_yoga_gen7_hmm_en.pdf",
        year=2022,
    ),
    M1ManualTarget(
        manual_id="thinkpad_e14_gen2_e15_gen2_hmm",
        title="ThinkPad E14 Gen 2, E15 Gen 2 Hardware Maintenance Manual",
        models=["ThinkPad E14 Gen 2", "ThinkPad E15 Gen 2"],
        generations=["Gen 2"],
        machine_types=["20TA", "20TB", "20TD", "20TE"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-edge-laptops/thinkpad-e15-gen-2-type-20td-20te/20td/"
            "selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/e14_gen2_e15_gen2_hmm_en.pdf",
        year=2020,
    ),
    M1ManualTarget(
        manual_id="thinkpad_p1_gen4_x1_extreme_gen4_hmm",
        title="ThinkPad X1 Extreme Gen 4, P1 Gen 4 Hardware Maintenance Manual",
        models=["ThinkPad P1 Gen 4", "ThinkPad X1 Extreme Gen 4"],
        generations=["Gen 4"],
        machine_types=["20Y3", "20Y4", "20Y5", "20Y6"],
        product_page_url=(
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-p-series-laptops/thinkpad-p1-gen-4-type-20y3-20y4/20y3/"
            "selfrepair/removalsreplacements"
        ),
        local_pdf_path="data/manuals/x1_extreme_gen4_p1_gen4_hmm_en.pdf",
        year=2021,
    ),
]


def fetch_text(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Fetch URL text with a browser-like user agent."""

    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
    return raw.decode(encoding, errors="replace")


def extract_product_guid_chain(html: str) -> list[str]:
    """Extract Lenovo parent GUIDs plus the current product GUID from product HTML."""

    match = re.search(
        r'"Guid":"(?P<guid>[0-9A-Fa-f-]{36})".*?"ParentGuids":\[(?P<parents>.*?)\]',
        html,
        flags=re.DOTALL,
    )
    if not match:
        return []

    parents = re.findall(r'"([0-9A-Fa-f-]{36})"', match.group("parents"))
    guid = match.group("guid")
    seen: set[str] = set()
    chain: list[str] = []
    for item in [*parents, guid]:
        normalized = item.upper()
        if normalized not in seen:
            seen.add(normalized)
            chain.append(normalized)
    return chain


def build_recommend_manual_url(
    product_guids: Iterable[str],
    *,
    country: str = "us",
    language: str = "en",
) -> str:
    """Build Lenovo's official recommended-manual API URL for a product GUID chain."""

    encoded_pids = quote(",".join(product_guids), safe=",")
    return (
        f"{LENOVO_BASE_URL}/{country}/{language}/api/v4/contents/recommendmanual"
        f"?pids={encoded_pids}&loggedIn=false&language={language}"
        f"&countries={country}&remove-count-limit=true"
    )


def _normalize_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(LENOVO_BASE_URL, url)
    return url


def _walk_payload(value: Any) -> Iterable[tuple[str | None, dict[str, Any]]]:
    if isinstance(value, dict):
        bucket = value.get("_bucket")
        if "title" in value and ("url" in value or "pdfLink" in value or "htmlLink" in value):
            yield bucket, value
        for key, child in value.items():
            if isinstance(child, list):
                for item in child:
                    if isinstance(item, dict):
                        item = dict(item)
                        item.setdefault("_bucket", str(key))
                    yield from _walk_payload(item)
            else:
                yield from _walk_payload(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_payload(item)


def extract_manual_candidates(payload: dict[str, Any]) -> list[LenovoManualCandidate]:
    """Extract official Lenovo manual candidates from a support API payload."""

    candidates: list[LenovoManualCandidate] = []
    for bucket, item in _walk_payload(payload):
        raw_url = item.get("url") or item.get("pdfLink") or item.get("htmlLink")
        title = item.get("title")
        if not raw_url or not title:
            continue
        url = _normalize_url(str(raw_url))
        host = urlparse(url).netloc.lower()
        if not (host == LENOVO_DOWNLOAD_HOST or host.endswith(".lenovo.com")):
            continue
        candidates.append(
            LenovoManualCandidate(
                title=str(title),
                url=url,
                docid=item.get("docid"),
                language=item.get("language"),
                updated=item.get("updated"),
                source_bucket=bucket,
            )
        )

    deduped: list[LenovoManualCandidate] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)
        deduped.append(candidate)
    return deduped


def discover_hmm_candidates_from_product_page(product_page_url: str) -> list[LenovoManualCandidate]:
    """Discover HMM candidates by scraping product GUIDs then calling Lenovo's API."""

    html = fetch_text(product_page_url)
    product_guids = extract_product_guid_chain(html)
    if not product_guids:
        return []
    payload = json.loads(fetch_text(build_recommend_manual_url(product_guids)))
    return [candidate for candidate in extract_manual_candidates(payload) if candidate.is_hmm]
