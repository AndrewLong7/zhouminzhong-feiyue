"""州民中飞跃手册 - 问卷 xlsx → 案例 Markdown 转换脚本

将问卷导出的 xlsx 表格转换为符合本站规范的案例 Markdown 文件
（格式参考 docs/cases/earlier/adj-hitsz.md）。

运行方式:
    python3 scripts/xlsx_to_md.py <xlsx_path> [-o <output_dir>]

示例:
    python3 scripts/xlsx_to_md.py /Users/xxx/Downloads/365943323_1_1.xlsx
    python3 scripts/xlsx_to_md.py xxx.xlsx -o docs/cases/2026

依赖:
    python3 -m pip install openpyxl
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import openpyxl


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "cases" / "earlier"


# ============================================================
# 列索引（基于问卷模板 365943323_1_1.xlsx，1-based）
# ============================================================
COL = {
    "alias": 7,            # 化名
    "school": 8,           # 学校
    "school_type": 9,      # 学校属于（985/211/...）
    "region": 10,          # 城市所在地
    "major": 11,           # 专业
    "graduate_year": 12,   # 高中毕业届数
    "exam_track": 13,      # 高考科目（物理类/历史类）
    "exam_score": 14,      # 高考分数
    "exam_rank": 15,       # 高考排位
    "contact": 16,         # 联系方式（选填）
    "reason": 17,          # 我为什么选择这个学校/专业
    "destination": 18,     # 学校应届生去向
    "study": 19,           # 学业压力
    "atmosphere": 20,      # 校园氛围
    "dorm": 21,            # 住宿与生活
    "resources": 22,       # 资源与机会
    "social": 23,          # 社交与成长
    "city": 24,            # 城市感受
    "pits": 25,            # 我踩过的坑
    "message": 26,         # 写给后来者的一句话
    "tags": 27,            # 标签
}

# 多值字段分隔符（问卷工具默认）
MULTI_SEP = "┋"


# ============================================================
# 工具函数
# ============================================================
def cell(row: tuple, idx: int) -> str:
    """读取 1-based 列，并转字符串、去空白。"""
    if idx - 1 >= len(row):
        return ""
    val = row[idx - 1]
    if val is None:
        return ""
    return str(val).strip()


def parse_graduate_year(raw: str) -> str:
    """'其他：〖20〗' / '2020' / '20届' → '20 届'。"""
    if not raw:
        return ""
    m = re.search(r"〖\s*(\d+)\s*〗", raw)
    if m:
        return f"{m.group(1)} 届"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"{m.group(1)} 届"
    return raw


def parse_pits(raw: str) -> list[str]:
    """'1.〖坑1〗┋2.〖坑2〗' → ['坑1', '坑2']。"""
    if not raw:
        return []
    items = []
    for chunk in raw.split(MULTI_SEP):
        chunk = chunk.strip()
        if not chunk:
            continue
        # 去掉前导编号 "1." / "2、"
        chunk = re.sub(r"^\d+\s*[\.\、]\s*", "", chunk)
        # 去掉外层「〖〗」「" "」"" "" 等
        m = re.match(r"〖\s*(.+?)\s*〗\s*$", chunk)
        if m:
            chunk = m.group(1)
        items.append(chunk.strip())
    return items


def parse_tags(raw: str) -> list[str]:
    """'工科┋跨省' → ['工科', '跨省']。"""
    if not raw:
        return []
    return [t.strip() for t in raw.split(MULTI_SEP) if t.strip()]


def slugify(name: str) -> str:
    """生成文件名安全 slug：保留中英文数字，其他字符替换为 -。"""
    s = re.sub(r"[^\w\u4e00-\u9fa5]+", "-", name).strip("-")
    return s or "case"


def safe_name(name: str) -> str:
    """文件名清洗：保留原始字符（包括中文括号等），仅替换文件系统不允许的字符。"""
    if not name:
        return ""
    s = name.strip()
    # macOS/Linux 禁用 /；Windows 额外禁用 \ : * ? " < > |
    trans = {
        '/': '／',   # 全角斜杠
        '\\': '＼',  # 全角反斜杠
        ':': '：',
        '*': '＊',
        '?': '？',
        '"': '”',
        '<': '＜',
        '>': '＞',
        '|': '｜',
        '\0': '',
    }
    for k, v in trans.items():
        s = s.replace(k, v)
    # 合并连续空白
    s = re.sub(r"\s+", " ", s).strip()
    return s


def yaml_escape(s: str) -> str:
    """frontmatter 中字符串转义（含冒号、引号时加引号）。"""
    if any(c in s for c in [":", "#", "\"", "'"]):
        return '"{}"'.format(s.replace('"', '\\"'))
    return s


# ============================================================
# Markdown 渲染
# ============================================================
def build_frontmatter(alias: str, school: str, tags: list[str]) -> str:
    title = f"{alias} - {school}" if school else alias
    lines = [
        "---",
        f"title: {yaml_escape(title)}",
        "not_in_nav: true",
    ]
    if tags:
        lines.append("tags:")
        for t in tags:
            lines.append(f"  - {yaml_escape(t)}")
    lines.append("---")
    return "\n".join(lines)


def build_basic_info(d: dict[str, str]) -> str:
    """渲染「基本信息」区块。"""
    items: list[tuple[str, str]] = []
    if d.get("alias"):
        items.append(("化名", d["alias"]))
    if d.get("graduate_year"):
        items.append(("毕业届数", d["graduate_year"]))
    if d.get("exam_score"):
        items.append(("高考分数", f"{d['exam_score']} 分"))
    if d.get("exam_rank"):
        items.append(("全省位次", f"全省第 {d['exam_rank']} 名"))
    if d.get("exam_track"):
        items.append(("选科组合", d["exam_track"]))
    if d.get("school"):
        items.append(("录取院校", d["school"]))
    if d.get("major"):
        items.append(("录取专业", d["major"]))
    if d.get("region"):
        items.append(("所在城市", d["region"]))
    if d.get("contact"):
        items.append(("联系方式", d["contact"]))

    blocks = []
    for label, value in items:
        blocks.append(
            f'<div class="fy-case-info-item">\n'
            f'  <div class="fy-case-info-label">{label}</div>\n'
            f'  <div class="fy-case-info-value">{value}</div>\n'
            f'</div>'
        )
    inner = "\n\n".join(blocks)
    return (
        '<div class="fy-case-hero" markdown="1">\n\n'
        '## 基本信息\n\n'
        '<div class="fy-case-info-grid" markdown="1">\n\n'
        f'{inner}\n\n'
        '</div>\n\n'
        '</div>'
    )


def build_section(title: str, content: str) -> str:
    if not content:
        return ""
    return f"### {title}\n\n{content}"


def build_pits(pits: list[str]) -> str:
    if not pits:
        return ""
    blocks = ["## 我踩过的坑\n"]
    for i, pit in enumerate(pits, 1):
        # 第一行作为标题，其余作为正文（如有换行）
        lines = pit.splitlines()
        head = lines[0].strip() if lines else f"坑 {i}"
        body = "\n".join(lines[1:]).strip()
        block = (
            '<div class="fy-highlight-box" markdown="1">\n\n'
            f'#### ⚠️ {head}\n'
        )
        if body:
            block += f"\n{body}\n"
        block += "\n</div>"
        blocks.append(block)
    return "\n\n".join(blocks)


def build_tags_section(tags: list[str]) -> str:
    if not tags:
        return ""
    spans = "\n".join(f'<span class="fy-tag">{t}</span>' for t in tags)
    return f"## 标签\n\n{spans}"


def render_markdown(d: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append(build_frontmatter(d["alias"], d.get("school", ""), d.get("tags", [])))
    parts.append("")
    parts.append("# 我的飞跃故事")
    parts.append("")
    parts.append(build_basic_info(d))
    parts.append("")
    parts.append("---")

    if d.get("reason"):
        parts.append("")
        parts.append("## 我为什么选择这个学校/专业")
        parts.append("")
        parts.append(d["reason"])
        parts.append("")
        parts.append("---")

    # 大学真实体验
    sections = [
        ("学习压力", d.get("study", "")),
        ("校园氛围", d.get("atmosphere", "")),
        ("城市感受", d.get("city", "")),
        ("宿舍与生活", d.get("dorm", "")),
        ("资源与机会", d.get("resources", "")),
        ("社交与成长", d.get("social", "")),
    ]
    sections = [(t, c) for t, c in sections if c]
    if sections:
        parts.append("")
        parts.append("## 大学真实体验")
        for t, c in sections:
            parts.append("")
            parts.append(build_section(t, c))
        parts.append("")
        parts.append("---")

    if d.get("destination"):
        parts.append("")
        parts.append("## 应届生去向")
        parts.append("")
        parts.append(d["destination"])
        parts.append("")
        parts.append("---")

    pits_md = build_pits(d.get("pits", []))
    if pits_md:
        parts.append("")
        parts.append(pits_md)
        parts.append("")
        parts.append("---")

    if d.get("message"):
        parts.append("")
        parts.append("## 写给后来者的一句话")
        parts.append("")
        parts.append(f'> "{d["message"]}"')
        parts.append(">")
        parts.append(f"> —— {d['alias']}")
        parts.append("")
        parts.append("---")

    tags_md = build_tags_section(d.get("tags", []))
    if tags_md:
        parts.append("")
        parts.append(tags_md)

    parts.append("")
    return "\n".join(parts)


# ============================================================
# 主流程
# ============================================================
def parse_school_type_tags(raw: str) -> list[str]:
    """从「学校属于」字段抽取 985/211 标签。
    例如 '985┋双一流┋教育部直属' → ['985']
    """
    if not raw:
        return []
    result = []
    for item in raw.split(MULTI_SEP):
        item = item.strip()
        if item.startswith("985") or item.startswith("211"):
            result.append(item)
    return result


def parse_row(row: tuple) -> dict[str, Any]:
    """xlsx 一行 → 字段字典。"""
    region = cell(row, COL["region"])
    major = cell(row, COL["major"])
    school_type_raw = cell(row, COL["school_type"])
    tags = parse_tags(cell(row, COL["tags"]))

    # 追加额外标签：城市、专业、985/211
    if region and region not in tags:
        tags.append(region)
    if major and major not in tags:
        tags.append(major)
    for st in parse_school_type_tags(school_type_raw):
        if st not in tags:
            tags.append(st)

    return {
        "alias": cell(row, COL["alias"]),
        "school": cell(row, COL["school"]),
        "school_type": school_type_raw,
        "region": region,
        "major": major,
        "graduate_year": parse_graduate_year(cell(row, COL["graduate_year"])),
        "exam_track": cell(row, COL["exam_track"]),
        "exam_score": cell(row, COL["exam_score"]),
        "exam_rank": cell(row, COL["exam_rank"]),
        "contact": cell(row, COL["contact"]),
        "reason": cell(row, COL["reason"]),
        "destination": cell(row, COL["destination"]),
        "study": cell(row, COL["study"]),
        "atmosphere": cell(row, COL["atmosphere"]),
        "dorm": cell(row, COL["dorm"]),
        "resources": cell(row, COL["resources"]),
        "social": cell(row, COL["social"]),
        "city": cell(row, COL["city"]),
        "pits": parse_pits(cell(row, COL["pits"])),
        "message": cell(row, COL["message"]),
        "tags": tags,
    }


def convert(xlsx_path: Path, output_dir: Path) -> list[Path]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if idx == 1:
            continue  # 跳过标题行
        data = parse_row(row)
        if not data["alias"]:
            print(f"  [skip] 第 {idx} 行：缺少化名")
            continue
        # 文件名：化名-学校.md（学校保留单元格原始文本，仅做文件系统安全清洗）
        alias_slug = slugify(data['alias'])
        school_name = safe_name(data.get('school', ''))
        base_name = f"{alias_slug}-{school_name}" if school_name else alias_slug
        filename = f"{base_name}.md"
        out = output_dir / filename
        md = render_markdown(data)
        out.write_text(md, encoding="utf-8")
        written.append(out)
        try:
            display = out.relative_to(ROOT)
        except ValueError:
            display = out
        print(f"  [ok] 第 {idx} 行 → {display}")

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="问卷 xlsx → 案例 Markdown 转换")
    parser.add_argument("xlsx", help="输入的 xlsx 文件路径")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"输出目录（默认: {DEFAULT_OUTPUT_DIR.relative_to(ROOT)}）",
    )
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx).expanduser().resolve()
    if not xlsx_path.exists():
        print(f"错误：文件不存在 {xlsx_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).expanduser().resolve()
    print(f"输入: {xlsx_path}")
    print(f"输出: {output_dir}")
    print("-" * 60)
    written = convert(xlsx_path, output_dir)
    print("-" * 60)
    print(f"完成：共生成 {len(written)} 个 Markdown 文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
