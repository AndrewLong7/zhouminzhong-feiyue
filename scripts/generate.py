"""州民中飞跃手册 - 卡片生成脚本

从 data/cases.yml 读取元数据，自动生成各页面的案例卡片和大学卡片。
运行方式: python scripts/generate.py
"""

import re
from pathlib import Path
from collections import defaultdict

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "cases.yml"
DOCS = ROOT / "docs"

# ============================================================
# 1. 读取数据
# ============================================================
with open(DATA_FILE, encoding="utf-8") as f:
    data = yaml.safe_load(f)

cases = data["cases"]
universities = data["universities"]

# 预计算索引
cases_by_year = defaultdict(list)
for c in cases:
    cases_by_year[c["year"]].append(c)

cases_by_school = defaultdict(list)
for c in cases:
    cases_by_school[c["school"]].append(c)


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
    <div class="fy-case-card-school">🏫 {c['school']} · {c['major']}</div>
    <div class="fy-case-card-major-score">高考 {c['score']} 分 · 全省第 {c['rank']} 名</div>
    <div class="fy-case-card-summary">
      "{c['quote']}"
    </div>
  </div>
  <div class="fy-case-card-tags">{type_badge}{tags_html}
  </div>
  <a href="{href}" style="display: block; margin-top: 12px; color: var(--md-primary-fg-color); font-weight: 500; text-decoration: none;">阅读全文 →</a>
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
    return f"""<div class="fy-school-card" style="cursor: pointer;" onclick="location.href='{slug}/'">
  <span class="fy-school-card-name">{year} 届</span>
  <span class="fy-school-card-count">{count_text}</span>
  <span class="fy-school-card-major">{major_text}</span>
</div>"""


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

    # 链接：有案例则跳到案例库，无案例则跳到投稿页（相对路径）
    if school_cases:
        first_case = school_cases[0]
        slug = first_case["file"].replace("cases/", "").replace(".md", "/")
        link = f"{base}cases/{slug}"
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
    lines.append(f"""<div class="fy-school-card" style="cursor: pointer;" onclick="location.href='earlier/'">
  <span class="fy-school-card-name">更早的案例</span>
  <span class="fy-school-card-count">{earlier_count_text}</span>
  <span class="fy-school-card-major">{earlier_major_text}</span>
</div>""")

    return "\n\n".join(lines)


def gen_latest_cases(for_index: bool = False) -> str:
    """生成最新案例列表（按届数降序）"""
    sorted_cases = sorted(cases, key=lambda c: c["year"], reverse=True)
    cards = []
    for c in sorted_cases:
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

    cards = [case_card(c, c["file"].split("/")[-1].replace(".md", "/")) for c in sorted(year_cases, key=lambda c: c["year"], reverse=True)]
    return "\n".join(cards)


def gen_homepage_university_cards() -> str:
    """生成首页大学卡片（不带分类标题）"""
    all_schools = []
    for cat in universities:
        all_schools.extend(cat["schools"])
    cards = [university_card(s, "") for s in all_schools]
    return "\n\n".join(cards)


def gen_university_cards() -> str:
    """生成大学分类页的所有卡片（按白名单分类）"""
    sections = []
    for cat in universities:
        category_name = cat["category"]
        schools = cat["schools"]
        cards = [university_card(s, "../") for s in schools]
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
        print(f"  ⚠ 文件不存在: {filepath}")
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
        print(f"  ✓ 已更新: {filepath.relative_to(ROOT)}")
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
        print("⚠️  以下 case 文件未在 data/cases.yml 中注册：")
        for f in sorted(missing_in_yaml):
            print(f"    - {f}")
        print()

    if missing_on_disk:
        print("⚠️  data/cases.yml 中以下条目指向不存在的文件：")
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

    if all_ok:
        print("\n✅ 全部完成（校验通过）")
    else:
        print("❌ 请先修复上述问题后再提交")


if __name__ == "__main__":
    main()
