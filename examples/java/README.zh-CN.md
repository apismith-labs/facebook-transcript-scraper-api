# 用 Java 调用 Facebook Transcript Scraper API

Java 17+，只用 JDK。不需要 Maven，不需要 Gradle，也不引第三方库：HTTP 走 `java.net.http`，JSON 由
`Json.java` 里一个小的读写实现负责，覆盖 Apify 实际返回的形态。

[English](README.md) · [快速开始](../../docs/zh-CN/quickstart.md)

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `ReliableActor.java` | 分阶段执行器：传输、状态判定、重试策略、JSONL journal、脱敏 |
| `TranscriptClient.java` | `getTranscript()`、链接校验、结果与异常类型 |
| `Json.java` | 极简 JSON 解析与序列化（零依赖） |
| `Cost.java` | 双事件计费模型与“不足一分钟按一分钟”规则 |
| `SingleUrl.java` | 命令行工具：`.env` 加载、`--json`、`--output`、`--resume`、journal |
| `BatchCsv.java` | CSV 一行一个 Run；不加 `--execute` 时只做计划 |
| `Quickstart.java` | 最小示例，无 journal |
| `OfflineTests.java` | 零依赖断言测试运行器 |

## 编译与运行

```bash
cd examples/java
mkdir -p out
javac -encoding UTF-8 -d out $(find src/main/java -name '*.java')

export APIFY_TOKEN='your_apify_token_here'
java -cp out com.apismith.facebooktranscript.Quickstart 'https://www.facebook.com/watch/?v=1234567890'
```

## 可复用的接口

```java
import com.apismith.facebooktranscript.TranscriptClient;

TranscriptClient.Options options = new TranscriptClient.Options();
TranscriptClient.Result result = TranscriptClient.getTranscript(
        "https://www.facebook.com/watch/?v=1234567890", options);

if (result.succeeded()) {
    System.out.println(result.text());
    for (var segment : result.segments()) {
        System.out.println(segment.get("start") + " " + segment.get("text"));
    }
} else {
    System.out.println(result.status() + " " + result.error());
}
```

`Result` 字段：`status`、`text`、`segments`、`items`、`runId`、`datasetId`、`sourceUrl`、
`canonicalUrl`、`urlForm`、`error`、`datasetComplete`、`title`、`nickname`、`duration`。
`succeeded()` 与 `exitCode()` 与其他客户端保持一致。

受检异常：`ConfigurationException`、`ProtocolException`（带 `runId`）、`TransportException`、
`CreationUnknownException`。业务结果以返回值形式给出，不抛异常。

可用参数：`token`、`actorId`、`build`、`timeoutSeconds`、`maxTotalChargeUsd`、`requireChargeCap`、
`datasetLimit`、`runId`、`rowId`、`transport`、`journal`。

## 命令行

```bash
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/watch/?v=1234567890'
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/reel/1234567890/' --json
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/watch/?v=1234567890' \
  --require-charge-cap --max-total-charge-usd 0.10
```

退出码与 Python、Node.js 客户端一致：`0` 成功，`4` actor_error，`5` empty，`6` no_transcript，
`7` unknown，`8` transport_error，`9` run_failed，`10` creation_unknown，`2` 配置问题，`3` 协议错误。

命令会从工作目录加载 `.env`，只读取 `APIFY_*` 键，且不覆盖已存在的环境变量。journal 位于
`sample-output/generated/java-run-journal.jsonl`。

## 批量

```bash
java -cp out com.apismith.facebooktranscript.BatchCsv ../../sample-data/facebook-video-urls.csv
java -cp out com.apismith.facebooktranscript.BatchCsv ../../sample-data/facebook-video-urls.csv --execute
java -cp out com.apismith.facebooktranscript.BatchCsv file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

CSV 列：`videoUrl`（或 `url`）必填，`durationSeconds` 可选。行号会成为 `rowId`。默认结果文件是与 CSV
同目录的 `facebook-batch-results-<UTC>.json`；journal 为同目录下的 `java-run-journal.jsonl`。全部行成功
退出 `0`，有失败退出 `1`，CSV 或配置错误退出 `2`。

## 测试

```bash
cd examples/java
./run_tests.sh
```

脚本会把全部源码编译到 `out/`，然后执行 89 条离线断言，使用假 transport 与临时 journal。不需要 token、
不需要网络，也不需要 `.env`。
