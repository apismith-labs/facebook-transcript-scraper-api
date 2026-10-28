# 兼容性与验证状态

[English](../compatibility.md)

这张表把“已实现”和“已验证”分开。**离线测试通过**指用合成的 Dataset 条目在本地与 CI 上跑过，全程无网络。
**尚未线上验证**指代码路径存在，但本仓库没有记录过任何受控的付费 Run。

构建本仓库的过程中没有执行过线上付费 Run。测试里的字段形态来自锁定 build 的 schema，不是录制下来的真实
响应。

## 各语言状态

| 接入方式 | 单链接 | CSV 批量 | 仅计划模式 | 只读恢复 | 成本估算 |
| --- | --- | --- | --- | --- | --- |
| Python 3.10+ | 已实现、离线通过、未线上验证 | 已实现、离线通过 | 支持 | 支持 | 支持 |
| Node.js 18+ | 已实现、离线通过、未线上验证 | 已实现、离线通过 | 支持 | 支持 | 支持 |
| Go 1.22+ | 已实现、离线通过、未线上验证 | 已实现、离线通过 | 支持 | 支持 | 支持 |
| Java 17+ | 已实现、离线通过、未线上验证 | 已实现、离线通过 | 支持 | 支持 | 支持 |
| cURL | 仅示例 | 未实现 | 不适用 | 未实现 | 不支持 |
| Rust | 未实现 | — | — | — | — |

Rust 是有意不交付的，而不是交一份没验证过的代码：本仓库只发布能在 CI 里离线跑通测试的客户端。补上它需要
可用的 `cargo`/`rustc` 工具链，以及常规的 `serde`/HTTP crate；工具链就绪后，移植本身是机械工作。除此之外
的所有示例，只靠 JDK、Go 工具链、Node.js 或 Python 就能构建。
| Apify MCP | 记录了客户端配置，未做端到端验证 | 非本仓库能力 | — | — | — |

## Actor 模式覆盖

| Actor 模式 | Actor 是否支持 | 客户端支持 |
| --- | --- | --- |
| 单条视频（`videoUrl`） | 支持 | Python、Node.js、cURL |
| 原生批量（`bulkUrls`） | **不存在该字段** | 不适用 |
| 主页帖子（`usernames`） | **不存在该字段** | 不适用 |
| CSV 批量 | 不是 Actor 模式 | 客户端一行一个 Run |

## 本仓库已验证的内容

- Build `0.0.18` 与 Build ID `fZIlpYENof2jYqIJc` 在两个客户端里都被锁定，并在运行时从创建响应或 Run 读取
  结果中校验。
- 请求形态：单次 `POST`，body 为 `{ "videoUrl": ... }`，带 `restartOnError=false`、`build=0.0.18`，可选
  `maxTotalChargeUsd`。
- 状态判定的优先级（`empty` → `errMsg` → `text` → `no_transcript` → `unknown`）。
- 七种可接受链接形态的校验与规范化。
- journal 的追加、读取、权限，以及 journal 损坏时拒绝继续。
- 创建结果不明确时绝不重试；创建遇 429 也不重试。
- GET 轮询与 Dataset 读取的重试行为（仅限 429/5xx/网络错误）。

以上全部由离线测试覆盖：89 个 Python 用例、5 个 Node.js 测试文件、`examples/go` 下的 68 个 Go 测试用例
（`go test ./...`），以及 `examples/java` 下的 89 条 Java 断言（`./run_tests.sh`）。

## 未验证的内容

- 对合法公开视频的任意真实 Actor 响应。
- 私密、已删除、地区锁定视频的行为。
- `fb.watch` 与 `/share/{v,r}/` 链接能否在 Actor 内解析。
- 每次 Run 的条目数量；客户端能容忍零条或多条，但预期是一条。
- 真实计费，包括静音视频是否会触发 `speech2text`。
- 高并发下创建 Run 的速率限制阈值。

## Release 与包发布

GitHub Release 只是给本仓库的快照打版本，**不会**发布到 PyPI、npm 或任何其他仓库。Python 与 Node.js 示例
就是源码文件，复制进你的项目，或用相对路径导入。

## 相关文档

- [快速开始](quickstart.md)
- [输入输出字段](input-output-fields.md)
- [成本与限制](cost-and-limits.md)
- [Actor 审计](audit/actor_audit_20261028.md)
