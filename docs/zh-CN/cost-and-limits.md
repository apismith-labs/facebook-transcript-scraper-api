# 成本与限制

[English](../cost-and-limits.md)

Store 页写的是 **“from $1.00 / 1,000 results”**。这个数字只描述了两个计费事件中的一个。一次转写发生的真实
费用，是两者之和。

## 一次成功转写包含两个计费事件

| 事件 | 单价（2026-10-28 采集） | 计价单位 |
| --- | --- | --- |
| `apify-default-dataset-item` | **$0.001** | 每条数据集条目 |
| `speech2text` | **$0.0045**（FREE）· $0.0035（BRONZE）· $0.003（SILVER）· $0.002（GOLD、PLATINUM、DIAMOND） | 每满一分钟（不足一分钟按一分钟） |

不足一分钟的时长一律按一分钟计费。所以 30 秒的短片和 60 秒的片子，转写费用相同。

单条视频的公式：

```
cost = 0.001 + ceil(max(duration_seconds, 1) / 60) × tier_price_per_minute
```

| 视频时长 | FREE 档 | GOLD 档 |
| --- | --- | --- |
| 30 秒 | $0.0055 | $0.0030 |
| 1 分钟 | $0.0055 | $0.0030 |
| 10 分钟 | $0.0460 | $0.0210 |
| 30 分钟 | $0.1360 | $0.0610 |
| 60 分钟 | $0.2710 | $0.1210 |

一千条 1 分钟的视频，在 FREE 档要花 **$5.50**，不是 $1.00。Store 页的标题价只统计了数据集条目事件。

执行前先估算：

```bash
python scripts/estimate_cost.py --videos 1000 --minutes 1 --tier FREE
python scripts/estimate_cost.py --videos 20 --minutes 8 --tier GOLD --json
```

批量执行器在“计划”阶段就会打印同样的估算，此时还没有任何 Run。

## 套餐限制

- **免费套餐：** 视频不超过 **5 分钟**。文档说明更长的视频会被拒绝。
- **付费套餐：** 文档说明时长不限。
- 除时长之外，真正的限制来自视频是否公开可访问，以及 Actor 对这条链接的成功率。

## 实际账单可能偏离预估的原因

- 静音视频或转写失败的视频，`speech2text` 事件可能不会触发。**未验证。**
- 被判定为 `no_transcript` 的视频，仍可能已经计了转写费用。
- Apify 套餐折扣改变的是每分钟档位价，不改变数据集条目单价。
- Apify 平台自身的用量按文档已包含在该 Actor 的按事件计费中，但账号套餐、代理与存储用量仍由你承担。
- 价格在服务端是有版本的。Actor 元数据里已经存在一份被取代的旧价（2026-03-06：每条结果 $0.0006 + 每分钟
  $0.001）。不要把任何一份价格写死在代码里，涉及钱的时候现读一次。

## 控制花费

| 控制手段 | 位置 |
| --- | --- |
| 单 Run 费用上限 | `--max-total-charge-usd 0.10`，或 `APIFY_MAX_TOTAL_CHARGE_USD` |
| 没有上限就拒绝执行 | `--require-charge-cap`，或 `APIFY_REQUIRE_MAX_TOTAL_CHARGE_USD=1` |
| 批量仅计划模式 | `batch_csv.py file.csv`（不带 `--execute`） |
| 限制行数 | `--limit 10` |
| 并发数 | 预算紧张时用 `--max-concurrency 1` |
| 精简输入集合 | 一行一个链接；空行会跳过，重复行**不会**自动去重 |

注意：请求的费用上限是 Run 的一个选项，不是最终发票的保证。Apify 会按自己的计费逻辑完成或中止 Run。请把
这个上限当作强护栏，而不是硬顶。

## 数据本身的限制

- 转写由语音识别自动生成，准确率取决于音质、语言和说话人重叠程度。
- 只转写音轨，不读取画面字幕。
- 互动数（`playCount`、`commentCount`、`reactionCount`、`likesCount`、`shareCount`）是某一时刻的快照，
  也可能缺失。
- `videoUrl` 与 `audioUrl` 是会过期的 CDN 链接，不要当作长期资产保存。
