# 生产环境接入清单

[English](../production-integration-checklist.md)

把真实业务流量指向这个 Actor 之前，请逐项过一遍。

## 凭据

- [ ] `APIFY_TOKEN` 来自密钥管理服务，而不是提交进仓库的文件。
- [ ] `.env` 已被 git 忽略；`.env.example` 里只有占位符。
- [ ] token 定期轮换，且一旦怀疑泄露立即轮换。
- [ ] token 从不放在 URL、query 或日志里。

## 成本

- [ ] 估算用的是真实的时长分布，而不是 Store 页的标题价。
- [ ] 每一处调用都设置了 `maxTotalChargeUsd`；批量任务还开启 `--require-charge-cap`。
- [ ] 免费套餐任务已过滤为 5 分钟以内的视频。
- [ ] Apify Console 里配置了月度预算提醒。
- [ ] 批量任务先用 `--limit` 和较小的并发起步。

## 幂等性

- [ ] 从不重试创建的 `POST`；结果不明确时按 `creation_unknown` 处理。
- [ ] 在轮询之前就持久化 `runId`、`datasetId` 与 `rowId`。
- [ ] 恢复时读取已有的 Run，绝不创建替代 Run。
- [ ] 不想重复付费的话，重复链接要在上游去掉。

## Build 稳定性

- [ ] 客户端锁定 `build=0.0.18`，并校验 `buildId=fZIlpYENof2jYqIJc`。
- [ ] 当 Actor 的 tagged build 变化时，有明确的重审流程。
- [ ] Build 不匹配时明确报错，而不是静默接受新字段。

## 失败处理

- [ ] `actor_error`、`no_transcript`、`empty`、`run_failed` 被当作不同结果分别处理。
- [ ] 重试只作用于 GET 轮询与 Dataset 读取（429/5xx/网络）。
- [ ] 告警依据业务状态，而不只看进程退出码。
- [ ] 永久性失败不会进入“不断创建新 Run”的重试循环。

## 数据处理

- [ ] 原始条目与归一化文本一起保存，便于日后审计上游变化。
- [ ] `videoUrl`/`audioUrl` 按会过期的 CDN 链接处理，不当长期资产。
- [ ] 转写内容的存储符合你的保留期与隐私政策。
- [ ] 互动数带时间戳，并按快照理解。
- [ ] journal 与结果文件保持 `0600` 权限，存放在加密存储上。

## 可观测性

- [ ] 每次 Run 都记录 `runId`、`datasetId`、状态、build 号与耗时。
- [ ] 跟踪“每条成功转写的成本”，而不只是总花费。
- [ ] 按链接形态（watch、reel、share、短链）分别监控成功率。
- [ ] journal 损坏时任务会失败，而不是静默丢失历史。

## 合规

- [ ] 你有权处理所提交的内容。
- [ ] 你遵守 Facebook 的服务条款与适用的当地法律。
- [ ] 下游用途（训练、发布、审核）对该内容类型是被允许的。
