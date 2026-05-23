# 州民中飞跃手册

> 来自学长学姐的真实经验，写给正在寻找方向的后来者。

[![Built with MkDocs](https://img.shields.io/badge/MkDocs-Material-0D9488?style=flat&logo=materialformkdocs)](https://squidfunk.github.io/mkdocs-material/)
[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-222?style=flat&logo=github)](https://pages.github.com/)

**🌐 网站入口：[andrewlong7.github.io/zhouminzhong-feiyue](https://andrewlong7.github.io/zhouminzhong-feiyue/)**

## 关于本项目

**州民中飞跃手册** 是一个由湘西州民族中学校友自发创建的公益性经验分享网站。

我们汇集历届高考毕业生的真实案例——包括高考成绩、录取学校、专业选择、志愿填报思路以及大学学习体验，希望为在校学弟学妹提供更真实、更具体的升学参考。

### 我们的信念

> **信息差不应该成为限制学生发展的门槛。**

对于很多来自湘西地区的学生而言，缺少经验、缺少交流渠道、缺少对大学与专业的真实认知，往往比"努力"本身更容易影响未来的选择。

## 技术栈

- **[MkDocs](https://www.mkdocs.org/)** — 静态网站生成器
- **[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)** — 现代化主题
- **[GitHub Pages](https://pages.github.com/)** — 免费托管与自动部署

无后端，无数据库，纯静态网站。易于维护，适合开源协作。

## 本地运行

### 环境要求

- Python 3.9+
- pip

### 安装与启动

```bash
# 1. 安装 MkDocs Material
pip install mkdocs-material

# 2. 进入项目目录
cd zhouminzhong-feiyue

# 3. 启动本地预览
mkdocs serve
```

浏览器访问 `http://127.0.0.1:8000` 查看网站。

### 构建静态文件

```bash
mkdocs build
```

生成的静态文件在 `site/` 目录中，可直接部署到任何静态托管服务。

## 项目结构

```
zhouminzhong-feiyue/
├── mkdocs.yml                  # MkDocs 配置文件
├── README.md                   # 项目说明
├── docs/                       # 网站内容（Markdown）
│   ├── index.md                # 首页
│   ├── about.md                # 关于我们
│   ├── contribute.md           # 投稿指南
│   ├── cases/                  # 案例库
│   │   ├── index.md            # 案例总览
│   │   ├── 2025/               # 2025 届案例
│   │   ├── 2024/               # 2024 届案例
│   │   ├── 2023/               # 2023 届案例
│   │   └── earlier/            # 更早的案例
│   ├── universities/           # 大学分类
│   │   └── index.md            # 大学分类总览
│   ├── assets/                 # 静态资源
│   │   └── images/             # 图片
│   ├── stylesheets/            # 自定义样式
│   │   └── extra.css
│   └── overrides/              # 主题模板覆盖
└── site/                       # 构建输出（由 mkdocs build 生成）
```

## 投稿方式

### 方式一：邮箱投稿
发送邮件至 **u3638259@connect.hku.hk**，主题格式：`[投稿] 你的化名 - 录取院校`

### 方式二：GitHub PR
1. Fork 本仓库
2. 在 `docs/cases/` 对应年份文件夹中新建 `.md` 文件
3. 参考[投稿模板](https://andrewlong7.github.io/zhouminzhong-feiyue/contribute/)填写
4. 提交 Pull Request

详见 [投稿指南](https://andrewlong7.github.io/zhouminzhong-feiyue/contribute/)

## 致谢

- 感谢每一位分享经验的校友
- 感谢深圳大学飞跃手册等前辈项目的灵感
- 感谢 Material for MkDocs 团队

## 许可证

本项目内容采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 许可。

## 联系方式

- 📧 邮箱：u3638259@connect.hku.hk
- 👤 联系人：龙熙予
