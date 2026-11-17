# Code, data and reproduction scope

## What can be directly recalculated?

`scripts/benchmark.py`Use command line parameters to read media, excluding personal absolute paths.`validate`Check seven products, 55 group evidence and 22 public video list (including historical exclusion records);`recompute`First appearance/first audible translated speech delay is recalculated from the reviewed original timestamp and reconciled with the final record. It does not perform network damage, log in to products, or download models.

```console
python scripts/benchmark.py validate
python scripts/benchmark.py validate --media-dir media
python scripts/benchmark.py recompute --output timing-recomputed.csv
python -m unittest discover -s tests -v
```

`stats`Requires ffmpeg and NumPy to perform signal check on the audio interval of the specified public video:

```console
python scripts/benchmark.py stats --media-dir media --video parley-v01 --start 20 --end 28
```

Output peak value, full sample ratio, and first active window at specified energy threshold. Public videos are AAC view copies, and these values ​​cannot pass for original measurements or subjective sound quality ratings. iFLYTEK Video retains two audio tracks: the default English translated speech and the second track Chinese test input; only the first track of the other six duplicate audio tracks that has been verified by the original record is retained.

## Actual used analysis source code

- `scripts/analysis/shared-five/`：JotMe, Palabra, Maestra Live, Wordly, Parley share common extraction tracks, OCR, ASR, mix cancellation, subtitle boundaries, output completion, sound quality and voiceprint analysis.
- `scripts/analysis/transync/`: Transync original capture, boundary review, mixing assistance, voiceprint and effective 10% packet loss re-recording analysis.
- `scripts/analysis/iflytek/`: iFLYTEK’s track selection, client/listening page fact-checking and sound quality analysis.

These are **historical analysis source code**, which retain the original algorithm and manually selected time intervals, and are not a fully automatic product test runner. The required historical workspace, intermediate audio, models, and human judgment are not all in the public repository; you cannot just clone the repository and fully reproduce the previous human visual review. Third-party models are not redistributed.

For the source code source and modification check value, see`data/source-code-manifest.json`. The native project path has been changed to`BENCHMARK_WORKSPACE`Environment variables, available when Python is running`BENCHMARK_PYTHON`specified. Five shared script expectations history structure`outputs/<product test directory>/evaluation results_20261103/`; iFLYTEK is`Evaluation results_20261104/`;Transync scripts still rely on its`analysis_20261102/`The adjacent file structure needs to be placed in the corresponding prepared workspace for use. Please read the script entry before running; some scripts will write analysis products and you need to use your own copy of the workspace.

Dependencies include NumPy, SciPy, soundfile, OpenCV, rapidocr_onnxruntime, faster-whisper, onnxruntime, kaldi-native-fbank and Pillow. See the version snapshot`requirements-analysis.txt`. OCR/ASR is an auxiliary, and the final factual judgment and boundaries still need to be manually checked. Model paths are specified explicitly or provided by historical layout; personal directories, model caches, or certification files are not added to the repository.

Public MP4 hides the desktop and part of the settings area, and the waveforms also change after compression; they are suitable for viewing evidence, not suitable for claiming to have fully reproduced the original OCR, voiceprint and precise acoustic starting point. To completely reproduce the experiment, you must keep the original and have its SHA-256 verified.

## Impaired network tool source code

`scripts/weak-network/`Only the source code and tests of the current v2 are included, excluding`data/`、`logs/`、`backups/`, session token, executable program or driver. Tools use Windows and NetBalancer; paths are available via`NETBALANCER_CMD`Specified, Python defaults to using the current interpreter that started it.

This round only does source code static inspection and pure statistical logic testing. **No collector, background service or administrator component is started, nor is the network status of any program changed**. Complete network tool acceptance needs to be performed separately on the isolation target, including configuration readback, direction, manual/scheduled recovery, and external configuration conflict handling. This archive verification cannot be regarded as these acceptances having been re-passed.

Run only pure counting logic tests:

```console
python -m unittest discover -s scripts/weak-network/tests -p test_packet_loss.py -v
```

other`live_checks`、`selftest`、`verify_*`Scripts may start processes, send packages, or change isolation probe configurations. Please read the source code and original tool behavior first, and do not blindly run it on daily networks or production processes.

## Data sources and filtering

`data/tables/`Only the visible worksheets from the final result workbook for each software. CSV is a snapshot of cell values; formulas, styles, and native hyperlinks are not preserved.`data/comparison.csv`Only the test conclusions in the final comparison table are exported, and prices, personal consumption/balance, or outdated product information are not imported.

2026-11-06 The revision of the explanation of the evidence gap is synchronized to the comprehensive comparison Excel,`data/comparison.csv`、`data/results.json`and full report.`data/tables/`The exported values ​​of each product detail workbook at that time are retained; the summary status should be read in conjunction with the indicator-by-index description of the latest version of the comprehensive comparison. The revision does not add new scenes, rewrite timestamps, or change factual determinations; v1.1 Release is still a pre-revision snapshot.

root directory[benchmark-results.xlsx](../benchmark-results.xlsx)is a privacy-cleaned copy of the original comprehensive comparison table, retaining its content, formatting, and public source annotations. Only the identity/native directory attributes in two package parts have changed, and the remaining 12 package parts are consistent with the originals byte by byte; the read values ​​of 88 cells are consistent. The prices, policies, and untested functions in the table are historical data, and actual measured judgments and limitations are subject to the report. See the verification record`data/workbook-verification.json`。

`data/results.json`Scenarios, timings, notes and conclusions are final reviewed; original OCR trajectories, early ASR/offset candidates are not public. The new recalculation program only checks the arithmetic consistency of these confirmed timestamps and cannot prove that the manual judgment itself is absolutely correct.

## Licensing and Third Party Content

This repository is used to share the test records and does not represent the manufacturer being tested. The software interface, trademarks and third-party tools belong to their respective rights holders. No third-party models, installation packages, or commercial components are redistributed; no new open source licenses are set for users.

storehouse`media/`Supplied with the redacted MP4 in the 22 segment list, two additional Mac examples and a copy of the historical pause (same content as example 02), and two public reference WAVs.`validate --media-dir media`Check the video in the 22 segment list; see also SHA256 for the two Mac examples`data/parley-normal-20261116.json`。[Normal retest on November 12](../media/parley-qwen-normal-retest-20261112.mp4) · [Qwen Live impaired network supplementary recording](../media/parley-qwen-network-20261111.mp4) · [Qwen Live normal supplementary recording](../media/parley-qwen-normal-20261111.mp4)
