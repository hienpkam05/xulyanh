# Image API benchmark report

## Environment

- Timestamp (UTC): 2026-08-25T08:22:41.288298+00:00
- Platform: Windows-11-10.0.26200-SP0
- CPU logical cores: 8
- Memory: 16895107072 bytes
- Python: 3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)]
- pyvips / libvips: 3.1.1 / 8.18.5
- Measured runs per profile: 3 (after 1 warm-up run(s))

## Input manifest

| Profile | Dimensions | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| 2k | 2048×1024 | 97610 | `0a9d90590ad29debb541dc80dc6c9339b16eeb030d6e0fa2acf2b44585397ef6` |
| 4k | 4096×2048 | 310538 | `70461774d75aeaee5220a4dab7dcb91771426e18e8a55cb8dd1244a0d925c1f9` |
| 8k | 8192×4096 | 1080458 | `b2d67f521e3dea32d66625de7588e02e2956d10924fe507f63b8f3441fe46d7d` |
| 12k | 12000×6000 | 2207745 | `df1c9033354aa12e050397e5bfa1d0d100d136149318d7e707eaf58f0f52f1aa` |

## Measured summary

Processing time equals POST latency because this baseline completes all five variants synchronously before responding.

| Profile | POST median/max (ms) | Peak RSS median/max (bytes) | Storage median/max (bytes) | Files median/max | GET first median/max (ms) | GET second median/max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2k | 319.906/350.79 | 97632256/99110912 | 113008/113008 | 6/6 | 2.791/4.146 | 2.921/3.608 |
| 4k | 360.15/367.196 | 125214720/127623168 | 322918/322918 | 6/6 | 3.011/3.066 | 2.827/2.955 |
| 8k | 809.295/846.935 | 184905728/203018240 | 1090978/1090978 | 6/6 | 2.791/3.496 | 2.821/3.594 |
| 12k | 1323.615/1376.482 | 263860224/266211328 | 2216825/2216825 | 6/6 | 2.955/4.19 | 3.066/4.53 |

Raw samples are in `samples.json`; this run removes processed assets after collecting metrics.
