"""LLM client — works with any OpenAI-compatible API."""

import json
import httpx

# ============ Chinese Prompts ============
PROMPTS_ZH = {
    "website": """你是专业的网站分析师。以下是网站「{title}」的技术数据和页面内容。

技术数据:
{tech_info}

页面内容 (前3000字):
{content}

请输出Markdown格式的分析报告，包含以下部分（用 --- 分隔）:

## 一句话结论
（20字以内定性判断）

## 基础情报
（表格：域名注册时间、CDN、后端框架、页面体积、图片数、外链数）

## 内容审计
（标称内容数量 vs 实际内容质量。内容是原创还是抓取？更新频率？）

## 商业模式
（有无定价/登录/付费功能。核心变现路径是什么？走通了吗？）

## SEO评估
（页面数、结构化数据、meta标签、外链情况。预计有无自然搜索流量？）

## 竞争力评分
（1-10分，给5个维度各打分：内容厚度/技术质量/商业闭环/SEO基础/更新活跃度。给出总分。）

## 可借鉴点
分两类:
- 可以偷的思路: ...
- 不要犯的错: ...
""",

    "article": """你是爆款内容分析师。以下是来自「{source}」的一篇文章/帖子。

标题: {title}

全文 (前5000字):
{content}

请输出Markdown格式的拆解报告:

## 一句话结论
（这篇内容为什么能火/为什么不会火）

## 选题分析
- 选题类型: (教程/事件/观点/故事/盘点/痛点)
- 选题大小: 大选题还是小切口
- 目标受众: 写给谁看的
- 时机: 为什么是现在

## 结构拆解
逆向出文章骨架:
- 标题技巧: (数字/反常识/痛点/好奇心/权威背书)
- 开头hook: 前3句怎么抓住注意力
- 主体结构: 分几层，每层什么功能
- 结尾: 怎么收
- 节奏: 长短句、段落密度、信息密度

## 双价值检查
- 实用价值: 读者学到了什么可操作的东西？
- 情绪价值: 读者看完什么感受？
- 如果两个都弱 → 扑街原因

## 传播因子
- 社交货币: 转发让人觉得你怎样
- 触发词: 有没有让人想讨论的点
- 实用转发性: 值不值得收藏/转发
- 情绪强度: 高唤醒 > 低唤醒

## 可模仿点
如果我来写这个选题:
- 怎么差异化
- 我的优势是什么
- 3个标题备选
""",

    "product": """你是产品转化率专家。以下是「{title}」的产品/落地页。

页面内容 (前5000字):
{content}

请输出Markdown格式的拆解报告:

## 一句话结论
（这个落地页的转化做得怎么样）

## 定位分析
- 一句话定位: 产品怎么描述自己的
- 目标用户: 为谁解决什么问题
- 差异化: vs竞品怎么说的

## 转化元素清单
逐一检查:
- [ ] Hero section: 标题+副标题+CTA
- [ ] 社会认证: 用户数/logo墙/评价
- [ ] 功能展示: 截图/视频/demo
- [ ] 定价: 免费/付费分界
- [ ] FAQ: 打消顾虑
- [ ] 最终CTA

## 文案质量
- 标题: 利益导向还是功能导向
- 副标题: 是否清楚解释了做什么
- CTA按钮: 是否有行动力

## 可借鉴点
哪些元素值得偷，哪些是败笔
""",

    "github": """你是开源项目评估专家。以下是GitHub项目「{title}」的信息。

项目信息:
{tech_info}

README (前3000字):
{content}

请输出Markdown格式的评估报告:

## 一句话结论
（这个项目值得关注吗）

## 项目概况
- Stars/Forks/活跃度
- 做什么的: 一句话
- 技术栈: 语言+框架
- License

## 商业潜力
- 是library/CLI/完整产品？
- 能产品化吗？
- 竞品有哪些？

## 可借鉴点
技术方案/产品思路/社区运营
""",
}

# ============ English Prompts ============
PROMPTS_EN = {
    "website": """You are a professional website analyst. Below is technical data and page content for "{title}".

Technical data:
{tech_info}

Page content (first 3000 chars):
{content}

Output a Markdown analysis report with these sections (separated by ---):

## One-Line Verdict
(A definitive judgment in under 15 words)

## Basic Info
(Table: domain registration date, CDN, backend framework, page size, image count, external link count)

## Content Audit
(Claimed content quantity vs actual quality. Original or scraped? Update frequency?)

## Business Model
(Pricing/login/payment features. What's the monetization path? Does it work end-to-end?)

## SEO Assessment
(Page count, structured data, meta tags, backlinks. Expected organic search traffic?)

## Competitive Score
(1-10 across 5 dimensions: content depth / tech quality / business loop / SEO / activity. Give total.)

## Takeaways
Two categories:
- Ideas worth stealing: ...
- Mistakes to avoid: ...
""",

    "article": """You are a viral content analyst. Below is an article/post from "{source}".

Title: {title}

Full text (first 5000 chars):
{content}

Output a Markdown teardown report:

## One-Line Verdict
(Why this content will or won't go viral)

## Topic Analysis
- Topic type: (tutorial / news / opinion / story / listicle / pain-point)
- Scope: macro topic or niche angle
- Target audience: who is this for
- Timing: why now

## Structure Teardown
Reverse-engineer the article skeleton:
- Title technique: (number / contrarian / pain-point / curiosity / authority)
- Opening hook: how the first 3 sentences grab attention
- Body structure: how many layers, what each layer does
- Ending: how it wraps up
- Pacing: sentence variety, paragraph density, information density

## Dual Value Check
- Practical value: what actionable thing did the reader learn?
- Emotional value: how does the reader feel after reading?
- If both are weak → why it flopped

## Virality Factors
- Social currency: sharing this makes you look how
- Triggers: is there a point that makes people want to discuss
- Shareability: worth bookmarking/forwarding
- Emotional intensity: high arousal > low arousal

## How to Adapt
If I were to write on this topic:
- How to differentiate
- What's my unique advantage
- 3 alternative title ideas
""",

    "product": """You are a conversion rate expert. Below is the product/landing page for "{title}".

Page content (first 5000 chars):
{content}

Output a Markdown teardown report:

## One-Line Verdict
(How good is this landing page's conversion design)

## Positioning Analysis
- One-liner: how the product describes itself
- Target user: who needs this, what problem
- Differentiation: how it positions vs competitors

## Conversion Element Checklist
Check each:
- [ ] Hero section: headline + subheadline + CTA
- [ ] Social proof: user count / logo wall / testimonials
- [ ] Feature showcase: screenshots / video / demo
- [ ] Pricing: free/paid boundary
- [ ] FAQ: objection handling
- [ ] Final CTA

## Copy Quality
- Headline: benefit-driven or feature-driven
- Subheadline: does it clearly explain what it does
- CTA button: does it drive action

## Takeaways
Which elements are worth stealing, which are misses
""",

    "github": """You are an open source project evaluator. Below is info for the GitHub project "{title}".

Project info:
{tech_info}

README (first 3000 chars):
{content}

Output a Markdown evaluation report:

## One-Line Verdict
(Is this project worth attention)

## Project Overview
- Stars/Forks/activity
- What it does: one sentence
- Tech stack: language + framework
- License

## Commercial Potential
- Is it a library / CLI / full product?
- Can it be productized?
- What are the alternatives?

## Takeaways
Tech approach / product insight / community strategy
""",
}

# Backwards-compatible default (Chinese)
PROMPTS = PROMPTS_ZH


def get_prompts(lang: str = "zh"):
    """Return prompt templates for the given language."""
    if lang == "en":
        return PROMPTS_EN
    return PROMPTS_ZH


def call_llm(
    prompt: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o",
    timeout: int = 90,
) -> str:
    """Call any OpenAI-compatible API and return the response text."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 3000,
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
