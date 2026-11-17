# Privacy processing and evidence boundaries

## Inclusion Principles

Only the videos, final data, conclusions and related source code used in the final evaluation are included. Use explicit file list filtering for the original directory and do not upload the entire directory. Scrap drafts, pre-modification backups, old/adjusted draft workbooks, unused text, run logs, original OCR/ASR candidates, dependent directories, models, installation packages, key files, caches, background states, and session configurations are excluded.

The original recordings and workbooks are retained locally and will not be rewritten or deleted. Seven final detail workbooks export only the CSV values ​​of visible cells, without hidden tables, author attributes, comments, formulas, or personal file hyperlinks. The four pieces of software that did not perform the timbre cloning test were clearly marked "skip this time" in the report, and the old function descriptions were not used as the actual test conclusions.

According to user requirements, a final comprehensive comparison table is also included.`benchmark-results.xlsx`Privacy-cleaned copy of. Check all ZIP package parts, clear the modifier/authorship and local absolute working directory attributes; cell XML, styles, drawings and open source annotations are consistent byte by byte. There are no formulas or external relationships in the table, there is only one visible worksheet. Original/copy verification values ​​and modified parts list see`data/workbook-verification.json`, the cleared names and paths are not recorded.

## Screen processing

The account number, browser avatar and bookmarks, names of participants, meeting links/conference codes/QR codes, and local process paths were found in the original video. The public copy uses a fully opaque black mask that blocks the entire frame by default, revealing only explicitly selected areas of the test business. A time-sharing rectangle is used when moving the window to avoid re-exposing personal information when the window is moved later.

- Transync, Parley, Palabra, JotMe: mainly retain the test translation area; hide the account area, historical navigation, process path, browser bar and desktop peripherals.
- Maestra Live: Preserve test input/translation area; hide browser profile and request details in development tools.
- Wordly: Only keep the test text area; hide participant names, conference codes, links and browser content.
- iFLYTEK: Time-sharing retains the client test text and the second half of the listening page text; hides the shared QR code, meeting address, account area and development tool request details. The tool window is revealed less when moved to the text area.

These occlusions are intentionally conservative and may cover part of the test text, startup interface, control parameters or status. Therefore, the public copies are helpful for viewing the translation and playback process, but they are not a complete desktop forensics package. It cannot be claimed that these copies alone have re-proven the entire scope of the impaired network. Configuration verification follows the final original record, and the original SHA-256 is available for local comparison.

47 report screenshots are extracted directly from the corresponding time points of the public copy, and the safe area is cropped for easy reading; the test text is not redrawn, and subtitles at different times are not collaged. For cropping coordinates see`data/evidence-index.json`, see video occlusion coordinates and effective period.`data/media-manifest.json`。

## Sound processing

User expressly gives permission for public testing of spoken and timbre cloned voices. The public copy only retains the time interval where the test input/output in the original review occurred, and the rest of the time period is muted. The reserved intervals are recorded in the video list one by one. Incorrect translations, extra numbers and abnormal broadcasts of the test itself are evidence of the results and will not be deleted due to incorrect content.

Only the first track is retained among the six software's repeated audio tracks; iFLYTEK retains two audio tracks with different contents. The default track is English translated speech, and the second track is Chinese input. The browser usually plays the default track. If you need to select another input track, you can use a local player that supports track switching. Input and clone reference samples are also provided with the full package, with file metadata cleared.

Public audio re-encoded to AAC; quantitative results such as peaking, digital clipping, voiceprint and precise start and end times are derived from the original. The reference WAV is a PCM-decoded copy of the test sample; no voiceprint vector file has been released that can directly retrieve individual identities.

## Cropping corresponds to time

The retained video starts from the original PTS 0, without speeding up or splicing; only the content not used for the conclusion is cut off at the end. The normal segment of Transync is kept until 128.5 seconds, and the network segment is kept until 86 seconds; the normal segment of Parley history is kept until 58 seconds; the normal segment of Maestra is kept until 110 seconds; the normal segment of JotMe is kept until 72 seconds, and subsequent automatic summaries are not included. The remaining historical videos will be retained until the end of the original recording. On November 11th, Parley's re-recording only displays subtitle rectangles, uses a black screen during the preparation phase and before and after session exit, and mutes outside the test voice range. Impaired network supplementary recording also retains the bottom configuration of the tool. The desktop, account, path and non-test area are all cut out, and the local time in the subtitles is blocked.

MP4 The encoded tail duration may differ by one or two frames/audio packets from the original; public copies are not used for frame-level remeasurement. The original timestamp, original hash, public copy hash and actual public duration are saved separately, and the two hashes cannot be mixed.

## Check scope and limitations

This inspection includes frame extraction and key scene review, privacy keyword OCR scanning of 47 evidence maps, frame-by-frame occlusion area inspection of all exported videos, non-test interval silence inspection, text/source code secret information scanning and release list inspection. Appears in text scanning`example.com`The login format is a test case for denying a credential URL, not a real account or credential.

The sound content verification is based on the existing transcription, fixed test corpus, final manual judgment record and the test interval allowed to be retained; there is no new full manual second-by-second audition, nor frame-by-frame manual review of the source video. Frame extraction/OCR and automatic occlusion verification cannot replace a comprehensive human review. If any omissions are found later, the corresponding material should be removed and revised.

## Source code configuration

The personal project path in the history script is changed to an environment variable. Impaired network tool does not come with this machine`data/`、`logs/`Or start the authentication file in the background. The authentication variables, token generation and permission checking in the code are program logic, and the real token value is not included in the public package. Submit using the repository-specific non-personal email identity, without the original directory Git history.
