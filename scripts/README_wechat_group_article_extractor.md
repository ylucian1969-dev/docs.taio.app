# wechat_group_article_extractor.py 使用说明

## 1. 准备环境

项目使用 Python 标准库即可运行，无需额外安装第三方依赖。

```bash
python --version
```

建议 Python 3.10+。

## 2. 准备聊天记录文件

将微信群聊天内容导出/整理成纯文本文件，例如 `chat.txt`。脚本会自动识别其中的公众号文章链接（`https://mp.weixin.qq.com/s?...`）。

示例：

```text
张三：这个值得看 https://mp.weixin.qq.com/s?__biz=xxx&mid=111&idx=1&sn=aaa。
李四：还有这个 https://mp.weixin.qq.com/s?__biz=yyy&mid=222&idx=1&sn=bbb
```

## 3. 运行脚本

```bash
python scripts/wechat_group_article_extractor.py \
  --chat-file chat.txt \
  --output wechat_articles.jsonl \
  --errors wechat_article_errors.jsonl \
  --sleep 0.5
```

常用参数：

- `--chat-file`：聊天记录文本文件（必填）
- `--output`：成功结果输出文件（JSONL）
- `--errors`：失败记录输出文件（JSONL）
- `--encoding`：聊天记录编码（默认 `utf-8`）
- `--max-content-chars`：正文截断长度（默认 `5000`）
- `--sleep`：请求间隔秒数，建议设置为 `0.2~1.0`，降低请求过快风险

## 4. 查看结果

### 成功结果（`wechat_articles.jsonl`）

每行一条 JSON，示例：

```json
{"url":"https://mp.weixin.qq.com/s?__biz=...","title":"示例标题","account_name":"示例公众号","content":"正文内容..."}
```

### 失败结果（`wechat_article_errors.jsonl`）

每行一条 JSON，示例：

```json
{"url":"https://mp.weixin.qq.com/s?__biz=...","error":"HTTP Error 403: Forbidden"}
```

## 5. 先运行测试（推荐）

```bash
python -m unittest -v tests/test_wechat_group_article_extractor.py
```

## 6. 注意事项

- 微信文章可能存在访问频率限制、区域限制或反爬策略；失败链接会记录到错误文件。
- 如遇编码问题可尝试 `--encoding gb18030`。
