import unittest

from scripts.wechat_group_article_extractor import extract_wechat_urls, parse_wechat_article


class WechatExtractorTests(unittest.TestCase):
    def test_extract_wechat_urls_dedup_and_trim(self):
        chat = (
            "A: 看这个 https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=xxx。\n"
            "B: 重复链接 https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=xxx\n"
            "C: 第二个 https://mp.weixin.qq.com/s?__biz=def&mid=2&idx=1&sn=yyy)"
        )
        urls = extract_wechat_urls(chat)
        self.assertEqual(
            urls,
            [
                "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=xxx",
                "https://mp.weixin.qq.com/s?__biz=def&mid=2&idx=1&sn=yyy",
            ],
        )

    def test_parse_wechat_article(self):
        html = """
        <html>
          <head>
            <meta property="og:title" content="示例文章标题">
            <script>
              var nickname = '测试公众号';
            </script>
          </head>
          <body>
            <div id="js_content">
              <p>第一段内容。</p>
              <p>第二段内容。</p>
            </div>
          </body>
        </html>
        """
        article = parse_wechat_article("https://mp.weixin.qq.com/s?x=1", html, max_content_chars=5000)
        self.assertEqual(article.title, "示例文章标题")
        self.assertEqual(article.account_name, "测试公众号")
        self.assertIn("第一段内容。", article.content)
        self.assertIn("第二段内容。", article.content)


if __name__ == "__main__":
    unittest.main()
