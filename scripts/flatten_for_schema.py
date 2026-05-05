"""
Flatten nested samples.jsonl → clips.csv for Frictionless schema inference.
We keep one row per clip with summary fields only; per-response detail
goes in a separate responses.csv.
"""
import json
import pandas as pd
from pathlib import Path

SRC = "/mnt/user-data/uploads/samples.jsonl"  # or your latest samples.jsonl
OUT_DIR = Path("/home/claude/mosaiq_frictionless/data/ISD")
OUT_DIR.mkdir(parents=True, exist_ok=True)

clips_rows = []
responses_rows = []

with open(SRC) as f:
    for line in f:
        c = json.loads(line)

        # --- clip-level summary row ---
        row = {
            "clip_id":         c["clip_id"],
            "dataset_id":      c["dataset_id"],
            "LocationID":      c["grouping"]["LocationID"],
            "SessionID":       c["grouping"]["SessionID"],
            "GroupID":         c["grouping"]["GroupID"],
            "latitude":        c["grouping"].get("latitude"),
            "longitude":       c["grouping"].get("longitude"),
            "binaural_start_s": c["segment"]["binaural_start_s"],
            "binaural_end_s":   c["segment"]["binaural_end_s"],
            "audio_asset":     c["assets"]["binaural_wav"],
            "video_asset":     c["assets"].get("video_360"),
            "split":           c.get("split"),
            "licence_spdx":    c["licence"]["spdx"],
            "n_responses":     c["perceptual_summary"]["n_responses"],
        }
        # mean PAQs
        for k, v in c["perceptual_summary"]["mean_PAQs"].items():
            row[f"mean_{k}"] = v
        row["mean_ISOPleasant"] = c["perceptual_summary"]["mean_ISOPleasant"]
        row["mean_ISOEventful"] = c["perceptual_summary"]["mean_ISOEventful"]
        # primary psychoacoustics
        psy = c["psychoacoustic"]
        for f_ in ["LAeq_dBA", "loudness_N_sone", "sharpness_S_acum",
                   "roughness_R_asper", "fluctuation_strength_F_vacil",
                   "tonality_T_tu"]:
            row[f_] = psy.get(f_)
        clips_rows.append(row)

        # --- response-level detail rows ---
        for r in c["perceptual_ratings"]:
            rrow = {
                "response_id":   r["response_id"],
                "clip_id":       c["clip_id"],
                "participant_id": r["participant_id"],
                "language":      r.get("language"),
            }
            if r.get("PAQs"):
                for k, v in r["PAQs"].items():
                    rrow[k] = v
            if r.get("derived_circumplex"):
                rrow["ISOPleasant"] = r["derived_circumplex"]["ISOPleasant"]
                rrow["ISOEventful"] = r["derived_circumplex"]["ISOEventful"]
            if r.get("demographics"):
                rrow["age"]    = r["demographics"].get("age")
                rrow["gender"] = r["demographics"].get("gender")
            responses_rows.append(rrow)

pd.DataFrame(clips_rows).to_csv(OUT_DIR / "clips.csv", index=False)
pd.DataFrame(responses_rows).to_csv(OUT_DIR / "responses.csv", index=False)
print(f"clips.csv:     {len(clips_rows)} rows")
print(f"responses.csv: {len(responses_rows)} rows")
