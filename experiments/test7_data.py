from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


OFFICIAL_TEST7_PAGE = (
    'https://www.gov.uk/government/publications/'
    'benchmarking-the-latest-generation-of-2d-hydraulic-flood-modelling-packages'
)


@dataclass(slots=True)
class Test7DataProvenance:
    case_variant: str
    source_mode: str
    source_page_url: str
    technical_report_url: str | None
    model_zip_url: str | None
    local_report_path: str | None
    local_zip_path: str | None
    download_attempted: bool
    download_succeeded: bool
    fallback_reason: str | None = None
    notes: list[str] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['notes'] = list(self.notes or [])
        return payload


def _discover_local_assets(cache_root: Path) -> tuple[Path | None, Path | None]:
    report: Path | None = None
    model_zip: Path | None = None
    for candidate in sorted(cache_root.rglob('*')):
        if not candidate.is_file():
            continue
        lower = candidate.name.lower()
        if lower.endswith('.pdf') and report is None and ('benchmark' in lower or 'sc120002' in lower):
            report = candidate
        if lower.endswith('.zip') and model_zip is None and ('benchmark' in lower or 'lit-8570' in lower or 'model' in lower):
            model_zip = candidate
    return report, model_zip


def _extract_asset_urls(page_html: str, base_url: str) -> tuple[str | None, str | None]:
    pdf_matches = re.findall(r'href="([^"]+\.pdf[^"]*)"', page_html, flags=re.IGNORECASE)
    zip_matches = re.findall(r'href="([^"]+\.zip[^"]*)"', page_html, flags=re.IGNORECASE)

    report_url: str | None = None
    model_zip_url: str | None = None
    for href in pdf_matches:
        resolved = urljoin(base_url, href)
        lower = resolved.lower()
        if 'sc120002' in lower or 'benchmark' in lower:
            report_url = resolved
            break
    for href in zip_matches:
        resolved = urljoin(base_url, href)
        lower = resolved.lower()
        if 'benchmark' in lower or 'lit-8570' in lower or 'model' in lower:
            model_zip_url = resolved
            break
    return report_url, model_zip_url


def _download_file(url: str, destination: Path, timeout: float) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={'User-Agent': 'Codex-Test7-Downloader/1.0'})
    with urlopen(request, timeout=timeout) as response:
        destination.write_bytes(response.read())
    return destination


def resolve_test7_data(
    cache_root: Path,
    *,
    allow_download: bool = True,
    timeout: float = 8.0,
) -> Test7DataProvenance:
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    local_report, local_zip = _discover_local_assets(cache_root)
    if local_report is not None and local_zip is not None:
        return Test7DataProvenance(
            case_variant='official_test7_overtopping_only_variant',
            source_mode='official_cached',
            source_page_url=OFFICIAL_TEST7_PAGE,
            technical_report_url=None,
            model_zip_url=None,
            local_report_path=str(local_report),
            local_zip_path=str(local_zip),
            download_attempted=False,
            download_succeeded=False,
            notes=['使用仓库/本地缓存中的 EA Test 7 benchmark assets。'],
        )

    if not allow_download:
        return Test7DataProvenance(
            case_variant='surrogate_test7_overtopping_only_variant',
            source_mode='surrogate',
            source_page_url=OFFICIAL_TEST7_PAGE,
            technical_report_url=None,
            model_zip_url=None,
            local_report_path=None,
            local_zip_path=None,
            download_attempted=False,
            download_succeeded=False,
            fallback_reason='official_data_not_found_and_download_disabled',
            notes=['未找到官方缓存，且下载被禁用，转入 documented surrogate。'],
        )

    try:
        request = Request(OFFICIAL_TEST7_PAGE, headers={'User-Agent': 'Codex-Test7-Downloader/1.0'})
        with urlopen(request, timeout=timeout) as response:
            page_html = response.read().decode('utf-8', errors='replace')
        report_url, model_zip_url = _extract_asset_urls(page_html, OFFICIAL_TEST7_PAGE)
        if report_url is None or model_zip_url is None:
            raise RuntimeError('无法从官方 GOV.UK 页面解析 technical report / model zip 链接')
        downloaded_report = _download_file(report_url, cache_root / Path(report_url).name, timeout=timeout)
        downloaded_zip = _download_file(model_zip_url, cache_root / Path(model_zip_url).name, timeout=timeout)
        return Test7DataProvenance(
            case_variant='official_test7_overtopping_only_variant',
            source_mode='official_downloaded',
            source_page_url=OFFICIAL_TEST7_PAGE,
            technical_report_url=report_url,
            model_zip_url=model_zip_url,
            local_report_path=str(downloaded_report),
            local_zip_path=str(downloaded_zip),
            download_attempted=True,
            download_succeeded=True,
            notes=['成功从 GOV.UK 获取官方 benchmark technical report 与 model data ZIP。'],
        )
    except Exception as exc:  # pragma: no cover - error path is exercised through tests via monkeypatch
        return Test7DataProvenance(
            case_variant='surrogate_test7_overtopping_only_variant',
            source_mode='surrogate',
            source_page_url=OFFICIAL_TEST7_PAGE,
            technical_report_url=None,
            model_zip_url=None,
            local_report_path=None,
            local_zip_path=None,
            download_attempted=True,
            download_succeeded=False,
            fallback_reason=str(exc),
            notes=[
                '官方 Test 7 数据获取失败，自动退回 documented surrogate overtopping-only variant。',
                '该 fallback 不是静默行为，后续文档与 summary 中会保留 provenance 记录。',
            ],
        )
