"""Tests for url_xray package."""

import pytest
from url_xray.fetcher import detect_type, _is_spa, extract_source_name
from url_xray.llm import get_prompts, call_llm
from url_xray.analyzer import teardown, save_report


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

    def test_save_html_format(self, tmp_path):
        result = {"url": "https://example.com", "type": "website", "report": "# Test\n\ncontent"}
        path = save_report(result, str(tmp_path), fmt="html")
        assert path.endswith(".html")
        with open(path) as f:
            content = f.read()
            assert "<html" in content
            assert "Test" in content

    def test_save_different_types(self, tmp_path):
        for url_type in ["website", "article", "product", "github"]:
            result = {
                "url": f"https://example.com/{url_type}",
                "type": url_type,
                "report": "# Test",
            }
            path = save_report(result, str(tmp_path))
            assert path.endswith(".md")


class TestThinContentDetection:
    """Thin content detection tests — SPA pages with no real content."""

    def test_thin_content_triggers_honest_report(self):
        """When body_text is too short, should NOT call LLM."""
        from unittest.mock import patch
        with patch("url_xray.analyzer.call_llm") as mock_llm, \
             patch("url_xray.analyzer.fetch_page") as mock_fetch:
            mock_fetch.return_value = {
                "url": "https://spa-site.com",
                "error": None,
                "title": "SPA Site",
                "body_text": "You need to enable JavaScript to run this app.",
                "body_text_length": 45,
                "html_size_kb": 15,
                "status_code": 200,
            }
            result = teardown(
                "https://spa-site.com",
                api_key="fake-key",
                base_url="http://localhost",
                model="fake-model",
            )
            # LLM should NOT have been called
            assert mock_llm.call_count == 0
            # Report should mention the content issue
            assert "无法生成分析报告" in result["report"] or "页面内容不足" in result["report"]
            assert "SPA" in result["report"]
            # Error should be set
            assert result["error"] is not None
            assert "too thin" in result["error"]

    def test_normal_content_does_call_llm(self):
        """When body_text is sufficient, should call LLM normally."""
        from unittest.mock import patch
        with patch("url_xray.analyzer.call_llm") as mock_llm, \
             patch("url_xray.analyzer.fetch_page") as mock_fetch, \
             patch("url_xray.analyzer.build_tech_info") as mock_tech:
            mock_fetch.return_value = {
                "url": "https://normal-site.com",
                "error": None,
                "title": "Normal Site",
                "body_text": "This is a real website with lots of content. " * 50,
                "body_text_length": 1700,
                "html_size_kb": 120,
                "status_code": 200,
                "img_count": 10,
                "link_count": 20,
                "external_links": 5,
                "h1_tags": ["Welcome"],
                "frameworks_detected": [],
                "has_jsonld": False,
            }
            mock_tech.return_value = "域名: normal-site.com\n页面体积: 120KB"
            mock_llm.return_value = "## 一句话结论\n正常的网站"
            result = teardown(
                "https://normal-site.com",
                api_key="fake-key",
                base_url="http://localhost",
                model="fake-model",
            )
            # LLM SHOULD have been called
            assert mock_llm.call_count == 1
            assert "正常的网站" in result["report"]


class TestUrlSafety:
    """URL safety validation tests."""

    def test_accepts_https(self):
        from url_xray.fetcher import validate_url
        assert validate_url("https://example.com") == "https://example.com"

    def test_accepts_http(self):
        from url_xray.fetcher import validate_url
        assert validate_url("http://example.com") == "http://example.com"

    def test_rejects_file_scheme(self):
        from url_xray.fetcher import validate_url
        with pytest.raises(ValueError):
            validate_url("file:///etc/passwd")

    def test_rejects_javascript_scheme(self):
        from url_xray.fetcher import validate_url
        with pytest.raises(ValueError):
            validate_url("javascript:alert(1)")

    def test_rejects_localhost(self):
        from url_xray.fetcher import validate_url
        with pytest.raises(ValueError):
            validate_url("http://localhost:8080")

    def test_rejects_private_ip(self):
        from url_xray.fetcher import validate_url
        with pytest.raises(ValueError):
            validate_url("http://192.168.1.1")
        with pytest.raises(ValueError):
            validate_url("http://10.0.0.1")
        with pytest.raises(ValueError):
            validate_url("http://172.16.0.1")

    def test_rejects_cloud_metadata(self):
        from url_xray.fetcher import validate_url
        with pytest.raises(ValueError):
            validate_url("http://169.254.169.254")

    def test_rejects_userinfo(self):
        from url_xray.fetcher import validate_url
        with pytest.raises(ValueError):
            validate_url("http://user:pass@example.com")


class TestTypeOverride:
    """--type override tests."""

    def test_override_to_product(self):
        """User can override auto-detected type."""
        from unittest.mock import patch
        with patch("url_xray.analyzer.call_llm") as mock_llm, \
             patch("url_xray.analyzer.fetch_page") as mock_fetch, \
             patch("url_xray.analyzer.build_tech_info") as mock_tech:
            mock_fetch.return_value = {
                "url": "https://somesaas.com",
                "error": None,
                "title": "SaaS Product",
                "body_text": "This is a SaaS landing page with lots of marketing copy. " * 30,
                "body_text_length": 1200,
                "html_size_kb": 80,
                "status_code": 200,
                "img_count": 5,
                "link_count": 10,
                "external_links": 2,
                "h1_tags": ["Best SaaS Tool"],
                "frameworks_detected": [],
                "has_jsonld": False,
            }
            mock_tech.return_value = "域名: somesaas.com"
            mock_llm.return_value = "## 一句话结论\n好的产品页"
            result = teardown(
                "https://somesaas.com",
                api_key="k",
                base_url="http://x",
                model="m",
                url_type_override="product",
            )
            assert result["type"] == "product"
            assert result["type_source"] == "override"

    def test_auto_detection_default(self):
        """Without override, uses auto detection."""
        from unittest.mock import patch
        with patch("url_xray.analyzer.call_llm") as mock_llm, \
             patch("url_xray.analyzer.fetch_page") as mock_fetch, \
             patch("url_xray.analyzer.build_tech_info") as mock_tech:
            mock_fetch.return_value = {
                "url": "https://example.com",
                "error": None,
                "title": "Example",
                "body_text": "Content here. " * 50,
                "body_text_length": 700,
                "html_size_kb": 50,
                "status_code": 200,
                "img_count": 3,
                "link_count": 8,
                "external_links": 1,
                "h1_tags": ["Welcome"],
                "frameworks_detected": [],
                "has_jsonld": False,
            }
            mock_tech.return_value = "域名: example.com"
            mock_llm.return_value = "## 一句话结论\nok"
            result = teardown(
                "https://example.com",
                api_key="k",
                base_url="http://x",
                model="m",
            )
            assert result["type"] == "website"
            assert result["type_source"] == "auto"


class TestFetchStatus:
    """Fetch status (ok/partial/failed) tests."""

    def test_normal_fetch_is_ok(self):
        from unittest.mock import patch
        with patch("url_xray.analyzer.call_llm") as mock_llm, \
             patch("url_xray.analyzer.fetch_page") as mock_fetch, \
             patch("url_xray.analyzer.build_tech_info") as mock_tech:
            mock_fetch.return_value = {
                "url": "https://ok.com", "error": None, "title": "OK",
                "body_text": "x" * 500, "body_text_length": 500,
                "html_size_kb": 50, "status_code": 200,
                "img_count": 1, "link_count": 1, "external_links": 0,
                "h1_tags": ["Hi"], "frameworks_detected": [], "has_jsonld": False,
            }
            mock_tech.return_value = "域名: ok.com"
            mock_llm.return_value = "## 一句话结论\nok"
            result = teardown("https://ok.com", "k", "http://x", "m")
            assert result["fetch_status"] == "ok"

    def test_thin_content_is_partial(self):
        from unittest.mock import patch
        with patch("url_xray.analyzer.call_llm") as ml, \
             patch("url_xray.analyzer.fetch_page") as mf:
            mf.return_value = {
                "url": "https://spa.com", "error": None, "title": "SPA",
                "body_text": "JS required", "body_text_length": 12,
                "html_size_kb": 8, "status_code": 200,
            }
            result = teardown("https://spa.com", "k", "http://x", "m")
            assert result["fetch_status"] == "partial"

    def test_github_not_thin(self):
        """GitHub type should never be thin — uses API data."""
        from unittest.mock import patch
        with patch("url_xray.analyzer.call_llm") as ml, \
             patch("url_xray.analyzer.fetch_github_info") as mf:
            mf.return_value = {
                "url": "https://github.com/u/r", "error": None, "title": "Test Repo",
                "body_text": "", "body_text_length": 0,
                "github_data": {"stars": 42, "forks": 3},
            }
            ml.return_value = "## 一句话结论\nok"
            result = teardown("https://github.com/u/r", "k", "http://x", "m")
            # Should NOT be blocked by thin content
            assert result["fetch_status"] != "partial" or "thin" not in result.get("error", "")


class TestHtmlRendererSecurity:
    """HTML renderer security tests."""

    def test_javascript_link_filtered(self):
        from url_xray.html_render import _md_to_html
        result = _md_to_html("[click](javascript:alert(1))")
        assert "javascript:" not in result

    def test_data_link_filtered(self):
        from url_xray.html_render import _md_to_html
        result = _md_to_html("[x](data:text/html,<script>)")
        assert "data:" not in result

    def test_https_link_preserved(self):
        from url_xray.html_render import _md_to_html
        result = _md_to_html("[ok](https://example.com)")
        assert "https://example.com" in result

    def test_list_tag_closure_on_switch(self):
        """ol→ul switch should not leave unclosed tags."""
        from url_xray.html_render import _md_to_html
        result = _md_to_html("1. first\n2. second\n- bullet1\n- bullet2")
        assert result.count("<ol>") == result.count("</ol>")
        assert result.count("<ul>") == result.count("</ul>")


class TestPromptInjection:
    """Prompt injection isolation tests."""

    def test_system_message_exists(self):
        from url_xray.fetcher import DEFAULT_SYSTEM_MESSAGE
        assert "untrusted" in DEFAULT_SYSTEM_MESSAGE.lower()
        assert len(DEFAULT_SYSTEM_MESSAGE) > 50

    def test_call_llm_accepts_system_message(self):
        import inspect
        from url_xray.llm import call_llm
        sig = inspect.signature(call_llm)
        assert "system_message" in sig.parameters

    def test_prompts_have_zero_to_five_scoring(self):
        """Prompt templates should use 0-5, not 1-10."""
        prompts = get_prompts("zh")
        assert "0-5" in prompts["website"]
        prompts_en = get_prompts("en")
        assert "0-5" in prompts_en["website"]
