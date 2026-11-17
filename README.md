# Seven Simultaneous Interpretation Applications: Test Report

An offline review of Windows test recordings for **Transync AI, Parley Voice, Palabra, Maestra Live, JotMe, Wordly, and iFLYTEK Simultaneous Interpretation**, with supplementary Doubao examples recorded on Mac.

**[Full report](docs/report.md)** · **[Current comparison data](data/comparison.csv)** · **[Historical workbook](benchmark-results.xlsx)** · **[Doubao Mac examples](docs/parley-normal-20261116.md)**

The adopted comparison covers **47 scenarios and 19 videos**. Parley Voice uses the latest adopted Qwen Live test, recorded on **November 12, 2026**: first subtitle / first audible translated speech **3.4 / 3.8 seconds** on the first input and **4.5 / 5.0 seconds** on the repeated input. The impaired-network test was recorded on November 11. Exact application build numbers were not fully archived.

The two Doubao Mac examples use different audio from the standard S01 comparison script. They provide supplementary evidence of low latency, reaching approximately **1.7 seconds** for a short greeting. They are **excluded from cross-product comparisons**. Pauses may help earlier segmentation, but these samples cannot quantify the reduction caused by a pause. Earlier recordings remain historical evidence.

`5/5` means that all five facts in the fixed test script were confirmed. It is not an overall accuracy percentage. Recording conditions and audio tracks differ, so this report gives no overall product ranking. Configured network impairment is not a measurement of actual service impairment.

| Material | Location |
| --- | --- |
| Methods, findings, limitations and evidence | [Full report](docs/report.md) |
| Current structured results and timing | [results.json](data/results.json), [timing.csv](data/timing.csv) |
| Adopted scenarios and review notes | [47 scenarios](data/scenario-review.csv), [review notes](docs/data-review-20261111.md) |
| Historical workbook and localized verification | [benchmark-results.xlsx](benchmark-results.xlsx), [verification](data/workbook-verification.json) |
| Historical detailed workbook exports | [English CSV tables](data/tables/) |
| Redacted video files and recorded hashes | [media/](media/), [video manifest](data/media-manifest.json) |
| Reproduction code and limitations | [Reproducibility](docs/reproducibility.md), [scripts](scripts/) |
| Redaction and privacy scope | [Privacy](docs/privacy.md) |

[Latest Qwen test and original timestamps](docs/parley-normal-retest-20261112.md) · [Qwen test video](media/parley-qwen-normal-retest-20261112.mp4) · [Impaired-network video](media/parley-qwen-network-20261111.mp4)

## Videos and offline viewing

Redacted videos are tracked directly in [media/](media/). Clone or download the repository and open [report.html](report.html) locally to view the report with its videos. Original recordings remain local. Screenshots and recordings retain the original product interfaces and test speech as evidence; the surrounding documentation and data labels are English.

Historical Release packages are fixed snapshots and may contain excluded recordings or older Chinese documentation. Current findings are in this repository. [Historical v1.1 package](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/tag/v1.1-20261106).

## Verification

Python 3.10 or later; these checks need no third-party dependencies:

```console
python scripts/benchmark.py validate --media-dir media
python scripts/benchmark.py recompute
python scripts/build_scenario_review.py
python scripts/build_report.py
python -m unittest discover -s tests -v
```

The media manifest covers 22 videos including historical exclusions. The two Mac examples and the duplicate historical pause clip are supplemental. Mac video hashes are in [their data file](data/parley-normal-20261116.json).

## Historical material and scope

[November 14 parameter notes](docs/parley-parameters-20261114.md) retain the complete Qwen and Doubao timing records. Doubao is described separately and does not replace the adopted Qwen comparison.

The English historical workbook retains its role as a historical record. Translation changes its labels and prose; prices, policy descriptions and untested features are historical information, not current offers or new test findings. Current adopted results are in the report and comparison data.

Public materials contain reviewed redacted evidence. Test speech and cloned voice were retained with permission. Personal account details, meeting codes, browser content and local paths were masked. Unredacted originals, credentials, configurations, logs, models and installers are excluded.
