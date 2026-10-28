import csv
import json
import os
from struct import unpack
from typing import Any, Iterator, Optional, Union

import olefile as ofio

from .metadata import extract_metadata, format_metadata_header

DATAINFO_FMT = "<LLLLLLdddLLLLdddd"

CHANNELS_DEFINITIONS = {
    536871427: "TIME",
    268435715: "WAVELENGTH",
    4097: "CD",
    8193: "HT VOLTAGE",
    3: "ABSORBANCE",
    14: "FLUORESCENCE",
}


def frange(
    start: float, stop: float = 0, step: float = 1.0
) -> Iterator[float]:
    """Return evenly spaced number over specified range.

    Args:
        start (float): The starting value of the sequence.
        stop (float): The last value of the sequence.
        step (float): The step for which the sequence is generated.
    """

    count = 0
    while True:
        range = start + count * step
        if step > 0 and range >= stop:
            break
        elif step < 0 and range <= stop:
            break
        yield range
        count += 1


class JWSFile:
    """Representation of the JASCO JWS or JWB file."""

    def __init__(self, path: str) -> None:
        """Initializes the JWSFile class.

        Args:
           path (str): PAtj tp JWS or JWB file
        """
        file = ofio.olefile.OleFileIO(path)

        data_info = file.openstream("DataInfo").read()

        if (len(data_info)) < 96:
            raise Exception("DataInfo should be at least 96 bytes!")

        data_info = data_info[:96]
        data_tuple = unpack(DATAINFO_FMT, data_info)
        self.numchanels = data_tuple[3]
        self.npoints = data_tuple[5]
        self.x_for_first_point = data_tuple[6]
        self.x_for_last_point = data_tuple[7]
        self.x_increment = data_tuple[8]

        if not isinstance(self.npoints, int) or self.npoints < 2:
            raise ValueError("Invalid npoints.")

        if self.x_increment in (None, 0):
            span = self.x_for_last_point - self.x_for_first_point
            if span == 0:
                raise ValueError(
                    "Cannot compute x_increment: identical first/last points."
                )

            self.x_increment = span / (self.npoints - 1)

        self.header_codes = tuple(
            [
                x
                for i, x in enumerate(data_tuple[9:13])
                if x not in data_tuple[9:13][:i]
            ]
        )

        self.header_names = [
            CHANNELS_DEFINITIONS.get(k, "undefined") for k in self.header_codes
        ]

        self.data_list = list(data_tuple)

        if not file.exists("Y-Data"):
            raise Exception("Y-Data not found!")

        y_data = file.openstream("Y-Data").read()
        # Each JASCO spectrum consists of npoints float32 values. Some JWB
        # files store scan_count * signal_count spectra (signal-major order).
        bytes_per_spectrum = self.npoints * 4
        if not bytes_per_spectrum or len(y_data) % bytes_per_spectrum:
            raise ValueError("Invalid Y-Data length for float32 spectra")
        stored_spectra = len(y_data) // bytes_per_spectrum
        scan_count, signal_count = data_tuple[1], data_tuple[3]
        allowed = {signal_count, scan_count, scan_count * signal_count}
        if stored_spectra not in allowed or stored_spectra <= 0:
            raise ValueError(
                f"Y-Data contains {stored_spectra} spectra, but DataInfo "
                f"declares {scan_count} scans and {signal_count} signals"
            )
        self.numchanels = stored_spectra
        self.__unpack_y_data(
            y_data, format="<" + "f" * self.npoints,
            num_chanels=stored_spectra
        )
        # Preserve ordinary JWS header behaviour. For multi-scan JWB,
        # use neutral labels: DataInfo does not establish whether the
        # independent variable is temperature, concentration, or something else.
        if (scan_count > 1 and signal_count > 1 and
                stored_spectra == scan_count * signal_count):
            codes = data_tuple[10:10 + signal_count]
            self.header_names = ["WAVELENGTH"]
            for i in range(signal_count):
                signal = CHANNELS_DEFINITIONS.get(
                    codes[i], f"Signal_{i + 1}"
                )
                for scan in range(scan_count):
                    self.header_names.append(f"{signal}_scan{scan + 1}")

        self.metadata = extract_metadata(
            ole=file,
            npoints=self.npoints,
            x_first=self.x_for_first_point,
            x_last=self.x_for_last_point,
            x_increment=self.x_increment,
            header_names=self.header_names,
            scan_count=scan_count,
        )

        sample_meta = self.metadata.get("sample", {})
        self.sample_name = sample_meta.get("name", "")
        self.comment = sample_meta.get("comment", "")

        file.close()

    def __unpack_y_data(
        self, y_data: bytes, format: str, num_chanels: int
    ) -> None:
        """Unpacks the Y-Data from the JWS file."""
        chunk_size = int(len(y_data) / num_chanels)
        data_chunked = [
            y_data[i : i + chunk_size]
            for i in range(0, len(y_data), chunk_size)
        ]
        unpacked_data = [
            unpack(format, data_chunk) for data_chunk in data_chunked
        ]
        # generate x_data
        x_data = frange(
            self.x_for_first_point,
            self.x_for_last_point + self.x_increment,
            self.x_increment,
        )

        unpacked_data.insert(0, tuple(x_data))
        self.unpacked_data = unpacked_data

    def write_data(
        self,
        out_file: Union[str, os.PathLike, Any],
        write_comments: bool = True,
        write_header: bool = True,
        delimiter: str = "\t",
        metadata: Union[str, bool] = False,
        json_path: Optional[str] = None,
    ) -> None:
        """Writes spectral data to a text file and optionally writes metadata.

        Args:
            out_file: Target file path or writable stream.
            write_comments: Write sample name and comment rows (default True).
            write_header: Write column header row (default True).
            delimiter: Column delimiter (default tab).
            metadata: Metadata output mode: 'header' (prefixed comment lines at top of file),
                      'json' (companion sidecar json file), 'both' (both header and json),
                      or False/'none' (default, no metadata).
            json_path: Explicit path for the metadata JSON file (if json output requested).
        """
        values = list(zip(*self.unpacked_data))

        meta_mode = str(metadata).strip().lower()
        write_meta_header = meta_mode in ("header", "both", "true")
        write_meta_json = meta_mode in ("json", "both")

        def _write_content(writer):
            if write_meta_header:
                for line in format_metadata_header(self.metadata):
                    writer.writerow([line])

            if write_comments is True:
                writer.writerow([self.sample_name])
                writer.writerow([self.comment])

            if write_header is True:
                if len(self.header_names) == len(self.unpacked_data):
                    writer.writerow(self.header_names)
                elif len(self.header_names) < len(self.unpacked_data):
                    diff = len(self.unpacked_data) - len(self.header_names)
                    self.header_names.extend(
                        [self.header_names[-1]] * diff
                    )
                    writer.writerow(self.header_names)

            writer.writerows(values)

        if hasattr(out_file, "write"):
            writer = csv.writer(out_file, delimiter=delimiter)
            _write_content(writer)
        else:
            try:
                with open(out_file, "x", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f, delimiter=delimiter)
                    _write_content(writer)
            except FileExistsError:
                print(f"Error: File '{out_file}' already exists.")

        if write_meta_json:
            target_json = json_path
            if not target_json and isinstance(out_file, (str, os.PathLike)):
                target_json = os.path.splitext(out_file)[0] + ".json"
            if target_json:
                self.write_metadata_json(target_json)

    def write_metadata_json(self, out_file: str, indent: int = 2) -> None:
        """Writes metadata as a JSON file."""
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=indent, ensure_ascii=False)
