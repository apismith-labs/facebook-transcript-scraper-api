# 用 cURL 调用 Facebook Transcript Scraper API

[English](README.md)

一个脚本、没有 SDK：创建 Run，轮询同一个 Run，读取它的 Dataset。

## 依赖

`bash`、`curl`、`jq`。

## 运行

```bash
export APIFY_TOKEN='your_apify_token_here'
chmod +x examples/curl/single-url-sync.sh
./examples/curl/single-url-sync.sh 'https://www.facebook.com/watch/?v=1234567890'
```

可选的单 Run 费用上限：

```bash
export APIFY_MAX_TOTAL_CHARGE_USD=0.10
```

## 输出形态

```
Run ID: <id>
Status: success
Segments: 42
Transcript:
<转写文本>
```

## 退出码

| 退出码 | 含义 |
| --- | --- |
| 0 | 已打印转写文本 |
| 2 | 缺少链接参数 |
| 6 | Dataset 为空、`errMsg` 非空，或没有文本 |
| 8 | 创建或读取失败 |
| 9 | Run 以 `FAILED`、`ABORTED`、`TIMED-OUT` 结束 |
| 10 | 创建响应里没有 Run ID |

## 脚本强制的规则

- 创建 `POST` 严格一次；结果不明不重试。
- 轮询只对返回的那个 Run 发 `GET`。
- Build 锁定 `0.0.18`，`restartOnError=false`。
- token 只放在 `Authorization` 请求头里。

批量任务请用 Python 或 Node.js 的 CSV 执行器；cURL 脚本只处理单个链接。

中文文档：[快速开始](../../docs/zh-CN/quickstart.md)。
