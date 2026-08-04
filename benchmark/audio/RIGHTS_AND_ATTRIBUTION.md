# ISD audio rights and attribution

## Source

- Dataset: The International Soundscape Database
- Record: <https://doi.org/10.5281/zenodo.10672568>
- Version used by MOSAIQ: `1.0.1-alpha.1`
- Record publication date: 16 February 2024
- Publisher: Zenodo
- Licence declared by the record API: CC BY 4.0

The record description states that all ISD recordings are provided under CC BY
4.0 and encourages reuse of both recordings and perceptual data with proper
attribution. The source record remains authoritative.

## Creators

Andrew Mitchell; Tin Oberman; Francesco Aletta; Mercede Erfanian; Magdalena
Kachlicka; Matteo Lionello; Xiang Fang; Jian Kang.

## MOSAIQ attribution text

> ISD audio was obtained from Mitchell et al., *The International Soundscape
> Database: An integrated multimedia database of urban soundscape surveys*,
> version 1.0.1-alpha.1, Zenodo,
> https://doi.org/10.5281/zenodo.10672568, licensed CC BY 4.0.

MOSAIQ must also cite the SSID protocol publication identified by the source
record. Any public archive must retain the DOI, version, licence, creators,
archive names, and source MD5 checksums in
`benchmark/governance/isd_zenodo_source_registry.csv`.

## Scope boundary

This review covers assets distributed by the cited ISD record. It does not
grant rights to ARAUS, SATP, DeLTA, or unrelated upstream media. It records the
source licence and is not legal advice.

## Observed technical discrepancy

The record description characterises the binaural WAV files as 32-bit
floating-point. The 51 usable Groningen WAV files inspected on 30 July 2026
are 48 kHz, stereo, `int16`. MOSAIQ detects the actual encoding per file and
does not assume a dtype from the prose description.
