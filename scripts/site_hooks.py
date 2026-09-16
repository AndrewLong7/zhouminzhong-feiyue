"""Build-only page metadata and analytics configuration; no visitor data is stored here."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse
import yaml
from mkdocs.exceptions import ConfigurationError

ROOT = Path(__file__).resolve().parent.parent
CASES = {}

def on_config(config):
    global CASES
    data = yaml.safe_load((ROOT / "data/cases.yml").read_text(encoding="utf-8"))
    CASES = {item["file"]: item for item in data["cases"]}
    analytics = config.extra.get("feiyue_analytics", {})
    script, website_id = analytics.get("script_url"), analytics.get("website_id")
    if bool(script) != bool(website_id):
        raise ConfigurationError("统计脚本 URL 与网站 ID 必须同时配置，或同时留空。")
    for key in ("script_url", "dashboard_url"):
        if analytics.get(key):
            parsed = urlparse(analytics[key])
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ConfigurationError("统计地址必须是无账号、令牌、查询参数的 HTTPS 地址。")
    if website_id and not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", website_id):
        raise ConfigurationError("请使用 Umami 提供的网站 UUID，不能填写 API 密钥。")
    return config

def on_page_markdown(markdown, page, config, files):
    case = CASES.get(page.file.src_uri)
    if not case:
        return markdown
    page.meta["fy_case"] = hashlib.sha256(case["file"].encode()).hexdigest()[:16]
    heading = f"{case['school']} · {case['major']}"
    markdown = re.sub(r"^# 我的飞跃故事\s*$", lambda _: "# " + heading, markdown, count=1, flags=re.M)
    page.title = f"{heading}｜{case['name']}"
    for label, field in (("高考分数", "score"), ("全省位次", "rank"), ("毕业届数", "year")):
        if not case.get(field):
            pattern = r'(<div class="fy-case-info-label">' + label + r'</div>\s*<div class="fy-case-info-value">)[^<]*(</div>)'
            markdown = re.sub(pattern, r"\g<1>未提供\g<2>", markdown)
    return markdown
