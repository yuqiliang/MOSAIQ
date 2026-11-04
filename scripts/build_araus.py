"""Build MOSAIQ ARAUS clips/responses tables from raw ARAUS metadata.

Input can be either:
1) a directory containing ARAUS CSV files (responses.csv, participants.csv), or
2) a ZIP file containing these files (e.g., data.zip from Dataverse).

Output:
- datasets/ARAUS/data/responses.csv
- datasets/ARAUS/data/clips.csv
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MOSAIQ ARAUS tables")
    parser.add_argument(
        "--input-zip",
        type=Path,
        default=None,
        help="Path to ARAUS data zip (contains data/responses.csv etc.)",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Path to directory containing responses.csv and participants.csv",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("datasets/ARAUS/data"),
        help="Output directory for generated MOSAIQ CSV files",
    )
    parser.add_argument(
        "--dev-fold",
        type=int,
        default=None,
        choices=[1, 2, 3, 4, 5],
        help="Optional CV fold to map to split=dev (other CV folds stay train)",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str], table_name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"{table_name} missing required columns: {missing_str}")


def load_csv_from_zip(zf: zipfile.ZipFile, filename: str) -> pd.DataFrame:
    candidates = [filename, f"data/{filename}", f"datav2/{filename}"]
    for cand in candidates:
        try:
            data = zf.read(cand)
            return pd.read_csv(io.BytesIO(data))
        except KeyError:
            continue
    tried = ", ".join(candidates)
    raise FileNotFoundError(f"Could not find {filename} in zip. Tried: {tried}")


def load_inputs(input_zip: Path | None, input_dir: Path | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if input_zip is None and input_dir is None:
        raise ValueError("Provide one of --input-zip or --input-dir")
    if input_zip is not None and input_dir is not None:
        raise ValueError("Provide only one of --input-zip or --input-dir")

    if input_zip is not None:
        with zipfile.ZipFile(input_zip) as zf:
            responses = load_csv_from_zip(zf, "responses.csv")
            participants = load_csv_from_zip(zf, "participants.csv")
        return responses, participants

    assert input_dir is not None
    responses_path = input_dir / "responses.csv"
    participants_path = input_dir / "participants.csv"
    if not responses_path.exists() or not participants_path.exists():
        raise FileNotFoundError(
            f"Expected {responses_path} and {participants_path} to exist"
        )
    return pd.read_csv(responses_path), pd.read_csv(participants_path)


def iso_coords_from_paq(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Compute ISO circumplex coordinates from PAQ ratings (1-5 Likert)."""
    c = np.cos(np.pi / 4.0)
    denom = 4.0 + np.sqrt(32.0)

    iso_p = (
        (df["PAQ1_pleasant"] - df["PAQ5_annoying"])
        + c
        * (
            (df["PAQ8_calm"] - df["PAQ4_chaotic"])
            + (df["PAQ2_vibrant"] - df["PAQ6_monotonous"])
        )
    ) / denom
    iso_e = (
        (df["PAQ3_eventful"] - df["PAQ7_uneventful"])
        + c
        * (
            (df["PAQ4_chaotic"] - df["PAQ8_calm"])
            + (df["PAQ2_vibrant"] - df["PAQ6_monotonous"])
        )
    ) / denom
    return iso_p, iso_e


def map_split(fold_r: int, dev_fold: int | None) -> str:
    if fold_r == -1:
        return "aux"
    if fold_r == 0:
        return "test"
    if fold_r in (6, 7):
        return "test"
    if dev_fold is not None and fold_r == dev_fold:
        return "dev"
    return "train"


def main() -> None:
    args = parse_args()

    responses_raw, participants_raw = load_inputs(args.input_zip, args.input_dir)

    require_columns(
        responses_raw,
        [
            "participant",
            "fold_r",
            "soundscape",
            "masker",
            "smr",
            "stimulus_index",
            "time_taken",
            "is_attention",
            "pleasant",
            "vibrant",
            "eventful",
            "chaotic",
            "annoying",
            "monotonous",
            "uneventful",
            "calm",
            "appropriate",
            "Savg_r",
            "Navg_r",
            "Favg_r",
            "LAavg_r",
            "Ravg_r",
            "Tavg_r",
        ],
        "responses.csv",
    )
    require_columns(
        participants_raw,
        ["participant", "language_a", "age", "gender"],
        "participants.csv",
    )

    participants = participants_raw[["participant", "language_a", "age", "gender"]].copy()
    participants = participants.rename(
        columns={
            "participant": "participant_id",
            "language_a": "language",
        }
    )

    resp = responses_raw.copy()
    resp = resp.rename(
        columns={
            "participant": "participant_id",
            "smr": "smr_db",
            "time_taken": "time_taken_s",
            "pleasant": "PAQ1_pleasant",
            "vibrant": "PAQ2_vibrant",
            "eventful": "PAQ3_eventful",
            "chaotic": "PAQ4_chaotic",
            "annoying": "PAQ5_annoying",
            "monotonous": "PAQ6_monotonous",
            "uneventful": "PAQ7_uneventful",
            "calm": "PAQ8_calm",
            "LAavg_r": "LAeq_dBA",
            "Navg_r": "loudness_N_sone",
            "Savg_r": "sharpness_S_acum",
            "Ravg_r": "roughness_R_asper",
            "Favg_r": "fluctuation_strength_F_vacil",
            "Tavg_r": "tonality_T_tu",
        }
    )

    # Keep only folds represented in current schema constraints.
    resp = resp[resp["fold_r"].isin([-1, 0, 1, 2, 3, 4, 5, 6, 7])].copy()

    # Merge demographics/primary language.
    resp = resp.merge(participants, on="participant_id", how="left")

    # Derived ISO coordinates from PAQ1-PAQ8.
    iso_p, iso_e = iso_coords_from_paq(resp)
    resp["ISOPleasant"] = iso_p.round(6)
    resp["ISOEventful"] = iso_e.round(6)

    # Clip key (unique augmented stimulus).
    key_cols = ["fold_r", "soundscape", "masker", "smr_db"]
    clip_keys = (
        resp[key_cols]
        .drop_duplicates()
        .sort_values(key_cols)
        .reset_index(drop=True)
        .copy()
    )
    clip_keys["clip_id"] = [f"ARAUS_{i:06d}" for i in range(1, len(clip_keys) + 1)]
    clip_keys["split"] = clip_keys["fold_r"].map(lambda f: map_split(int(f), args.dev_fold))
    clip_keys["is_common_stimulus"] = clip_keys["fold_r"] == -1
    clip_keys["dataset_id"] = "ARAUS"
    clip_keys["audio_asset"] = ""
    clip_keys["video_asset_id"] = (
        clip_keys["soundscape"]
        .astype(str)
        .str.replace(r"\\.wav$", "", regex=True)
        .str.replace(r"_segment_.*$", "", regex=True)
        + "_360"
    )
    clip_keys["video_asset"] = clip_keys["video_asset_id"]
    clip_keys["start_s"] = 0.0
    clip_keys["end_s"] = 30.0
    clip_keys["licence_spdx"] = "Other"

    resp = resp.merge(clip_keys[key_cols + ["clip_id"]], on=key_cols, how="left")
    if resp["clip_id"].isna().any():
        raise RuntimeError("Some response rows could not be assigned a clip_id")

    # Response IDs are stable using participant and stimulus index.
    resp["response_id"] = (
        "ARAUS_"
        + resp["participant_id"].astype(str)
        + "_S"
        + resp["stimulus_index"].astype(int).astype(str).str.zfill(2)
    )

    # Build clips (aggregated means over responses per clip).
    clip_agg = (
        resp.groupby("clip_id", as_index=False)
        .agg(
            n_responses=("participant_id", "size"),
            mean_PAQ1_pleasant=("PAQ1_pleasant", "mean"),
            mean_PAQ2_vibrant=("PAQ2_vibrant", "mean"),
            mean_PAQ3_eventful=("PAQ3_eventful", "mean"),
            mean_PAQ4_chaotic=("PAQ4_chaotic", "mean"),
            mean_PAQ5_annoying=("PAQ5_annoying", "mean"),
            mean_PAQ6_monotonous=("PAQ6_monotonous", "mean"),
            mean_PAQ7_uneventful=("PAQ7_uneventful", "mean"),
            mean_PAQ8_calm=("PAQ8_calm", "mean"),
            mean_appropriate=("appropriate", "mean"),
            mean_ISOPleasant=("ISOPleasant", "mean"),
            mean_ISOEventful=("ISOEventful", "mean"),
            LAeq_dBA=("LAeq_dBA", "mean"),
            loudness_N_sone=("loudness_N_sone", "mean"),
            sharpness_S_acum=("sharpness_S_acum", "mean"),
            roughness_R_asper=("roughness_R_asper", "mean"),
            fluctuation_strength_F_vacil=("fluctuation_strength_F_vacil", "mean"),
            tonality_T_tu=("tonality_T_tu", "mean"),
        )
    )

    clips = clip_keys.merge(clip_agg, on="clip_id", how="left")
    clip_out_cols = [
        "clip_id",
        "dataset_id",
        "fold_r",
        "split",
        "soundscape",
        "masker",
        "smr_db",
        "is_common_stimulus",
        "audio_asset",
        "video_asset",
        "video_asset_id",
        "start_s",
        "end_s",
        "licence_spdx",
        "n_responses",
        "mean_PAQ1_pleasant",
        "mean_PAQ2_vibrant",
        "mean_PAQ3_eventful",
        "mean_PAQ4_chaotic",
        "mean_PAQ5_annoying",
        "mean_PAQ6_monotonous",
        "mean_PAQ7_uneventful",
        "mean_PAQ8_calm",
        "mean_appropriate",
        "mean_ISOPleasant",
        "mean_ISOEventful",
        "LAeq_dBA",
        "loudness_N_sone",
        "sharpness_S_acum",
        "roughness_R_asper",
        "fluctuation_strength_F_vacil",
        "tonality_T_tu",
    ]
    clips = clips[clip_out_cols].copy()

    responses = resp[
        [
            "response_id",
            "clip_id",
            "participant_id",
            "fold_r",
            "stimulus_index",
            "time_taken_s",
            "is_attention",
            "language",
            "age",
            "gender",
            "PAQ1_pleasant",
            "PAQ2_vibrant",
            "PAQ3_eventful",
            "PAQ4_chaotic",
            "PAQ5_annoying",
            "PAQ6_monotonous",
            "PAQ7_uneventful",
            "PAQ8_calm",
            "appropriate",
            "ISOPleasant",
            "ISOEventful",
            "LAeq_dBA",
            "loudness_N_sone",
            "sharpness_S_acum",
            "roughness_R_asper",
            "fluctuation_strength_F_vacil",
            "tonality_T_tu",
        ]
    ].copy()

    # Ensure unique response IDs; if duplicates exist, append row index.
    if responses["response_id"].duplicated().any():
        dup_mask = responses["response_id"].duplicated(keep=False)
        suffix = (
            responses[dup_mask]
            .groupby("response_id")
            .cumcount()
            .astype(str)
            .str.zfill(2)
        )
        responses.loc[dup_mask, "response_id"] = (
            responses.loc[dup_mask, "response_id"] + "_R" + suffix.values
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    clips.to_csv(args.out_dir / "clips.csv", index=False)
    responses.to_csv(args.out_dir / "responses.csv", index=False)

    print(f"Built clips.csv: {len(clips)} rows -> {args.out_dir / 'clips.csv'}")
    print(f"Built responses.csv: {len(responses)} rows -> {args.out_dir / 'responses.csv'}")


if __name__ == "__main__":
    main()
