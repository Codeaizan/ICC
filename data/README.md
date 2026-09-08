# Data directory

Keep downloaded scans outside version control. The root `.gitignore` excludes `data/raw/` and generated outputs.

For each dataset, record:

- provider and access URL;
- version and download date;
- license/terms of use;
- number of cases and split definition;
- file format and orientation convention;
- SHA-256 checksums for archives and atlas files.

AISD is the immediate development dataset. APIS access is a parallel registration task and should be added later as external validation. Do not place credentials, registration forms, or patient identifiers in this repository.

Use `manifests/aisd.example.csv` as the starting format. Remove its comment row before running batch processing, then verify every path exists.
