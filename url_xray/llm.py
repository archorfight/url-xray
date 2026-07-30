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
（标称内容数量 vs 实际内容质量。内容是原创还是抓取？更新频率？交叉验证：首页标称数量 vs 实际展示条数 vs sitemap URL 数，不一致=虚标）

## 商业模式
（有无定价/登录/付费功能。核心变现路径是什么？走通了吗？注意：路由返回200不代表功能存在，可能是SPA catch-all）

## SEO评估
（canonical、结构化数据类型、meta description长度、外链情况。预计有无自然搜索流量？）

## 竞争力评分
五个维度各打0-5分。锚点：0=无，1=极差，3=及格，5=优秀。
- 内容厚度
- 技术质量
- 商业闭环
- SEO基础
- 更新活跃度

每个分数后面跟一句话理由 + 一条证据。缺关键证据标N/A，不默认给中间分。总分=加权平均，保留一位小数。

## 可借鉴点
分两类:
- 可以偷的思路: ...
- 不要犯的错: ...

---

重要：以上所有分析必须基于实际采集到的页面内容和技术数据。如果提供的"页面内容"过短（如仅有"You need to enable JavaScript"之类的提示），说明页面是SPA未渲染，你应该明确指出"页面内容不足，无法完成分析"，不要根据空白页面编造内容。
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

注意：没有传播数据时只分析"传播潜力"，不要编造"为什么爆"。

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
逐一检查（有的打✓没的打✗并说明影响）:
- [ ] Hero section: 标题+副标题+主CTA是否齐全
- [ ] 社会证明: 用户数/logo墙/评价/案例
- [ ] 功能展示: 截图/视频/demo/交互
- [ ] 定价透明度: 免费/付费分界是否清楚
- [ ] 风险逆转: 退款保证/免费试用/FAQ打消顾虑
- [ ] 最终CTA: 页面底部有没有再推一把

## 文案质量
- 标题: 利益导向还是功能导向
- 副标题: 是否一句话说清做什么
- CTA按钮: 是否有行动力（"免费开始" vs "提交"）

## 可借鉴点
哪些元素值得偷，哪些是败笔

注意：只读文字不足以评价视觉转化，如未做视觉评估请在报告中说明。
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
- Stars/Forks/Issues/Releases
- 做什么的: 一句话
- 技术栈: 主语言+框架
- License
- 最近提交时间、发布频率、贡献者数量

## 健康度评估
- 活跃度: 最近提交 vs 最后一次提交间隔
- 维护质量: issue响应速度、有无CI、有无测试、有无安全策略
- 文档质量: README是否说清安装和使用
- 交叉验证: README声称的功能 vs 仓库实际文件是否对应

## 技术与商业评估
- 类型: library/CLI/完整产品？
- 商业潜力: 能否产品化？竞品有哪些？

注意：商业潜力是推断，不能从star数直接推导。标记为推断并写明依据。

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
(Claimed content quantity vs actual quality. Original or scraped? Update frequency? Cross-validate: homepage claimed count vs displayed items vs sitemap URL count — mismatch = inflated)

## Business Model
(Pricing/login/payment features. What's the monetization path? Does it work end-to-end? Note: route returning 200 doesn't mean feature exists — could be SPA catch-all)

## SEO Assessment
(Canonical, structured data types, meta description length, backlinks. Expected organic search traffic?)

## Competitive Score
Score each dimension 0-5. Anchors: 0=none, 1=terrible, 3=adequate, 5=excellent.
- Content depth
- Tech quality
- Business loop
- SEO foundation
- Update activity

Each score must have a one-line reason + one piece of evidence. Mark N/A for missing evidence — do NOT default to a middle score. Total = weighted average, one decimal.

## Takeaways
Two categories:
- Ideas worth stealing: ...
- Mistakes to avoid: ...

---

IMPORTANT: All analysis must be based on actual page content and technical data provided above. If the "page content" is very short (e.g., only "You need to enable JavaScript"), the page is an unrendered SPA — state clearly that content is insufficient and analysis cannot be completed. Do NOT fabricate analysis from an empty page.
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

Note: Without distribution data, only analyze "virality potential" — do not fabricate "why it went viral."

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
Check each (mark ✓ present, ✗ missing with impact note):
- [ ] Hero section: headline + subheadline + main CTA
- [ ] Social proof: user count / logo wall / testimonials / case studies
- [ ] Feature showcase: screenshots / video / demo / interactive
- [ ] Pricing transparency: free/paid boundary clear
- [ ] Risk reversal: refund guarantee / free trial / FAQ objection handling
- [ ] Final CTA: bottom-of-page push

## Copy Quality
- Headline: benefit-driven or feature-driven
- Subheadline: does it clearly explain what it does
- CTA button: does it drive action ("Start free" vs "Submit")

## Takeaways
Which elements are worth stealing, which are misses

Note: Text alone can't evaluate visual conversion. State "no visual assessment" if you couldn't see the page layout.
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
- Stars/Forks/Issues/Releases
- What it does: one sentence
- Tech stack: main language + framework
- License
- Last commit date, release frequency, contributor count

## Health Assessment
- Activity: recent commit vs last commit interval
- Maintenance quality: issue response speed, CI presence, tests, security policy
- Documentation quality: does README explain installation and usage
- Cross-validation: README claims vs actual repo files

## Tech & Commercial Assessment
- Type: library / CLI / full product?
- Commercial potential: can it be productized? What alternatives exist?

Note: Commercial potential is an inference — cannot be derived directly from star count. Mark as inference with stated basis.

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
    system_message: str = None,
) -> str:
    """Call any OpenAI-compatible API and return the response text.

    If system_message is provided, it is sent as a separate {"role": "system"}
    message before the user message for prompt injection isolation (WP3).
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
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
