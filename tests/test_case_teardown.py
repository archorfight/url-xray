"""Tests for case_teardown package."""

import pytest
from case_teardown.fetcher import detect_type, _is_spa, extract_source_name
from case_teardown.llm import get_prompts, call_llm
from case_teardown.analyzer import teardown, save_report


class TestDetectType:
    """URL type detection tests."""

    def test_website(self):
        assert detect_type("https://example.com") == "website"
        assert detect_type("https://ideafactorys.com/") == "website"

    def test_wechat_article(self):
        assert detect_type("https://mp.weixin.qq.com/s/abc123") == "article"

    def test_feishu_wiki(self):
        assert detect_type("https://waytoagi.feishu.cn/wiki/test") == "article"

    def test_zhihu(self):
        assert detect_type("https://zhuanlan.zhihu.com/p/123") == "article"

    def test_github(self):
        assert detect_type("https://github.com/user/repo") == "github"

    def test_producthunt(self):
        assert detect_type("https://www.producthunt.com/posts/foo") == "product"

    def test_xiaohongshu(self):
        assert detect_type("https://www.xiaohongshu.com/explore/abc") == "article"

    def test_adds_https(self):
        """detect_type should not crash on URLs without scheme."""
        # detect_type itself doesn't add scheme, but shouldn't crash
        result = detect_type("example.com")
        assert result in ("website",)


class TestSpaDetection:
    """SPA detection tests."""

    def test_spa_nextjs(self):
        html = '<html><body><div id="__NEXT_DATA__"></div></body></html>'
        assert _is_spa(html) is True

    def test_spa_react_root(self):
        html = '<html><body><div id="root"></div></body></html>'
        assert _is_spa(html) is True

    def test_not_spa(self):
        html = '<html><body><h1>Hello World</h1><p>This is a real page with lots of text content that exceeds the threshold for SPA detection.</p></body></html>'
        assert _is_spa(html) is False


class TestSourceName:
    """Source name extraction tests."""

    def test_wechat(self):
        assert extract_source_name("https://mp.weixin.qq.com/s/abc") == "微信公众号"

    def test_feishu(self):
        assert extract_source_name("https://waytoagi.feishu.cn/wiki/test") == "通往AGI"

    def test_zhihu(self):
        assert extract_source_name("https://zhuanlan.zhihu.com/p/123") == "知乎"

    def test_unknown(self):
        assert extract_source_name("https://random-site.com/page") == "random-site.com"


class TestPrompts:
    """Prompt template tests."""

    def test_chinese_prompts_exist(self):
        prompts = get_prompts("zh")
        for t in ["website", "article", "product", "github"]:
            assert t in prompts
            assert len(prompts[t]) > 100

    def test_english_prompts_exist(self):
        prompts = get_prompts("en")
        for t in ["website", "article", "product", "github"]:
            assert t in prompts
            assert len(prompts[t]) > 100

    def test_default_is_chinese(self):
        zh = get_prompts("zh")
        default = get_prompts()
        assert zh["website"] == default["website"]

    def test_prompts_differ_by_language(self):
        zh = get_prompts("zh")["website"]
        en = get_prompts("en")["website"]
        assert zh != en


class TestSaveReport:
    """Report saving tests."""

    def test_save_creates_file(self, tmp_path):
        result = {
            "url": "https://example.com",
            "type": "website",
            "report": "# Test Report\n\ncontent",
        }
        path = save_report(result, str(tmp_path))
        assert path.endswith(".md")
        with open(path) as f:
            content = f.read()
            assert "Test Report" in content
            assert "https://example.com" in content

    def test_save_different_types(self, tmp_path):
        for url_type in ["website", "article", "product", "github"]:
            result = {
                "url": f"https://example.com/{url_type}",
                "type": url_type,
                "report": "# Test",
            }
            path = save_report(result, str(tmp_path))
            assert path.endswith(".md")
