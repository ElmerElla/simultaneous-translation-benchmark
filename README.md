# 七款同声传译软件测试报告

基于 Windows 实测录像，对 **Transync AI、Parley Voice、Palabra、Maestra Live、JotMe、Wordly、讯飞同传**进行离线核查。

分析日期：2026-11-02—2026-11-04。整理发布日期：2026-11-06。

**[阅读完整中文测试报告](docs/report.md)** · **[视频与完整离线文档包](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/tag/v1.0-20261106)** · **[查看最终对比数据](data/comparison.csv)**

本批共七款软件、47 组场景证据、19 段有效录像的脱敏副本。报告包含翻译事实核对、首显/首响、译音质量、弱网表现及有证据的音色比较，并在各场景列出截图与视频时间点。

固定语料的 `5/5` 是五项事实覆盖，不能解释为总体准确率。各行条件和音轨不同，不给跨软件综合排名；弱网配置值不等于实际业务损伤。产品版本未完整留档，结论仅适用于本批录像。

| 内容 | 入口 |
| --- | --- |
| 测试方法、总览、七款详情、47 组截图 | [完整报告](docs/report.md) |
| 结构化最终判定和原件时间戳 | [results.json](data/results.json) / [timing.csv](data/timing.csv) |
| 七份最终明细工作簿的可见工作表值 | [CSV 结果表](data/tables/) |
| 视频原件/公开副本校验值与遮挡规则 | [证据清单](data/media-manifest.json) |
| 离线核对、复算、分析与弱网工具代码 | [复现说明](docs/reproducibility.md) / [脚本](scripts/) |
| 隐私处理、裁切说明与复核边界 | [隐私说明](docs/privacy.md) |

下载 Release 中的 `benchmark-report-offline.zip`，完整解压后打开 `report.html`，可直接阅读并播放视频，无需登录产品或联网加载外部脚本。也可以单独下载所需 MP4；视频不存入 Git 历史。

公开包只包含最终采用材料。**废稿视频、旧版表格、修改前备份、未采用文本、日志、缓存、模型、安装程序和会话配置不收录。** 测试朗读和克隆声音经用户允许保留；账号、会议码、浏览器个人内容和本机路径所在画面区域已遮挡。原件保留本地。

快速核对（Python 3.10+，无第三方依赖）：

```console
python scripts/benchmark.py validate
python scripts/benchmark.py recompute
python -m unittest discover -s tests -v
```

视频哈希核对：把 Release MP4 放到 `media/` 后运行 `python scripts/benchmark.py validate --media-dir media`。
