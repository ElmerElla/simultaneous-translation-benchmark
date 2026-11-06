# 代码、数据与复现范围

## 可以直接复算什么

`scripts/benchmark.py` 采用命令行参数读入媒体，不含个人绝对路径。`validate` 检查七款产品、47 组证据和19 段公开视频清单；`recompute` 从已复核的原件时间戳重新计算首显/首响延迟，并与最终记录核对。它不会执行网络损伤、登录产品或下载模型。

```console
python scripts/benchmark.py validate
python scripts/benchmark.py validate --media-dir media
python scripts/benchmark.py recompute --output timing-recomputed.csv
python -m unittest discover -s tests -v
```

`stats` 需要 ffmpeg 和 NumPy，对指定公开视频的音频区间做信号检查：

```console
python scripts/benchmark.py stats --media-dir media --video parley-v01 --start 20 --end 28
```

输出峰值、满幅样本占比和指定能量阈值下的首个活动窗口。公开视频是 AAC 浏览副本，这些值不能冒充原件测量或主观音质评分。讯飞视频保留两条音轨：默认英文译音、第二轨中文测试输入；其他六款经原记录核对的重复音轨仅保留第一条。

## 实际使用过的分析源码

- `scripts/analysis/shared-five/`：JotMe、Palabra、Maestra Live、Wordly、Parley 共用的抽轨、OCR、ASR、混音抵消、字幕边界、输出完成、音质和声纹分析。
- `scripts/analysis/transync/`：Transync 原件采集、边界复核、混音辅助、声纹和有效 10% 丢包补录分析。
- `scripts/analysis/iflytek/`：讯飞的选轨、客户端/收听页逐事实核对及声音质量分析。

这些是**历史分析源码**，保留原算法和人工选定的时间区间，不是全自动产品测试运行器。所需的历史工作区、中间音频、模型以及人工判定不全在公开仓库中；不能只克隆仓库就完整重现此前人工视觉复核。第三方模型不重新分发。

源码出处及改动校验值见 `data/source-code-manifest.json`。本机项目路径已改为 `BENCHMARK_WORKSPACE` 环境变量，Python 运行时可用 `BENCHMARK_PYTHON` 指定。五款共用脚本期望历史结构 `outputs/<产品测试目录>/评测结果_20261103/`；讯飞为 `评测结果_20261104/`；Transync 脚本仍依赖其 `analysis_20261102/` 的相邻文件结构，需要放入相应准备好的工作区使用。运行前请阅读脚本入口；部分脚本会写分析产物，需使用自己的工作区副本。

依赖包括 NumPy、SciPy、soundfile、OpenCV、rapidocr_onnxruntime、faster-whisper、onnxruntime、kaldi-native-fbank 和 Pillow，版本快照见 `requirements-analysis.txt`。OCR/ASR 是辅助，最终事实判断和边界仍需人工核对。模型路径显式指定或按历史布局提供；不将个人目录、模型缓存或认证文件加入仓库。

公开 MP4 隐去了桌面和部分设置区域，压缩后波形也有变化；它们适于查看证据，不适于宣称已完整复现原件 OCR、声纹和精确声学起点。完整复现实验需保有原件且已核对其 SHA-256。

## 弱网工具源码

`scripts/weak-network/` 仅收录现行 v2 的源码及测试，不包含 `data/`、`logs/`、`backups/`、会话令牌、可执行程序或驱动。工具使用 Windows 与 NetBalancer；路径可通过 `NETBALANCER_CMD` 指定，Python 默认使用启动它的当前解释器。

本轮只做源码静态检查及纯统计逻辑测试，**没有启动采集器、后台服务或管理员组件，也没有改变任何程序的网络状态**。完整网络工具验收需要单独在隔离目标上执行，包括配置回读、方向、手动/定时恢复及外部配置冲突处理，不能把本次归档验证当成这些验收已重新通过。

仅运行纯计数逻辑测试：

```console
python -m unittest discover -s scripts/weak-network/tests -p test_packet_loss.py -v
```

其他 `live_checks`、`selftest`、`verify_*` 脚本可能启动进程、发包或改变隔离探针配置，请先阅读源码和原工具行为，不能在日常网络或生产进程上盲目运行。

## 数据来源与筛选

`data/tables/` 仅来自每款软件的最终结果工作簿的可见工作表。CSV 为单元格值快照，公式、样式和本机超链接不保留。`data/comparison.csv` 只导出最终比较表中的测试结论，未导入价格、个人消费/余额或过时产品资料。

2026-11-06 对证据缺口的说明修订同步至综合对比 Excel、`data/comparison.csv`、`data/results.json` 和完整报告。`data/tables/` 保留各产品明细工作簿当时的导出值；其中的概括状态应结合最新版综合对比的逐指标说明阅读。修订没有新增场景、改写时间戳或改变事实判定；v1.1 Release 仍为修订前快照。

根目录的 [测试结论.xlsx](../测试结论.xlsx) 是最终综合对比原表的隐私清理副本，保留其内容、格式和公开来源批注。仅两个包部件中的身份/本机目录属性发生变化，其余 12 个包部件与原件逐字节一致；88 个单元格读取值核对一致。表内价格、政策、未实测功能是历史资料，实测判断及其局限以报告为准。校验记录见 `data/workbook-verification.json`。

`data/results.json` 是最终已复核的场景、时间、备注和结论；原始 OCR 轨迹、早期 ASR/抵消候选不公开。新增复算程序只核对这些已确认时间戳的算术一致性，不能证明人工判断本身绝对正确。

## 授权与第三方内容

本仓库用于分享本次测试记录，不代表被测厂商。软件界面、商标及第三方工具归各自权利人所有。未将第三方模型、安装包或商业组件重新分发；也未替用户设定新的开源许可证。
