# 七款同声传译软件测试报告

基于 Windows 实测录像，对 **Transync AI、Parley Voice、Palabra、Maestra Live、JotMe、Wordly、讯飞同传**进行离线核查。

分析日期：2026-11-02—2026-11-04。整理发布日期：2026-11-06。

**[阅读完整中文测试报告](docs/report.md)** · **[查看当前对比数据](data/comparison.csv)** · **[下载历史工作簿](测试结论.xlsx)**

当前采用七款软件的 47 组场景、19 段录像。2026-11-11 纳入 Parley Voice 千问 Live 的正常与弱网补录。原豆包正常与弱网录像 V01、V02 作为历史记录。

固定语料的 `5/5` 是五项事实覆盖，不能解释为总体准确率。各行条件和音轨不同，不给跨软件综合排名；弱网配置值不等于实际业务损伤。产品版本未完整留档，结论仅适用于本批录像。

| 内容 | 入口 |
| --- | --- |
| 测试方法、总览、七款详情和当前采用的证据 | [完整报告](docs/report.md) |
| 历史综合对比原表，包含已排除的 V01 | [测试结论.xlsx](测试结论.xlsx) / [隐私清理校验](data/workbook-verification.json) |
| 结构化判定和时间戳，含排除标记 | [results.json](data/results.json) / [timing.csv](data/timing.csv) |
| 逐轮判定与证据路径 | [复核记录](docs/data-review-20261111.md) / [47 组采用场景](data/scenario-review.csv) |
| 七份历史明细工作簿的可见工作表值 | [CSV 留档](data/tables/) |
| 视频原件/公开副本校验值与遮挡规则 | [证据清单](data/media-manifest.json) |
| 离线核对、复算、分析与弱网工具代码 | [复现说明](docs/reproducibility.md) / [脚本](scripts/) |
| 隐私处理、裁切说明与复核边界 | [隐私说明](docs/privacy.md) |

v1.1 Release 的离线包是历史快照，包含已排除的 V01。当前结论以本页链接的仓库报告和逐轮表为准。[历史离线包](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/tag/v1.1-20261106)

[千问 Live 弱网补录脱敏录像](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/download/parley-network-retest-20261111/parley-qwen-network-20261111.mp4) · [千问 Live 正常补录脱敏录像](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/download/parley-retest-20261111/parley-qwen-normal-20261111.mp4)。

历史素材共有 **19 段脱敏 MP4、47 张截图、2 份独立测试参考 WAV**，包括已排除的 V01。各软件的翻译播报保留在视频音轨中。[素材下载页](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/tag/v1.0-20261106) · [S01 测试输入](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/download/v1.0-20261106/s01-input.wav) · [音色克隆参考](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/download/v1.0-20261106/clone-reference.wav)

Excel 仅清空作者/修改人身份和本机工作目录属性；单元格、样式、绘图及公开来源批注保持原样。表内价格、政策和未实测功能描述是当时资料记录，不能当作最新报价或新增实测结论；实测范围与限制以报告为准。

公开包只包含最终采用材料。**废稿视频、旧版表格、修改前备份、未采用文本、日志、缓存、模型、安装程序和会话配置不收录。** 测试朗读和克隆声音经用户允许保留；账号、会议码、浏览器个人内容和本机路径所在画面区域已遮挡。原件保留本地。

快速核对（Python 3.10+，无第三方依赖）：

```console
python scripts/benchmark.py validate
python scripts/benchmark.py recompute
python scripts/build_scenario_review.py
python -m unittest discover -s tests -v
```

视频哈希核对：把 Release MP4 放到 `media/` 后运行 `python scripts/benchmark.py validate --media-dir media`。
