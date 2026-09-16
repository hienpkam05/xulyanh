# Image API benchmark report

## Environment

- Timestamp (UTC): 2026-08-25T08:22:23.791888+00:00
- Platform: Windows-11-10.0.26200-SP0
- CPU logical cores: 8
- Memory: 16895107072 bytes
- Python: 3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)]
- pyvips / libvips: 3.1.1 / 8.18.5
- Measured runs per profile: 1 (after 0 warm-up run(s))

## Input manifest

| Profile | Dimensions | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| 2k | 2048×1024 | 97610 | `0a9d90590ad29debb541dc80dc6c9339b16eeb030d6e0fa2acf2b44585397ef6` |

## Measured summary

Processing time equals POST latency because this baseline completes all five variants synchronously before responding.

| Profile | POST median/max (ms) | Peak RSS median/max (bytes) | Storage median/max (bytes) | Files median/max | GET first median/max (ms) | GET second median/max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2k | 312.987/312.987 | 94474240/94474240 | 113008/113008 | 6/6 | 13.01/13.01 | 3.278/3.278 |

Raw samples are in `samples.json`; this run removes processed assets after collecting metrics.
