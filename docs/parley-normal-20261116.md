# Parley Voice: supplementary Doubao Mac examples

### Doubao Mac short-utterance and pause examples (01, 02)

These two Mac recordings use different audio from the standard S01 cross-product test. They are supplementary evidence of low latency only, are excluded from the comparison table, and do not replace the latest adopted Qwen test. The lowest observed latency is approximately 1.7 seconds; this is not representative of long utterances or continuous speech.

**Example 01: a short greeting.** The Chinese greeting (English gloss: "Hello") is translated as "Hello". Subtitle latency is approximately 1.8 seconds and translated-speech onset latency approximately 1.7 seconds. The meaning is correct. Short utterances and suitable pauses may help the system segment and translate earlier. This sample cannot quantify a latency reduction caused by pausing; sentence length, speaking rhythm and recording conditions also matter.

[Play Doubao Mac example 01](../media/parley-doubao-normal-01-20261116.mp4)

**Example 02: a greeting, a pause, then a meeting question.** The speaker pauses approximately 0.5 seconds after the Chinese greeting, then asks in Chinese, "What time does this afternoon's meeting start?" The greeting subtitle appears after approximately 1.7 seconds. The question's subtitle latency is approximately 3.4 seconds and translated-speech onset latency approximately 3.37 seconds. The translation preserves the meaning. A pause may help earlier segmentation, but this sample cannot quantify the reduction caused by pausing or imply that the longer question also has a 1.7-second latency.

[Play Doubao Mac example 02](../media/parley-doubao-normal-02-20261116.mp4)

Each delay starts at the corresponding Chinese utterance onset. Subtitle sampling uncertainty is approximately 0.1 seconds. The greeting's translated speech in example 02 overlaps the following Chinese input, so its onset is unconfirmed. Mixed-audio waveforms and assisted transcription support the content checks. No human listening assessment was performed, and the audio/video paths were not calibrated. No matched-script with/without-pause trial was conducted, so no causal reduction or fixed latency is claimed.

## Original recording timestamps

Example 01: source onset 4.78 s; subtitle onset 6.50–6.60 s; translated speech onset 6.48 s.

Example 02, greeting: source onset 4.03 s; subtitle onset 5.70–5.75 s. Question: source onset 4.94 s; subtitle onset 8.30–8.40 s; translated speech onset 8.31 s.

[Structured data](../data/parley-normal-20261116.json) · [Latest adopted Qwen test](parley-normal-retest-20261112.md)

![Example 01 subtitle](../evidence/images/parley-doubao-normal-01.png)
