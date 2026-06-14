"""州民中飞跃手册 - 卡片生成脚本

从 data/cases.yml 读取元数据，自动生成各页面的案例卡片和大学卡片。
运行方式: python scripts/generate.py
"""

import re
from datetime import date
from pathlib import Path
from collections import defaultdict

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "cases.yml"
SCHOOLS_FILE = ROOT / "data" / "schools.yml"
DOCS = ROOT / "docs"

# ============================================================
# 1. 读取数据
# ============================================================
with open(DATA_FILE, encoding="utf-8") as f:
    data = yaml.safe_load(f)

cases = data["cases"]
universities = data["universities"]

# 学校结构化元数据(官网/城市/类型),独立文件以免被 sync.py 覆盖
if SCHOOLS_FILE.exists():
    with open(SCHOOLS_FILE, encoding="utf-8") as f:
        SCHOOL_INFO = yaml.safe_load(f) or {}
else:
    SCHOOL_INFO = {}

# 预计算：案例内容长度（用于排序）
_case_length_cache = {}
for c in cases:
    md_path = DOCS / c["file"]
    try:
        text = md_path.read_text(encoding="utf-8")
        # 去掉 frontmatter
        if text.startswith("---"):
            end = text.find("---", 4)
            body = text[end + 3:] if end != -1 else text
        else:
            body = text
        _case_length_cache[c["file"]] = len(body)
    except Exception:
        _case_length_cache[c["file"]] = 0


def _case_content_len(case: dict) -> int:
    """返回案例 .md 文件正文字符数，越长 = 内容越丰富。"""
    return _case_length_cache.get(case["file"], 0)


def _school_content_len(school_name: str) -> int:
    """返回某学校单个最长案例的内容长度（按最优案例排名）。"""
    school_cases = cases_by_school.get(school_name, [])
    if not school_cases:
        return 0
    return max(_case_content_len(c) for c in school_cases)


# 预计算索引
cases_by_year = defaultdict(list)
for c in cases:
    cases_by_year[c["year"]].append(c)

cases_by_school = defaultdict(list)
for c in cases:
    cases_by_school[c["school"]].append(c)

# 学校 slug 映射：{学校名: slug}
school_slug = {}


def _slugify(text: str) -> str:
    """与 sync.py 保持一致的 URL slug 规则"""
    s = re.sub(r"[^\w一-龥]+", "-", text).strip("-").lower()
    return s or "school"


def _school_name(entry) -> str:
    """归一化：学校条目可以是字符串或 {name, slug} 对象"""
    if isinstance(entry, dict):
        name = entry["name"]
        if "slug" in entry:
            school_slug[name] = entry["slug"]
        return name
    return entry


def _iter_schools():
    """遍历所有学校名（用于排序和卡片生成）"""
    for cat in universities:
        for s in cat["schools"]:
            yield _school_name(s)


# 初始化 school_slug 映射(显式 slug 优先,其余自动 slugify)
for _name in _iter_schools():
    school_slug.setdefault(_name, _slugify(_name))


# ============================================================
# 2. HTML 生成函数
# ============================================================
def case_card(c: dict, href: str) -> str:
    """生成单个案例卡片 HTML"""
    type_badge = (
        '\n    <span class="fy-tag fy-tag-amber">模板案例</span>'
        if c["type"] == "template"
        else ""
    )
    tags_html = "".join(f'\n    <span class="fy-tag">{t}</span>' for t in c["tags"])

    return f"""<div class="fy-case-card">
  <div class="fy-case-card-header">
    <div class="fy-case-card-avatar">{c['avatar']}</div>
    <div class="fy-case-card-meta">
      <span class="fy-case-card-name">{c['name']}</span>
      <span class="fy-case-card-year">{c['year']} 届 · {c['group']}</span>
    </div>
  </div>
  <div class="fy-case-card-body">
    <div class="fy-case-card-school">{c['school']} · {c['major']}</div>
    <div class="fy-case-card-major-score">高考 {c['score']} 分 · 全省第 {c['rank']} 名</div>
    <div class="fy-case-card-summary">
      "{c['quote']}"
    </div>
  </div>
  <div class="fy-case-card-tags">{type_badge}{tags_html}
  </div>
  <a href="{href}" class="fy-case-card-link">阅读全文 →</a>
</div>"""


def year_card(year: int, count: int, is_template: bool = False) -> str:
    """生成年份卡片 HTML"""
    slug = str(year) if year >= 2023 else "earlier"
    if count == 0:
        count_text = "敬请期待"
        major_text = "敬请期待"
    else:
        count_text = f"{count} 个案例"
        major_text = "模板案例" if is_template else "往届毕业生"
    return f"""<a href="{slug}/" class="fy-school-card">
  <span class="fy-school-card-name">{year} 届</span>
  <span class="fy-school-card-count">{count_text}</span>
  <span class="fy-school-card-major">{major_text}</span>
</a>"""


def university_card(school: str, base: str = "") -> str:
    """生成大学卡片 HTML（base 为相对路径前缀）"""
    school_cases = cases_by_school.get(school, [])
    real_count = sum(1 for c in school_cases if c["type"] == "real")
    template_count = sum(1 for c in school_cases if c["type"] == "template")
    total = len(school_cases)

    if total == 0:
        count_text = "敬请期待"
    elif real_count == 0 and template_count > 0:
        count_text = "模板案例"
    elif real_count > 0:
        count_text = f"已收录 {real_count} 人"
    else:
        count_text = f"已收录 {total} 人"

    # 汇总专业
    majors = list(dict.fromkeys(c["major"] for c in school_cases))

    if not majors:
        majors_str = ""
    else:
        majors_str = " · ".join(majors[:3])

    # 链接：所有有案例的学校都走学校专属页(含信息卡 + 案例列表)
    # 无案例(敬请期待)的学校引导到投稿页
    slug = school_slug.get(school) or _slugify(school)
    if school_cases:
        link = f"{base}universities/{slug}/"
    else:
        link = f"{base}contribute/"

    return f"""<a href="{link}" class="fy-school-card">
  <span class="fy-school-card-name">{school}</span>
  <span class="fy-school-card-count">{count_text}</span>
  <span class="fy-school-card-major">{majors_str}</span>
</a>"""


# ============================================================
# 3. 生成各模块内容
# ============================================================
def gen_year_cards() -> str:
    """生成案例总览页的年份卡片区（固定 2025/2024/2023 + 更早的案例）"""
    lines = []
    fixed_years = [2025, 2024, 2023]
    for year in fixed_years:
        year_cases = cases_by_year.get(year, [])
        count = len(year_cases)
        is_template = all(c["type"] == "template" for c in year_cases) if year_cases else False
        lines.append(year_card(year, count, is_template))

    # 更早的案例 (< 2023)
    earlier_cases = [c for c in cases if c["year"] < 2023]
    earlier_count = len(earlier_cases)
    if earlier_count == 0:
        earlier_count_text = "敬请期待"
        earlier_major_text = "敬请期待"
    else:
        earlier_count_text = f"{earlier_count} 个案例"
        earlier_major_text = "往届毕业生"
    lines.append(f"""<a href="earlier/" class="fy-school-card">
  <span class="fy-school-card-name">更早的案例</span>
  <span class="fy-school-card-count">{earlier_count_text}</span>
  <span class="fy-school-card-major">{earlier_major_text}</span>
</a>""")

    return "\n\n".join(lines)


def gen_latest_cases(for_index: bool = False) -> str:
    """生成最新案例列表（按内容长度降序取前 6 条，优先展示丰富案例）"""
    latest = sorted(cases, key=_case_content_len, reverse=True)[:6]
    cards = []
    for c in latest:
        file_path = c["file"]
        if for_index:
            # 案例总览页：相对路径如 2025/xiaoxi-pku/
            href = file_path.replace("cases/", "").replace(".md", "/")
        else:
            # 首页：需要保留 cases/ 前缀
            href = file_path.replace(".md", "/")
        cards.append(case_card(c, href))
    return "\n".join(cards)


def gen_year_case_cards(year_dir: str) -> str:
    """生成特定年份页面的案例卡片"""
    # year_dir 如 "2025", "2024", "2023", "earlier"
    if year_dir == "earlier":
        # earlier 包含所有 < 2023 的案例
        year_cases = [c for c in cases if c["year"] < 2023]
    else:
        year_cases = cases_by_year.get(int(year_dir), [])

    if not year_cases:
        return '<div style="text-align: center; padding: 40px 16px;">\n\n该届案例正在收集中，敬请期待。\n\n</div>'

    cards = [case_card(c, c["file"].split("/")[-1].replace(".md", "/")) for c in sorted(year_cases, key=_case_content_len, reverse=True)]
    return "\n".join(cards)


def _sorted_schools(schools: list) -> list:
    """学校排序：有案例的优先（按内容总量降序），无案例的靠后"""
    return sorted(schools, key=lambda s: (
        len(cases_by_school.get(_school_name(s), [])) == 0,
        -_school_content_len(_school_name(s)),
    ))


def gen_footer_stats() -> str:
    """生成页脚的"最近更新+案例总数"行,体现活跃维护"""
    case_count = len(cases)
    school_count = len({c["school"] for c in cases})
    today = date.today().isoformat()
    return (
        f'<span class="fy-footer-stats-item">最近更新于 {today}</span>'
        f'<span class="fy-footer-stats-sep">·</span>'
        f'<span class="fy-footer-stats-item">已收录 {case_count} 位校友 / {school_count} 所大学</span>'
    )


def gen_homepage_stats() -> str:
    """生成首页 hero 下方的统计数字带（社会证明）"""
    case_count = len(cases)
    school_count = len({c["school"] for c in cases})
    year_count = len({c["year"] for c in cases})
    return f"""<div class="fy-stats">
  <div class="fy-stats-item">
    <span class="fy-stats-num">{case_count}</span>
    <span class="fy-stats-label">位校友故事</span>
  </div>
  <div class="fy-stats-item">
    <span class="fy-stats-num">{school_count}</span>
    <span class="fy-stats-label">所大学</span>
  </div>
  <div class="fy-stats-item">
    <span class="fy-stats-num">{year_count}</span>
    <span class="fy-stats-label">届毕业生</span>
  </div>
</div>"""


def gen_homepage_university_cards() -> str:
    """生成首页大学卡片（不带分类标题）"""
    all_schools = []
    for cat in universities:
        all_schools.extend(cat["schools"])
    cards = [university_card(_school_name(s), "") for s in _sorted_schools(all_schools)[:20]]
    return "\n\n".join(cards)


_SCHOOL_INFO_MARK_RE = re.compile(r'<!--\s*AUTO-GEN:\s*SCHOOL_INFO\s*-->')


def _ensure_school_info_marker(filepath: Path, school_name: str) -> None:
    """老的学校 md 文件可能不含 SCHOOL_INFO 区块,自动在 `# {学校}` 标题下方注入空占位"""
    text = filepath.read_text(encoding="utf-8")
    if _SCHOOL_INFO_MARK_RE.search(text):
        return
    title_re = re.compile(rf'^(# {re.escape(school_name)})\s*$', re.MULTILINE)
    m = title_re.search(text)
    if not m:
        return  # 找不到主标题,保守不动
    insert_at = m.end()
    insert = (
        '\n\n<!-- AUTO-GEN: SCHOOL_INFO -->\n'
        '<!-- /AUTO-GEN: SCHOOL_INFO -->'
    )
    filepath.write_text(text[:insert_at] + insert + text[insert_at:], encoding="utf-8")


def gen_school_info_card(school: str) -> str:
    """生成学校专属页顶部的"学校信息卡"HTML
    数据源 data/schools.yml,未注册的学校返回空串(模板里区块自动留空)
    """
    info = SCHOOL_INFO.get(school)
    case_count = sum(1 for c in cases_by_school.get(school, []) if c["type"] == "real")

    if not info:
        return ""

    types = info.get("type") or []
    tags_html = "".join(
        f'<span class="fy-school-info-chip">{t}</span>' for t in types
    )

    official = (info.get("official") or "").strip()
    if official:
        official_html = (
            f'<a href="{official}" target="_blank" rel="noopener noreferrer" '
            f'class="fy-school-info-link">'
            f'<span>访问 {school} 官网</span>'
            f'<span class="fy-school-info-link-arrow" aria-hidden="true">→</span>'
            f'</a>'
        )
    else:
        official_html = (
            '<span class="fy-school-info-link fy-school-info-link--disabled">'
            '官网链接待补充 · <a href="../../contribute/">提交一份</a>'
            '</span>'
        )

    city = (info.get("city") or "").strip()
    pin_svg = (
        '<svg class="fy-school-info-pin" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0'
        'C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0Z"/>'
        '<circle cx="12" cy="10" r="3"/></svg>'
    )
    city_html = (
        f'<span class="fy-school-info-city">{pin_svg}<span>{city}</span></span>'
        if city else ""
    )

    case_html = (
        f'<span class="fy-school-info-cases">已收录 {case_count} 位校友</span>'
        if case_count > 0 else ""
    )

    return f"""<div class="fy-school-info-card">
  <div class="fy-school-info-meta">
    {city_html}
    {case_html}
  </div>
  <div class="fy-school-info-tags">{tags_html}</div>
  <div class="fy-school-info-actions">
    {official_html}
  </div>
</div>"""


def gen_school_case_cards(school: str) -> str:
    """生成学校专属页面的案例卡片列表"""
    school_cases = cases_by_school.get(school, [])
    if not school_cases:
        return '<div style="text-align: center; padding: 40px 16px;">\n\n暂无案例。\n\n</div>'
    cards = [case_card(c, f"../../cases/{c['file'].replace('cases/', '').replace('.md', '/')}") for c in school_cases]
    return "\n".join(cards)


def gen_university_cards() -> str:
    """生成大学分类页的所有卡片（按白名单分类）"""
    sections = []
    for cat in universities:
        category_name = cat["category"]
        schools = _sorted_schools(cat["schools"])
        cards = [university_card(_school_name(s), "../") for s in schools]
        cards_html = "\n\n".join(cards)
        sections.append(f"""## {category_name}

<div class="fy-card-grid">

{cards_html}

</div>""")

    return "\n\n".join(sections)


# ============================================================
# 4. 页面处理
# ============================================================
MARKER_START = re.compile(r"<!-- AUTO-GEN:\s*(\w+)\s*-->")
MARKER_END = re.compile(r"<!-- /AUTO-GEN:\s*\w+\s*-->")


def process_page(filepath: Path, generators: dict) -> bool:
    """处理单个页面，替换 AUTO-GEN 标记之间的内容"""
    if not filepath.exists():
        print(f"  [!] 文件不存在: {filepath}")
        return False

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    modified = False
    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = MARKER_START.search(line)
        if m:
            key = m.group(1)
            new_lines.append(line)  # 保留起始标记行

            # 跳过旧内容直到结束标记
            i += 1
            while i < len(lines) and not MARKER_END.search(lines[i]):
                i += 1

            # 插入新内容
            if key in generators:
                gen_content = generators[key]()
                new_lines.append(gen_content)

            if i < len(lines):
                new_lines.append(lines[i])  # 保留结束标记行
            modified = True
        else:
            new_lines.append(line)
        i += 1

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n" if new_lines else "\n".join(new_lines))
        print(f"  [OK] 已更新: {filepath.relative_to(ROOT)}")
    else:
        print(f"  - 无标记: {filepath.relative_to(ROOT)}")

    return modified


def validate_coverage():
    """校验 YAML 元数据与实际 case 文件的一致性"""
    # 收集 YAML 中注册的文件路径
    yaml_files = {c["file"] for c in cases}

    # 收集 docs/cases/ 下所有实际的 case .md 文件（排除 index.md）
    actual_files = set()
    for md_file in DOCS.glob("cases/**/*.md"):
        if md_file.name == "index.md":
            continue
        rel = str(md_file.relative_to(DOCS)).replace("\\", "/")
        actual_files.add(rel)

    missing_in_yaml = actual_files - yaml_files
    missing_on_disk = yaml_files - actual_files

    if missing_in_yaml:
        print("[!]️  以下 case 文件未在 data/cases.yml 中注册：")
        for f in sorted(missing_in_yaml):
            print(f"    - {f}")
        print()

    if missing_on_disk:
        print("[!]️  data/cases.yml 中以下条目指向不存在的文件：")
        for f in sorted(missing_on_disk):
            print(f"    - {f}")
        print()

    return len(missing_in_yaml) == 0 and len(missing_on_disk) == 0


def main():
    print("州民中飞跃手册 - 卡片生成\n")

    # 0. 先做覆盖校验
    all_ok = validate_coverage()

    # 案例总览页
    print("[案例总览]")
    process_page(
        DOCS / "cases" / "index.md",
        {
            "YEAR_CARDS": gen_year_cards,
            "LATEST_CASES": lambda: gen_latest_cases(for_index=True),
        },
    )

    # 各年份页
    for year_dir in ["2025", "2024", "2023", "earlier"]:
        print(f"[{year_dir} 届]")
        process_page(
            DOCS / "cases" / year_dir / "index.md",
            {"CASE_CARDS": lambda yd=year_dir: gen_year_case_cards(yd)},
        )

    # 首页
    print("[首页]")
    process_page(
        DOCS / "index.md",
        {
            "HOMEPAGE_STATS": gen_homepage_stats,
            "HOMEPAGE_UNIVERSITIES": gen_homepage_university_cards,
            "LATEST_CASES": lambda: gen_latest_cases(for_index=False),
        },
    )

    # 大学分类页
    print("[大学分类]")
    process_page(
        DOCS / "universities" / "index.md",
        {"UNIVERSITY_CARDS": gen_university_cards},
    )

    # 页脚 (main.html 注入)
    print("[页脚]")
    process_page(
        DOCS / "overrides" / "main.html",
        {"FOOTER_STATS": gen_footer_stats},
    )

    # 学校专属页面(所有有案例的学校都建专属页:学校信息卡 + 校友案例列表)
    for school_name, slug in school_slug.items():
        school_cases = cases_by_school.get(school_name, [])
        if not school_cases:
            continue  # 暂无案例的学校不建空页

        print(f"[学校页: {slug}]")
        school_page = DOCS / "universities" / f"{slug}.md"
        if not school_page.exists():
            school_page.write_text(
                f"""---
title: {school_name}
not_in_nav: true
---

# {school_name}

<!-- AUTO-GEN: SCHOOL_INFO -->
<!-- /AUTO-GEN: SCHOOL_INFO -->

<div class="fy-case-grid">

<!-- AUTO-GEN: SCHOOL_CASE_CARDS -->
<!-- /AUTO-GEN: SCHOOL_CASE_CARDS -->

</div>
""",
                encoding="utf-8",
            )
        else:
            # 老 md 缺少 SCHOOL_INFO 区块时,自动在标题下方插入
            _ensure_school_info_marker(school_page, school_name)

        process_page(
            school_page,
            {
                "SCHOOL_INFO": lambda s=school_name: gen_school_info_card(s),
                "SCHOOL_CASE_CARDS": lambda s=school_name: gen_school_case_cards(s),
            },
        )

    if all_ok:
        print("\n==> 全部完成（校验通过）")
    else:
        print("!! 请先修复上述问题后再提交")


if __name__ == "__main__":
    main()
