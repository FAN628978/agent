import re
from typing import Any

import requests

from src.tools.base import BaseTool


class WebSearchTool(BaseTool):
    """网页搜索工具，使用必应搜索"""

    name = "web_search"
    description = "搜索互联网上的信息，返回相关网页的标题、链接和摘要"

    def execute(self, query: str, max_results: int = 5) -> str:
        """执行网页搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数量，默认 5
        """
        try:
            results = self._search(query, max_results)
            if not results:
                return "未找到相关结果"
            return self._format_results(results)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    def _search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """使用必应搜索"""
        import urllib.parse

        encoded_query = urllib.parse.quote(query)
        url = f"https://cn.bing.com/search?q={encoded_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = "utf-8"

        return self._parse_bing_results(response.text, max_results)

    def _parse_bing_results(self, html: str, max_results: int) -> list[dict[str, Any]]:
        """解析必应搜索结果"""
        results = []

        # 必应搜索结果结构
        # 提取每个结果条目
        pattern = r'<li class="b_algo"[^>]*>(.*?)</li>'
        blocks = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for block in blocks[:max_results]:
            # 提取标题和链接
            title_match = re.search(r'<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', block, re.DOTALL | re.IGNORECASE)
            # 提取摘要
            snippet_match = re.search(r'<p class="b_paractl"[^>]*>(.*?)</p>', block, re.DOTALL | re.IGNORECASE)

            if title_match:
                url = title_match.group(1)
                title = title_match.group(2)

                # 过滤百度等内部链接
                if "cn.bing.com" in url:
                    continue

                results.append({
                    "title": self._clean_html(title),
                    "url": url,
                    "snippet": self._clean_html(snippet_match.group(1)) if snippet_match else "",
                })

        return results

    def _clean_html(self, text: str) -> str:
        """清理 HTML 标签"""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        return text.strip()

    def _format_results(self, results: list[dict]) -> str:
        """格式化搜索结果"""
        lines = []
        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result['title']}")
            lines.append(f"   链接: {result['url']}")
            if result.get("snippet"):
                lines.append(f"   摘要: {result['snippet']}")
            lines.append("")
        return "\n".join(lines)


tool = WebSearchTool()