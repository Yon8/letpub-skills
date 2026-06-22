# LetPub Skills

LetPub 期刊数据爬取工具，提供三大核心能力：

1. **查询期刊详情** —— 输入期刊名称，返回完整详情（影响因子、分区、审稿速度等）
2. **分析期刊评论** —— 输入期刊名称，自动翻页去重，综合评判该期刊
3. **推荐投稿期刊** —— 根据论文摘要，由 AI 智能调用搜索接口推荐合适期刊

---

## 快速开始

### 安装依赖

```bash
pip install requests beautifulsoup4
```

### 配置账号（可选，评论功能需要）

在 `assets/credentials.json` 中填入 LetPub 账号密码：

```json
{
  "email": "your@email.com",
  "password": "your_password"
}
```

> 脚本已支持自动登录续期，配置一次即可，无需手动维护 cookies。

---

## 功能演示

### 功能 1：查询期刊详情

```python
from scripts.search_journal import search_journal
from scripts.get_details import get_journal_detail

# 搜索拿到 journal_id
results = search_journal("CHEMICAL ENGINEERING SCIENCE")
journal_id = results[0]['id']

# 一步获取详情（请求 + 解析）
journal = get_journal_detail(journal_id)

print(journal['impact_factor'])          # 影响因子
print(journal['ch_sci_2025']['分区'])     # 中科院分区
print(journal['speed'])                  # 审稿速度
print(journal['similar_journals'])       # 同类著名期刊
```

### 功能 2：分析期刊评论

```python
from scripts.search_journal import search_journal
from scripts.get_comments import fetch_all_comments

results = search_journal("CHEMICAL ENGINEERING SCIENCE")
journal_id = results[0]['id']

# 自动翻页、去重，至少获取 30 条评论
all_comments = fetch_all_comments(journal_id, min_count=30)

print(f"共获取 {len(all_comments)} 条评论")
for c in all_comments[:3]:
    print(f"{c['floor']} | 评分:{c['score']} | {c['experience'][:50]}...")
```

### 功能 3：高级搜索

```python
from scripts.search_journal import search_journals_advanced, parse_search_results

html = search_journals_advanced(
    searchcategory1="计算机科学",
    searchcategory2="计算机：人工智能",
    searchimpactlow="5",
    searchscitype="SCIE",
    searchsort="impactor"
)
result = parse_search_results(html)
print(f"共 {result['total_records']} 条记录")
for j in result['journals'][:5]:
    print(f"{j['name']} - IF:{j['impact_factor']} - {j['partition']}")
```

---

## 配置说明

### 自动登录机制

评论接口需要登录态（`PHPSESSID`）。脚本的处理流程：

```
调用 get_journal_comments() / fetch_all_comments()
        ↓
检测响应：count > 1 但只返回 1 条数据？
        │
  是（cookie 已过期）
        ↓
ensure_logged_in(force=True)
读取 credentials.json → 自动重新登录 → 更新 cookies.json
        ↓
用新 cookie 重试一次
```

**手动触发登录：**

```python
from scripts.login import auto_login, load_credentials

email, password = load_credentials()
cookies = auto_login(email, password)
print(cookies)  # PHPSESSID=xxx
```

### 评论中常见投稿流程缩写

| 缩写 | 全称 | 含义 |
|------|------|------|
| STJ | Submit to Journal | 刚投递，待初审 |
| WE | With Editor | 编辑处理中 |
| UR | Under Review | 外审审稿中（X-Y-Z = 邀约-接受-返稿数）|
| RRC | Required Reviews Completed | 审稿意见收齐，等待终审 |

> 注：单独出现 `WE` / `with editor` 是正常流程，不代表负面；`一直with editor` / `WE很久` 才是慢审信号。

---

## 目录结构

```
letpub-skills/
├── SKILL.md                    # AI 操作手册（详细提示词与字段说明）
├── README.md                   # 本文件
├── assets/
│   ├── credentials.json        # 账号密码（用户填写）
│   └── cookies.json            # 登录 cookies（自动生成）
├── scripts/
│   ├── login.py                # 自动登录与 cookie 续期
│   ├── search_journal.py       # 期刊搜索（自动补全 + 高级搜索）
│   ├── get_details.py          # 期刊详情解析
│   └── get_comments.py         # 评论获取与解析（自动续期）
└── references/
    ├── search_journal.md       # 搜索参数与完整学科分类数据
    ├── get_journal_detail.md   # 详情字段说明
    └── get_journal_comments.md # 评论字段说明
```

---

## API 参考

| 模块 | 函数 | 说明 |
|------|------|------|
| `login` | `load_credentials()` | 从 credentials.json 读取账号密码 |
| `login` | `auto_login(email, password)` | 登录并保存 cookies |
| `login` | `ensure_logged_in(force=False)` | 检查 cookie 有效性，失效时自动续期 |
| `search_journal` | `search_journal(name)` | 自动补全搜索，返回 journal_id |
| `search_journal` | `search_journals_advanced(**params)` | 高级多条件搜索 |
| `search_journal` | `parse_search_results(html)` | 解析搜索结果页 |
| `get_details` | `get_journal_detail(journal_id)` | 一步获取并解析期刊详情 |
| `get_details` | `parse_journal_detail(html)` | 解析期刊详情 HTML |
| `get_comments` | `fetch_all_comments(journal_id, min_count)` | 自动翻页去重抓取评论 |
| `get_comments` | `get_journal_comments(journal_id, page)` | 获取单页评论（自动续期） |
| `get_comments` | `parse_comments_response(data)` | 解析评论列表 |

---

## Changelog

### v0.2.0

LetPub 评论按分页返回，默认每页约 10 条。程序会自动翻页，直到无新评论为止。如果期刊评论较少，可能不足 5 页。

**新增**
- `scripts/login.py`：自动登录模块，支持从 `credentials.json` 读取账号、自动续期 cookie
- `assets/credentials.json`：账号密码配置文件
- `fetch_all_comments()`：自动翻页 + 按 floor 去重 + cookie 失效自动续期
- `get_journal_detail()`：一步到位获取并解析期刊详情

**改进**
- `get_journal_comments()` 新增 cookie 过期检测（count > 1 但仅返回 1 条）并自动触发重新登录
- SKILL.md 更新：示例代码改用新便利函数，cookie 失效说明同步更新

### v0.1.0

- 初始版本：期刊自动补全搜索、高级搜索、详情解析、评论获取与解析

## 社区

有问题、建议，或想一起折腾？欢迎来 **[linux.do](https://linux.do)** 社区交流反馈。
