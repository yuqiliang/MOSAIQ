# Paper 2 legacy-draft integration audit

Status: **integrated and removed**
Legacy findings: **19**

The former repository working draft was audited before removal. It contained
19 stale triggers, including TODO markers, pre-release split counts, statements
that ISD/SATP/DeLTA still required splits, proposed rather than executed
baselines, and missing robustness evidence.

The replacement Word manuscript:

1. uses split version `0.1.0` and the fixed task/dataset counts;
2. reports the 17 executed no-audio tabular experiments without claiming full
   ARAUS or Tong-model replication;
3. incorporates Step 7 uncertainty, sensitivity, and calibration evidence;
4. preserves the no-audio scope and defers audio/visual/multimodal claims;
5. retains both validation warnings and the 48-record ARAUS test caveat; and
6. follows the current Scientific Data Data Descriptor section structure.

The removed Markdown file is no longer an input to the deterministic fixed-
output build. This audit is retained to document why it was deleted.
