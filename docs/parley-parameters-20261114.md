# Parley historical parameter records (not included in competitive product comparison)

The historical supplementary records of 2026-11-14; 2026-11-17 are adjusted to independent descriptions, and the Doubaos are not included in the comparison of competing products. Qwen N05/N06 will continue to be used as the normal recording number currently used by the seven Hengping models, and the Doubao version 2 will be used as a supplement, and the original 47 group will not be added or replaced. Version 2 is the name of the user's screen recording, and the build number has not been verified. Keep the complete two rounds of data, and extract the minimum value of different admissions according to indicators.

The original accuracy of the latest recordings adopted by Qwen remains unchanged: N05 first subtitle/first sound 3.37/3.84 seconds, original sound to dubbing completion 20.03 seconds; N06 is 4.51/5.04 seconds, 21.98 seconds; both rounds of subtitles are actually 5/5 seconds.

The Doubao version 2 is only a historical description: 5.14/5.57 seconds for the first subtitle/first sound, 22.05 seconds after the original sound is played to the dubbing; 4.76/5.13 seconds again, 21.05 seconds; both rounds of subtitles are actually 5/5 seconds. Mac examples of short sentences that take as little as 1.7 seconds See also[Two videos and instructions](parley-normal-20261116.md). This page does not compare speed across configurations.

Both configurations are Shanghai lines, but Qwen enables real-time cloning, and Doubao uses system VV female voice, each with only two rounds. The subtitles all retain five facts; the Doubao translated speech is only assisted by an independent audio track and is transcribed and checked, without human ear sound quality acceptance. In the second round of auxiliary transcription, Next appears before the last sentence. Whether it is an actual new word needs to be confirmed. The audio and video channels are not calibrated, and the difference in scale of about 0.1–0.2 seconds needs to be interpreted with caution.

## Doubao version 2 original recording time point

|record|original sound starting point|First appearance in English|Stable first sentence|The first sound of translated speech|End of translated speech|Screenshot time|
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
|first| 8.189 | 13.333 | 13.633 | 13.759 | 30.239 | 28.000 |
|again| 31.109 | 35.867 | 36.167 | 36.239 | 52.159 | 51.000 |

Unit second, original PTS; 30 fps, the first subtitleed frames counted from 0 are 400, 1076, there is no complete English word of this round in the previous frame. In the second round, only the new English words added after the old bubbles are counted. The sound is positioned with independent original and translated audio track 10 ms RMS, and the WAV 0 sample corresponds to -0.021 seconds, which has been corrected. Complete decimals see[structured data](../data/parley-parameters-20261114.json)。

## Desensitized subtitle evidence

First recording, original video 28 seconds:

![Doubao version 2 is subtitled for the first time, all five facts are retained](../evidence/images/parley-doubao2-1.png)

Enter again in the same session, the original video is 51 seconds; just check and add English below:

![The Doubao version 2 is subtitled again, all five facts are retained](../evidence/images/parley-doubao2-2.png)

The screenshot only retains the test subtitle area. Cold start of original video, normal translation_Doubao 2.mkv is 53.100 seconds long, SHA256 is e6bbdef093407aabdac368526d9a941fd032b068e963aa037aac7760414b9854, the original is only kept locally, and the unredacted original is not uploaded. This supplement does not provide new public videos or manual audition conclusions; the previously slow Doubao recordings will continue to be local only. Qwen public video and complete timing see you[November 12 retest](parley-normal-retest-20261112.md)。
