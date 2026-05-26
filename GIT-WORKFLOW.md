# Git 维护手册

## 分支说明

| 分支 | 用途 |
|------|------|
| `main` | 线上版本，GitHub Pages 自动部署。**禁止直接 push**（受保护） |
| `dev` | 日常开发。所有修改在此进行 |

---

## Admin（项目负责人）

### 日常开发

```bash
git checkout dev
git pull origin dev
# ... 做修改 ...
git add <文件>
git commit -m "类型: 描述"
git push
```

### 上线部署

```bash
git checkout main
git pull origin main
git merge dev
git push origin main
git checkout dev
```

### 提交信息规范

```
feat: 新增功能
fix: 修复 bug
docs: 文档修改
refactor: 代码重构
chore: 配置/杂项
```

---

## Collaborator（协作者）

### 首次

1. Fork 仓库
2. Clone 你的 fork 到本地
3. `git remote add upstream https://github.com/AndrewLong7/zhouminzhong-feiyue.git`

### 每次开发

```bash
git checkout dev
git fetch upstream
git merge upstream/dev
# ... 做修改 ...
git add <文件>
git commit -m "描述修改"
git push origin dev
```

### 提交 PR

1. 在 GitHub 上从你的 fork 的 `dev` 分支创建 Pull Request
2. base 选主仓库的 `dev`，compare 选你 fork 的 `dev`
3. 填写说明，提交

### 案例投稿流程

1. 在 `docs/cases/` 对应年份下新建 `.md` 文件
2. 在 `data/cases.yml` 添加元数据
3. 运行 `python scripts/generate.py`
4. 提交 PR

---

## 两条铁律

1. **永远不要在 main 上直接修改** — 所有改动走 dev
2. **新增案例必须同时改 .md 和 .yml** — 运行 `generate.py` 校验通过后再提交
