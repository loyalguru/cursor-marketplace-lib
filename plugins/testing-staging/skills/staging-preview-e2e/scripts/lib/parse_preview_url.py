#!/usr/bin/env python3
"""Extract cloud preview metadata from deploy/console/service URLs.

Prints KEY=value lines for state updates. Unknown fields omitted.
Does not hardcode any project or region. Callers must not eval untrusted
comment text as shell — parse structured KEY=value only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import parse_qs, urlparse

# Google Cloud Console Cloud Run detail:
# https://console.cloud.google.com/run/detail/<region>/<service>/...?...&project=<id>
CONSOLE_RUN_RE = re.compile(
    r"/run/detail/(?P<region>[^/]+)/(?P<service>[^/?#]+)",
    re.IGNORECASE,
)

# Cloud Run HTTPS service URL:
# https://<service>-<projectNumber>.<region>.run.app
RUN_APP_RE = re.compile(
    r"^(?P<host_service>.+)-(?P<project_number>\d+)\.(?P<region>[a-z0-9-]+)\.run\.app$",
    re.IGNORECASE,
)


def parse_url(raw: str) -> dict[str, str]:
    text = raw.strip()
    if not text:
        return {}

    parsed = urlparse(text)
    out: dict[str, str] = {}

    query = parse_qs(parsed.query)
    for key in ("project", "projectId", "project_id"):
        values = query.get(key) or []
        if values and values[0]:
            out["GCP_PROJECT"] = values[0]
            break

    console = CONSOLE_RUN_RE.search(parsed.path or "")
    if console:
        out["GCP_REGION"] = console.group("region")
        out["GCP_SERVICE"] = console.group("service")

    host = parsed.hostname or ""
    run_app = RUN_APP_RE.match(host)
    if run_app:
        # Hostname embeds project *number*, not project id.
        out["GCP_PROJECT_NUMBER"] = run_app.group("project_number")
        out["GCP_REGION"] = run_app.group("region")
        out["GCP_SERVICE"] = run_app.group("host_service")
        out.setdefault("URL", f"{parsed.scheme}://{host}")

    return out


def build_run_app_url(service: str, project_number: str, region: str) -> str:
    """Build a Cloud Run HTTPS URL from console/service metadata.

    Does not call gcloud. Project number (not project id) is required.
    """
    service = service.strip()
    project_number = project_number.strip()
    region = region.strip()
    if not service or not project_number or not region:
        raise ValueError("service, project_number, and region are required")
    return f"https://{service}-{project_number}.{region}.run.app"


def parse_text(text: str) -> dict[str, str]:
    """Scan free text (PR comment, workflow log) for the first useful URL."""
    url_re = re.compile(r"https?://[^\s<>\"']+")
    merged: dict[str, str] = {}
    for match in url_re.finditer(text):
        candidate = match.group(0).rstrip(").,;")
        parsed = parse_url(candidate)
        # Prefer console URLs that carry project id over run.app hostnames.
        if "GCP_PROJECT" in parsed and "GCP_PROJECT" not in merged:
            merged.update(parsed)
        elif not merged:
            merged.update(parsed)
        elif "GCP_PROJECT" not in merged and "GCP_PROJECT" in parsed:
            merged.update(parsed)
    # If we only got console metadata, try to attach URL from a run.app link
    # elsewhere in the same text, or leave URL unset for the caller.
    if "URL" not in merged:
        for match in url_re.finditer(text):
            candidate = match.group(0).rstrip(").,;")
            parsed = parse_url(candidate)
            if "URL" in parsed:
                if "GCP_SERVICE" in merged and parsed.get("GCP_SERVICE") not in (
                    None,
                    merged.get("GCP_SERVICE"),
                ):
                    continue
                merged["URL"] = parsed["URL"]
                merged.setdefault(
                    "GCP_PROJECT_NUMBER", parsed.get("GCP_PROJECT_NUMBER", "")
                )
                break
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        help="URL or path to a text file; stdin if omitted",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of KEY=value lines",
    )
    args = parser.parse_args()

    if args.input:
        path_or_url = args.input
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            data = parse_url(path_or_url)
        else:
            data = parse_text(open(path_or_url, encoding="utf-8").read())
    else:
        data = parse_text(sys.stdin.read())

    if args.json:
        json.dump(data, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        for key in sorted(data):
            print(f"{key}={data[key]}")

    return 0 if data else 1


if __name__ == "__main__":
    raise SystemExit(main())
