# Privacy model

Meeting recordings may contain confidential, personal, or market-sensitive information. VoiceNote
therefore treats provider selection and file retention as product behavior rather than incidental
configuration.

## Defaults

- Accept local files and validate them before provider invocation.
- Do not choose cloud processing from the mere presence of credentials.
- Do not copy source audio into output directories.
- Do not log transcript bodies, prompts, secrets, or provider payloads by default.
- Delete temporary derivative audio after a run unless retention was explicitly requested.
- Keep redacted derivatives separate from the immutable source transcript.

Every cloud adapter must document what data leaves the machine and surface its provider identity in
the run manifest. A future dry-run mode will show the planned provider boundary without processing
the file.

Local ASR can require model weights. Model download permission is separate from audio processing:
without it, the provider uses cached/local files only. Allowing a model download does not authorize
uploading the user's recording.

