# jws2txt

A program to convert binary JASCO SpectraManager (JWS and JWB) files to text files.

## Introduction
------------
jws2txt is a simple command line tool that allows for the conversion of JWS and JWB files from JASCO SpectraManager software to text files. These text files can be used in any data analysis workflows and software.

Unlike JASCO SpectraManager software, jws2txt enables batch conversion of JWS/JWB files.

Data unpacking is based on Víctor M. Hernández-Rocamora's jwsProcessor (https://github.com/vhernandez/jwsProcessor).

## Installation and Usage
------------
1. Download Python (>= 3.8).
2. Install with `pip install jws2txt` (or install dependencies via `pip install -r requirements.txt`).
3. To convert files via the command line:
   ```bash
   jws2txt --in-path <path_to_folder> --out-dir <output_folder_path>
   ```

### Command Line Options

- `--in-path`: Path to folder containing files for conversion (required).
- `--out-dir`: Destination folder for converted files (defaults to `--in-path`).
- `--delimiter`: Delimiter used in saved text files (default: `\t`).
- `--comments`: Write sample name and comments (`True` or `False`, default: `True`).
- `--header`: Write column headers row, e.g. `WAVELENGTH\tCD` (`True` or `False`, default: `True`).
- `--metadata`: Export metadata: `'none'` (default), `'header'` (writes `#`-prefixed comment lines at the top of the text file), `'json'` (generates a companion `.json` sidecar file), or `'both'`.

### Python API

```python
from jws2txt import JWSFile

# Load JWS or multi-scan JWB file
jws = JWSFile("path/to/spectrum.jwb")

# Access sample information and metadata dictionary
print(jws.sample_name, jws.comment)
print(jws.metadata["instrument"])
print(jws.metadata["parameters"])

# Export spectral data with metadata
# metadata options: False/'none', 'header', 'json', or 'both'
jws.write_data("spectrum.txt", write_comments=True, write_header=True, metadata="both")

# Or export JSON sidecar directly
jws.write_metadata_json("spectrum.json")
```
