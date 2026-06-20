"""州民中飞跃手册 - 一键同步脚本

从 docs/cases/ 下的标准 .md 文件自动生成 data/cases.yml，
然后更新所有页面的案例卡片和大学卡片。

运行方式:
    python scripts/sync.py

依赖:
    pyyaml
"""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CASES_DIR = DOCS / "cases"
DATA_FILE = ROOT / "data" / "cases.yml"


# ================================================================
# 1. 解析单个 .md 案例文件
# ================================================================
def parse_frontmatter(text: str) -> dict:
    """从 .md 文本中解析 YAML frontmatter。"""
    text = text.strip()
    if not text.startswith("---"):
        return {}
    end = text.find("---", 4)
    if end == -1:
        return {}
    yaml_str = text[4:end].strip()
    try:
        return yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError:
        return {}


def parse_info_items(content: str) -> dict:
    """解析 fy-case-info-item HTML 块，提取 label -> value 映射。"""
    info = {}
    pattern = (
        r'<div class="fy-case-info-label">([^<]+)</div>\s*'
        r'<div class="fy-case-info-value">([^<]*)</div>'
    )
    for m in re.finditer(pattern, content):
        label = m.group(1).strip()
        value = m.group(2).strip()
        if label and value:
            info[label] = value
    return info


def sanitize_text(s: str) -> str:
    """移除 Non-BMP 字符（emoji 等，PyYAML 不兼容），应用于所有写入 YAML 的字段。"""
    result = []
    for ch in s:
        if ord(ch) <= 0xFFFF:
            result.append(ch)
    return "".join(result)


def clean_quote(s: str) -> str:
    """清洗引用语：去引号、移除 non-BMP 字符。"""
    s = sanitize_text(s).strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1].strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1].strip()
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1].strip()
    return s


def extract_quote(content: str) -> str:
    """从「写给后来者的一句话」section 提取引用语。"""
    pattern = r'写给后来者[^\n]*\n\n> (.+?)(?:\n|$)'
    m = re.search(pattern, content)
    if m:
        return clean_quote(m.group(1))
    return ""


def parse_year(raw: str) -> int:
    """'2023 届' / '23 届' -> 2023。仅用于 fallback（非年份目录）。"""
    m = re.search(r"(\d+)", raw)
    if not m:
        return 0
    n = int(m.group(1))
    if n < 100:
        return n + 1900 if n >= 50 else n + 2000
    return n


def parse_number(raw: str) -> int:
    """解析数值：兼容 50000 / 5w / 5万 / 1w3 / 1.3万 等格式。"""
    if not raw:
        return 0
    s = raw.strip().replace(",", "").replace("，", "")

    # 1. "1w3" / "1w" / "1.3w" 等英文简写
    m = re.search(r"(\d+(?:\.\d+)?)w(\d*)\s*名?", s, re.IGNORECASE)
    if m:
        base = int(float(m.group(1)) * 10000)
        extra = int(m.group(2)) * 1000 if m.group(2) else 0
        return base + extra

    # 2. "1.3万" / "5万" 等中文单位
    m = re.search(r"(\d+(?:\.\d+)?)\s*万", s)
    if m:
        return int(float(m.group(1)) * 10000)

    # 3. 普通数字：50000 / 61 / 全省第 61 名
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else 0


def parse_group(raw: str) -> str:
    """提取选科类型：物理类 / 历史类 / 其他。"""
    if "物理" in raw:
        return "物理类"
    if "历史" in raw:
        return "历史类"
    return raw


def parse_case_file(md_path: Path) -> dict | None:
    """读取一个标准 .md 案例文件，返回 cases.yml 条目字典。"""
    text = md_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)

    # 去除 frontmatter 后拿正文
    if text.startswith("---"):
        end = text.find("---", 4)
        content = text[end + 3:] if end != -1 else text
    else:
        content = text

    info = parse_info_items(content)

    name = info.get("化名", "")
    if not name:
        print(f"  [!] 跳过（无化名）: {md_path.relative_to(ROOT)}")
        return None

    school = info.get("录取院校", "")

    # 年份：优先用文件夹名（权威来源）
    year_dir = md_path.parent.name  # e.g. "2023", "2025", "earlier"
    if year_dir.isdigit():
        year = int(year_dir)
    else:
        # "earlier" 或其他非数字目录 → 从内容解析
        year = parse_year(info.get("毕业届数", ""))

    # 标签：优先用 frontmatter tags，确保都是 string
    tags = [str(t) for t in fm.get("tags", [])]
    if not tags:
        body_tags = re.findall(r'<span class="fy-tag[^"]*">([^<]+)</span>', content)
        tags = list(dict.fromkeys(body_tags))

    case_type = "template" if "模板案例" in tags else "real"

    # 学校等级：从 frontmatter 的 level 字段提取（985 / 211 / 一本 / 二本）
    level = str(fm.get("level", "")).strip()

    # 引用语
    quote = extract_quote(content)
    if not quote:
        quote_matches = re.findall(r'^> "?([^"\n]+)"?', content, re.MULTILINE)
        if quote_matches:
            quote = clean_quote(quote_matches[-1])

    # 文件名 -> id
    filename = md_path.stem
    case_id = filename

    # 相对路径（相对于 docs/）
    rel_path = str(md_path.relative_to(DOCS)).replace("\\", "/")

    return {
        "id": case_id,
        "name": sanitize_text(name),
        "avatar": sanitize_text(name)[0] if name else "?",
        "year": year,
        "group": sanitize_text(parse_group(info.get("选科组合", ""))),
        "school": sanitize_text(school),
        "major": sanitize_text(info.get("录取专业", "")),
        "score": parse_number(info.get("高考分数", "")),
        "rank": parse_number(info.get("全省位次", "")),
        "city": sanitize_text(info.get("所在城市", "")),
        "type": case_type,
        "tags": [sanitize_text(t) for t in tags],
        "level": level,
        "quote": quote,
        "file": rel_path,
    }


# ================================================================
# 2. 扫描所有案例
# ================================================================
def scan_cases() -> list:
    """扫描 docs/cases/**/*.md，返回所有案例条目列表（按年份倒序）。"""
    cases = []
    for md_file in sorted(CASES_DIR.rglob("*.md")):
        if md_file.name == "index.md":
            continue
        print(f"  解析: {md_file.relative_to(ROOT)}")
        entry = parse_case_file(md_file)
        if entry:
            cases.append(entry)
        else:
            print(f"    [!] 解析失败，跳过")

    cases.sort(key=lambda c: (-c["year"], c["id"]))
    return cases


# ================================================================
# 3. 大学自动分类
# ================================================================
def slugify(text: str) -> str:
    """生成 URL 安全的 slug。"""
    s = re.sub(r"[^\w一-龥]+", "-", text).strip("-").lower()
    return s or "school"


def classify_universities(cases: list) -> list:
    """根据案例数据自动生成大学分类列表。"""
    schools = defaultdict(list)
    for c in cases:
        if c["school"]:
            schools[c["school"]].append(c)

    cats = {
        "985 院校": [],
        "211 / 双一流 院校": [],
        "一本院校": [],
        "二本院校": [],
        "港澳及海外院校": [],
        "其他院校": [],
    }

    # 港澳/海外 关键词
    OVERSEAS_CITY_KEYWORDS = ("香港", "澳门", "海外", "墨尔本", "悉尼", "伦敦", "纽约", "东京", "新加坡")
    OVERSEAS_SCHOOL_KEYWORDS = ("香港", "澳门", "海外")

    # level 字段到分类名的映射（兼容复合值如 211/双一流）
    def _resolve_level(raw: str) -> str:
        if not raw:
            return ""
        r = raw.strip()
        if "985" in r:
            return "985 院校"
        if "211" in r:
            return "211 / 双一流 院校"
        if "港澳" in r or "海外" in r:
            return "港澳及海外院校"
        if "一本" in r:
            return "一本院校"
        if "二本" in r:
            return "二本院校"
        return ""

    for school_name, school_cases in schools.items():
        all_tags = set()
        all_cities = set()
        # 收集该学校第一个有效的 level
        school_level = ""
        for c in school_cases:
            all_tags.update(c["tags"])
            if c.get("city"):
                all_cities.add(c["city"])
            if not school_level and c.get("level", "").strip():
                school_level = c["level"].strip()

        def _has_overseas_signal() -> bool:
            """检查标签/学校名/城市是否含港澳或海外信号。"""
            for t in all_tags:
                if any(kw in t for kw in ("港澳", "海外")):
                    return True
            for kw in OVERSEAS_SCHOOL_KEYWORDS:
                if kw in school_name:
                    return True
            for city in all_cities:
                for kw in OVERSEAS_CITY_KEYWORDS:
                    if kw in city:
                        return True
            return False

        # 分类：优先用 frontmatter level，其次海外信号，最后标签兜底
        resolved = _resolve_level(school_level)
        if resolved:
            cats[resolved].append(school_name)
        elif _has_overseas_signal():
            cats["港澳及海外院校"].append(school_name)
        elif any("985" in t for t in all_tags):
            cats["985 院校"].append(school_name)
        elif any("211" in t for t in all_tags):
            cats["211 / 双一流 院校"].append(school_name)
        elif any("一本" in t for t in all_tags):
            cats["一本院校"].append(school_name)
        elif any("二本" in t for t in all_tags):
            cats["二本院校"].append(school_name)
        else:
            cats["其他院校"].append(school_name)

    result = []
    for cat_name, school_list in cats.items():
        entries = []
        for s in sorted(school_list):
            count = len(schools[s])
            if count >= 2:
                entries.append({"name": s, "slug": slugify(s)})
            else:
                entries.append(s)
        result.append({"category": cat_name, "schools": entries})

    return result


# ================================================================
# 4. 生成 data/cases.yml
# ================================================================
def yaml_str(s: str) -> str:
    """安全输出 YAML 字符串值。"""
    # 如果包含特殊字符，用双引号包裹
    s_escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s_escaped}"'


def generate_cases_yml(cases: list, universities: list) -> str:
    """生成完整的 data/cases.yml 文件内容。"""
    lines = []
    lines.append("# ============================================================")
    lines.append("# 州民中飞跃手册 - 案例与大学元数据")
    lines.append("# 此文件由 scripts/sync.py 自动生成，请勿手动编辑。")
    lines.append("# 新增案例请直接在 docs/cases/ 下添加标准 .md 文件，")
    lines.append("# 然后运行: python scripts/sync.py")
    lines.append("# ============================================================")
    lines.append("")
    lines.append("cases:")

    for c in cases:
        lines.append(f'  - id: {yaml_str(c["id"])}')
        lines.append(f'    name: {yaml_str(c["name"])}')
        lines.append(f'    avatar: {yaml_str(c["avatar"])}')
        lines.append(f"    year: {c['year']}")
        lines.append(f'    group: {yaml_str(c["group"])}')
        lines.append(f'    school: {yaml_str(c["school"])}')
        lines.append(f'    major: {yaml_str(c["major"])}')
        lines.append(f"    score: {c['score']}")
        lines.append(f"    rank: {c['rank']}")
        lines.append(f'    city: {yaml_str(c["city"])}')
        lines.append(f'    type: {c["type"]}')
        if c.get("level"):
            lines.append(f'    level: {yaml_str(c["level"])}')
        tags_str = ", ".join(yaml_str(t) for t in c["tags"])
        lines.append(f"    tags: [{tags_str}]")
        lines.append(f'    quote: {yaml_str(c["quote"])}')
        lines.append(f'    file: {c["file"]}')
        lines.append("")

    lines.append("")
    lines.append("# ============================================================")
    lines.append("# 大学分类 - 由 sync.py 自动分类")
    lines.append("# 如需添加暂无案例的期待学校，请编辑下方对应 category 的 schools 列表。")
    lines.append("# ============================================================")
    lines.append("universities:")

    for cat in universities:
        lines.append(f'  - category: {yaml_str(cat["category"])}')
        if cat["schools"]:
            lines.append("    schools:")
            for s in cat["schools"]:
                if isinstance(s, dict):
                    lines.append(f'      - name: {yaml_str(s["name"])}')
                    lines.append(f'        slug: {yaml_str(s["slug"])}')
                else:
                    lines.append(f'      - {yaml_str(s)}')
        else:
            lines.append("    schools: []")

    return "\n".join(lines) + "\n"


# ================================================================
# 5. 校验
# ================================================================
def validate(cases: list) -> bool:
    """双向校验：YAML <-> 实际文件 一致性。"""
    yaml_files = {c["file"] for c in cases}

    actual_files = set()
    for md_file in CASES_DIR.rglob("*.md"):
        if md_file.name == "index.md":
            continue
        rel = str(md_file.relative_to(DOCS)).replace("\\", "/")
        actual_files.add(rel)

    missing_in_yaml = actual_files - yaml_files
    missing_on_disk = yaml_files - actual_files

    ok = True
    if missing_in_yaml:
        print("[!] 以下 .md 文件未被识别（可能格式不标准）：")
        for f in sorted(missing_in_yaml):
            print(f"    - {f}")
        print()
        ok = False

    if missing_on_disk:
        print("[!] YAML 中有以下条目指向不存在的文件：")
        for f in sorted(missing_on_disk):
            print(f"    - {f}")
        print()
        ok = False

    required_fields = ["name", "school", "year"]
    for c in cases:
        missing = [k for k in required_fields if not c.get(k)]
        if missing:
            print(f"[!] 案例 '{c.get('id', '?')}' 缺少必填字段: {', '.join(missing)}")
            ok = False

    return ok


# ================================================================
# 6. 主流程
# ================================================================
def main() -> int:
    print("州民中飞跃手册 - 一键同步\n")
    print("=" * 60)

    # [1/5] 扫描 .md 文件
    print("\n[1/5] 扫描案例文件...")
    cases = scan_cases()
    print(f"\n  共发现 {len(cases)} 个案例")

    # [2/5] 大学自动分类
    print("\n[2/5] 大学自动分类...")
    universities = classify_universities(cases)
    for cat in universities:
        print(f"  {cat['category']}: {len(cat['schools'])} 所")

    # [3/5] 生成 cases.yml
    print("\n[3/5] 生成 data/cases.yml...")
    yml_content = generate_cases_yml(cases, universities)
    DATA_FILE.write_text(yml_content, encoding="utf-8")
    print(f"  [OK] 已写入: {DATA_FILE.relative_to(ROOT)}")

    # [4/5] 校验
    print("\n[4/5] 数据校验...")
    all_ok = validate(cases)

    # [5/5] 运行卡片生成
    print("\n[5/5] 更新页面卡片...\n")
    generate_script = ROOT / "scripts" / "generate.py"
    result = subprocess.run(
        [sys.executable, str(generate_script)],
        cwd=str(ROOT),
    )

    if result.returncode != 0:
        print("\n!! 卡片生成失败，请检查错误信息")
        return 1

    if all_ok:
        print("\n==> 全部完成！")
        print(f"   案例总数: {len(cases)}")
        total_schools = sum(len(cat["schools"]) for cat in universities)
        print(f"   大学总数: {total_schools}")
        print(f"\n   下一步: git add -A && git commit && git push")
    else:
        print("\n!! 完成但有警告，请检查上述提示")

    return 0


if __name__ == "__main__":
    sys.exit(main())
