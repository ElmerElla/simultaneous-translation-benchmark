# Data review of seven simultaneous interpretation software

The review date is 2026-11-11. The objects are Windows Chinese-English videos analyzed from 2026-11-02 to 11-04. The seven softwares use the same S01 corpus, and the replay still belongs to the same corpus. The following results describe the admissions that have been retained.

The review before supplementary recording uses the 45 group of scenes and the 18 segment of video. The normal recording V01 (N01, N02) of Parley Voice has been excluded, and the system timbre and translated speech control that rely on this recording have been removed. The following file check still covers the complete history including V01.

- Re-export seven types of data from the final record of this machine, and compare them item by item with the existing 47 group scene determination, 49 timing events and 34 detailed worksheet CSV, and the content is consistent. Comprehensive comparison The public copy of Excel has consistent cell values ​​with the original table.
- The SHA-256 of the native original of the 19 segment and the public recording of the 19 segment are consistent with the manifest. The 47 screenshots are consistent with the cropped pixels at the corresponding time points of the redacted video. Two public reference WAV hashes match.
- Checked seven scene images of Parley Voice separately, and checked the peaking and clipping of two versions of original sound offset assisted transcription, event table and two independent tail sounds of three videos. The timbre cosine is compared with the output of the existing model, and the voiceprint model is not re-run this round. The rest of the software review is mainly based on the comparison of the final original evaluation record and evidence documents.

## Original video review summary

|software|Number of scenes/timed events|First recorded subtitles/translated complete facts|Please pay attention when checking|
| --- | --- | --- | --- |
| Transync AI | 7 / 7 | 5/5 · 5/5 |In the new segment after the interruption, only F4 and F5 are completely retained, and F2 is partially retained. After replaying, the supplementary translation cannot be uniquely attributed to the previous input.|
| Parley Voice | 5 / 5 |No normal admissions have been adopted|Keep clone and impaired network records, see below for details.|
| Palabra | 7 / 7 | 5/5 · 5/5 |The translated speech currencies of F2 and F3 for the other normal recordings and the 10% configured recordings have not yet been confirmed.|
| Maestra Live | 5 / 5 | 5/5 · 5/5 |The first observation is from the streaming intermediate draft. The impaired network comes from DevTools settings.|
| JotMe | 5 / 6 | 3/5 · 3/5 |The first time and the same process replay as well as the 100 ms configuration recording have mistranslation of amounts. The individual 10% configuration entries are 5/5.|
| Wordly | 8 / 9 |5/5 · Broadcast off|The first audible translated speech of 15.1 seconds belongs to another round of broadcast recording. Additional N02 timing events in`timing.csv`, there is no corresponding release scene screenshot.|
|iFLYTEK simultaneous interpretation| 8 / 8 | 5/5 · 5/5 |The subtitles on the first round of listening pages are also 5/5. Rdrop's client subtitles are complete, the controlled listening page stays at the old segment, and the recorded sound cannot uniquely belong to this window.|

## Parley Voice original video review

The original video review excluded V01. Subsequent Qwen Live impaired network supplementary recording replaced the four adoption records of V02. The following table shows the Doubao review results at that time.

|record|Subtitles/dubbed complete facts|Video First Display / First Response Approximate Value|This round of review|
| --- | --- | --- | --- |
|C01 real-time cloning| 3/5 · 3/5 |3.7 / 4.6 seconds| [25 second screenshot](../evidence/images/parley-c01.png)and auxiliary conversion to the budget amount of 30,000 yuan, which lacks the "upper limit" limit. F2 is partially reserved.|
|W01 upstream and downstream 100 ms configuration| 4/5 · 4/5 |4.0 / 4.6 seconds| [32 second screenshot](../evidence/images/parley-w01.png)F1 in becomes a written explanation to the HR department.|
|R01 interrupt related fragments|Items 0 are complete, items 1 are partial (subtitles and translations)|Time without independent ownership| [54 second screenshot](../evidence/images/parley-r01.png)The complete subtitles of the previous round will be displayed first, and then the fragments of this round will be displayed. Only check the newly added parts.|
|R02 Replay the same article after recovery|Items 4 are complete, items 1 are partial (subtitles and translations)|Time without independent ownership| [76 second screenshot](../evidence/images/parley-r02.png)Confirmation test results appear in the merged segment, which is also mixed with additional content such as "from now to Friday" and cannot be separated into an independent recovery.|
|W04 10% probability packet loss configuration for uplink and downlink| 4/5 · 4/5 |4.1 / 4.4 seconds| [104 second screenshot](../evidence/images/parley-w04.png)The new paragraph below requires a written explanation to be submitted to the panel. Actual business packet loss rates have not been independently verified.|

The timing of clone and impaired network recordings was based on the earliest acoustic activity in the original recording. First occurrences include the first occurrence of a complete English word, stable phrases are recorded separately. The overlapping first sounds are positioned by waveform cancellation, and the OBS channel is not calibrated.

The cosine value of the voiceprint of the C01 clone tail and the reference original sound is 0.5450, the peak value is 0.908, and the full-scale clipping is 0%. These values ​​describe the short segment. Blind listening and multi-sample testing are lacking for subjective sound quality and long-term cloning stability.

## How to use the round-by-round review table

Open[47 group adoption scenario](../data/scenario-review.csv). Each line contains test settings, F1 to F5 determinations, event ID, screenshot recording time and evidence path. iFLYTEK listening page single column. The number of complete facts only counts "correct" and "correct (offset auxiliary)". Blank means there are no independent timings to fill in or coverage numbers to determine. The specific time events for interruption and replay overlap and the original timing of excluded recordings can be found in[timing.csv](../data/timing.csv)。

The workbook and original data are still the source of this review. Round by round table[Generate script](../scripts/build_scenario_review.py)Export from structured results, evidence index and video inventory. Video directory correspondence[Redacted material Release](https://github.com/ElmerElla/simultaneous-translation-benchmark/releases/tag/v1.0-20261106)。


## November 11 Parley Voice normal scene supplementary recording

The two rounds of S01 using Qwen Live enable real-time cloning, and the interface displays the Singapore route. Currently, a total of 47 groups use scenes and 19 segments use videos. Two records for the old V01 remain excluded.

|record|subtitles/dubbing|original sound starting point|First appearance in English|Approximate value of first echo of translated voice|First appearance / first sound difference|End of subtitles / end of translation|
| --- | --- | --- | --- | --- | --- | --- |
|N03 first session| 5/5 · 5/5 |5.70 seconds|10.100 seconds|10.19 seconds|4.4 / 4.5 seconds|18.200 / 25.76 seconds|
|N04 Enter again in the same session| 5/5 · 5/5 |26.73 seconds|30.933 seconds|30.81 seconds|4.2 / 4.1 seconds|38.700 / 47.73 seconds|

The recording starting point client has been opened. It takes about 1.33 seconds to display that the session is in preparation, 3.53 seconds to enter monitoring, and the interface status transition takes about 2.2 seconds. The process startup time cannot be measured from this video. This is the same text entered twice in the same session, N04 only checks the new English in the bubble.

The first subtitle and the last sentence of subtitles are determined by adjacent frames of 30 fps. The decoded SHA-256 of the three audio tracks marked as remix, original audio, and dubbing is the same. Continuous acoustic activity of the first Chinese sentence was localized as a waveform, excluding short pulses such as clicks. The five facts in English were cross-checked by a local Faster-Whisper Small on full and segmented transcriptions of the mix and scored separately from the footage. Overlapping first sounds are approximate (approximately ±0.2 seconds), and the audio and video paths of the original are not calibrated. The new recordings are not independently translated, nor are default timbres, subjective sound quality, network impairments, or listener latency measured.

[Supplementary recording of redacted video](../media/parley-qwen-normal-20261111.mp4) · [N03 subtitle screenshot](../evidence/images/parley-n03.png) · [N04 subtitle screenshot](../evidence/images/parley-n04.png) · [Summary of original video and public copy](../data/media-manifest.json)

## November 11 Parley Voice impaired network scene supplementary recording

Four sets of video observations replace the four sets of scenes of Doubao V02. The new results are the same as the normal supplementary registration on the same day using Qwen Live. Each group of inputs is the same paragraph S01, and the new English is independently determined.

|record|subtitles/dubbing|original sound starting point|Subtitles appear for the first time / translation sounds for the first time|First appearance / first sound difference|End of subtitles / end of translation|
| --- | --- | --- | --- | --- | --- |
|W05 Qwen Live · Uplink and downlink each 100 ms configuration| 5/5 / 5/5 | 7.93 |12.900 / about 13.10|5.0 / about 5.2|20.633 / about 29.64|
|R03 Qwen Live · About 10 seconds interrupted|not observed / not observed| 37.17 | — | — | — |
|R04 Qwen Live · Replay of the same article after the interruption is lifted| 5/5 / 5/5 | 53.22 |58.000 / about 57.68|4.8 / about 4.5|65.767 / about 72.56|
|W06 Qwen Live · 10% probability packet loss configuration for both uplink and downlink| 5/5 / 5/5 | 77.51 |82.067 / about 82.21|4.6 / about 4.7|90.067 / about 98.38|

The times and differences in the table are all in seconds. The original sound is positioned by the acoustic activity of the first consecutive sentence. The English first sound is transcribed by mixing and waveform estimation; the audio and video channels are not calibrated. The decoded PCM hashes of the three tagged tracks are consistent. Use local Faster-Whisper Small to cross-check the complete video and segmented English transcriptions, and the first sound is approximated.

The impaired network workbench displays 100 ms and the configuration is approximately 5.27–31.80 seconds. The countdown of 10 seconds to interrupt the configuration is about 40.13–50.27 seconds. The input is before the configuration, and it is input again after about 3.0 seconds after canceling. No new output of this round appears before replay, and only a complete set of new output appears after replay. There is no way to independently quantify reconnection or automatically compensate for latency.

The 10% configuration appears approximately at 75.80 seconds and remains valid until at least 99 seconds. The first sentence of the packet loss round is appended to the end of the old bubble, and the second bubble continues with the remaining four facts. The impaired network workbench prompts that a possible local relay has been detected, and the service coverage needs to be verified. There is only one round of each condition, and the measured service delay and packet loss rate are not collected independently.

[Impaired network supplementary recording of redacted videos](../media/parley-qwen-network-20261111.mp4) · [round by round results](../data/scenario-review.csv) · [Video Checklist](../data/media-manifest.json)
