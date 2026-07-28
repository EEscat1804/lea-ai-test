# Test fixtures

- `trigger_weapon.wav` — synthesized locally and offline with macOS `say`
  (no external API/service involved), saying the phrase *"He's here. He has
  a weapon."*, which matches guardrail rule `G-01` in `evaluator.py`
  (`"he's here"`, `"has a weapon"`). Used to verify the audio pipeline
  actually routes a real trigger phrase to the correct guardrail response,
  not just neutral speech. Generated with:
  ```bash
  say -o trigger_weapon.wav --file-format=WAVE --data-format=LEI16@16000 \
      "He's here. He has a weapon."
  ```
- `sample_en.mp3` — the English example clip bundled with the SenseVoiceSmall
  model itself (`iic/SenseVoiceSmall/example/en.mp3`, downloaded as part of
  the model assets on first run). Used only to verify `.mp3` input decodes
  correctly — not trigger-phrase content.
