# ARAUS Schema Notes (MOSAIQ)

This note documents how raw ARAUS fields are mapped into the MOSAIQ schema.

## Data sources

- Dataverse DOI: `10.21979/N9/9OTEVX`
- Reference repo: `ntudsp/araus-dataset-baseline-models`
- Raw tables used: `responses.csv`, `participants.csv`, `soundscapes.csv`, `maskers.csv`

## Unit of analysis

- `responses.csv` in MOSAIQ: one row per accepted participant response (raw ARAUS response row).
- `clips.csv` in MOSAIQ: one row per unique augmented stimulus defined by
  `(fold_r, soundscape, masker, smr)`, aggregated across responses.

## Identifier design

- `clip_id`: generated stable id with prefix `ARAUS_` (e.g., `ARAUS_000001`).
- `response_id`: generated stable id with prefix `ARAUS_`, e.g.
  `ARAUS_{participant}_{stimulus_index}`.

## Split mapping

- `fold_r` in `{1,2,3,4,5}` -> `split=train` (or optionally one fold as `dev` later).
- `fold_r == 0` -> `split=test`.
- `fold_r == -1` -> `split=aux` (practice / attention / consistency stimuli).
- `fold_r` in `{6,7}` (ARAUSv2 test folds) can be mapped to `test` in future expansion.

## Field mapping (raw -> MOSAIQ harmonized)

- `participant` -> `participant_id`
- `smr` -> `smr_db`
- `time_taken` -> `time_taken_s`
- `pleasant` -> `PAQ1_pleasant`
- `vibrant` -> `PAQ2_vibrant`
- `eventful` -> `PAQ3_eventful`
- `chaotic` -> `PAQ4_chaotic`
- `annoying` -> `PAQ5_annoying`
- `monotonous` -> `PAQ6_monotonous`
- `uneventful` -> `PAQ7_uneventful`
- `calm` -> `PAQ8_calm`
- `LAavg_r` -> `LAeq_dBA`
- `Navg_r` -> `loudness_N_sone`
- `Savg_r` -> `sharpness_S_acum`
- `Ravg_r` -> `roughness_R_asper`
- `Favg_r` -> `fluctuation_strength_F_vacil`
- `Tavg_r` -> `tonality_T_tu`
- `language_a` -> `language` (primary language)

## Derived fields

- `ISOPleasant`, `ISOEventful`: computed from PAQ1-PAQ8 using ISO circumplex equations.
- Clip-level `mean_*` fields: mean across all responses sharing the same clip key.

