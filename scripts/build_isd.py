"""Regenerate clips.csv and responses.csv directly from ISD CSV."""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "source_data" / "ISD" / "ISD_v1_0_Data.csv"
OUT_DIR = ROOT / "datasets" / "ISD" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)

# PAQ columns: ISO order
PAQ_MAP = {
    "PAQ1_pleasant":   "pleasant",
    "PAQ2_vibrant":    "vibrant",
    "PAQ3_eventful":   "eventful",
    "PAQ4_chaotic":    "chaotic",
    "PAQ5_annoying":   "annoying",
    "PAQ6_monotonous": "monotonous",
    "PAQ7_uneventful": "uneventful",
    "PAQ8_calm":       "calm",
}

def iso_coords(p):
    """Compute ISOPleasant/ISOEventful from PAQ dict (renamed)."""
    try:
        pl = (p["PAQ1_pleasant"] - p["PAQ5_annoying"]) + np.cos(np.pi/4) * (
             (p["PAQ8_calm"] - p["PAQ4_chaotic"]) + (p["PAQ2_vibrant"] - p["PAQ6_monotonous"]))
        ev = (p["PAQ3_eventful"] - p["PAQ7_uneventful"]) + np.cos(np.pi/4) * (
             (p["PAQ4_chaotic"] - p["PAQ8_calm"]) + (p["PAQ2_vibrant"] - p["PAQ6_monotonous"]))
        return round(pl / (4 + np.sqrt(32)), 4), round(ev / (4 + np.sqrt(32)), 4)
    except Exception:
        return None, None

# ==============================================================
# 1. responses.csv  (one row per participant response)
# ==============================================================
responses = []
for _, row in df.iterrows():
    clip_id = f"ISD_{row['LocationID']}_{row['SessionID']}_{row['GroupID']}"
    paqs = {std: (int(row[src]) if pd.notna(row[src]) else None)
            for std, src in PAQ_MAP.items()}
    iso_p, iso_e = (iso_coords(paqs)
                    if all(v is not None for v in paqs.values())
                    else (None, None))
    responses.append({
        "response_id":   f"{clip_id}_R{row['RecordID']}",
        "clip_id":       clip_id,
        "participant_id": str(row["RecordID"]),
        "language":      row.get("Language"),
        **paqs,
        "ISOPleasant":   iso_p,
        "ISOEventful":   iso_e,
        "age":           row.get("age00"),
        "gender":        row.get("gen00"),
    })

resp_df = pd.DataFrame(responses)
resp_df.to_csv(OUT_DIR / "responses.csv", index=False)

# ==============================================================
# 2. clips.csv  (one row per clip = GroupID-aggregated)
# ==============================================================
clips = []
for (loc, sess, grp), g in df.groupby(["LocationID", "SessionID", "GroupID"]):
    clip_id = f"ISD_{loc}_{sess}_{grp}"
    r0 = g.iloc[0]

    means = {f"mean_PAQ{i}_{name}": round(g[name].mean(), 3)
             for i, name in enumerate(
                 ["pleasant","vibrant","eventful","chaotic",
                  "annoying","monotonous","uneventful","calm"], start=1)
             if g[name].notna().any()}

    # ISO from means
    if len(means) == 8:
        m = {k.replace("mean_", ""): v for k, v in means.items()}
        iso_p, iso_e = iso_coords(m)
    else:
        iso_p = iso_e = None

    clips.append({
        "clip_id":          clip_id,
        "dataset_id":       "ISD",
        "LocationID":       loc,
        "SessionID":        sess,
        "GroupID":          grp,
        "latitude":         r0.get("latitude"),
        "longitude":        r0.get("longitude"),
        "binaural_start_s": 0.0,
        "binaural_end_s":   r0.get("RecordingLength"),
        "audio_asset":      f"ISD_{loc}_{grp}_binaural",
        "video_asset":      f"ISD_{loc}_{sess}_360",
        "video_asset_id":   f"ISD_{loc}_{sess}_360",
        "start_s":          0.0,
        "end_s":            r0.get("RecordingLength"),
        "split":            "",  # to be filled later by site-balanced splitter
        "licence_spdx":     "CC-BY-4.0",
        "n_responses":      len(g),
        **means,
        "mean_ISOPleasant": iso_p,
        "mean_ISOEventful": iso_e,
        "LAeq_dBA":         r0.get("LAeq_L(A)"),
        "loudness_N_sone":  r0.get("N_N5"),
        "sharpness_S_acum": r0.get("S_S"),
        "roughness_R_asper": r0.get("R_R"),
        "fluctuation_strength_F_vacil": r0.get("FS_F"),
        "tonality_T_tu":    r0.get("T_TonalityHMS"),
    })

pd.DataFrame(clips).to_csv(OUT_DIR / "clips.csv", index=False)

print(f"responses.csv: {len(responses)} rows, {len(resp_df.columns)} columns")
print(f"clips.csv:     {len(clips)} rows, {len(clips[0])} columns")
