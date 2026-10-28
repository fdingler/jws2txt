import json
import os
import unittest
import jws2txt


class TestMetadata(unittest.TestCase):

    def setUp(self) -> None:
        self.hg_file = jws2txt.JWSFile(r"tests/files/001Hg.jws")
        self.jwb_file = jws2txt.JWSFile(r"tests/files/2022_05_14-1.jwb")
        self.fl_file = jws2txt.JWSFile(r"tests/files/sample_fluorescence.jws")
        self.cd_file = jws2txt.JWSFile(r"tests/files/sample_CD_HT_Abs.jws")
        self.test_txt = "test_out.txt"
        self.test_json = "test_out.json"

    def tearDown(self) -> None:
        for path in (self.test_txt, self.test_json):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_metadata_structure(self):
        meta = self.hg_file.metadata
        self.assertIn("file_info", meta)
        self.assertIn("instrument", meta)
        self.assertIn("software", meta)
        self.assertIn("operator", meta)
        self.assertIn("sample", meta)
        self.assertIn("parameters", meta)

        self.assertEqual(meta["instrument"]["model"], "J-1500")
        self.assertEqual(meta["instrument"]["serial_number"], "A005461638")
        self.assertEqual(meta["operator"]["institution"], "Uniwersytet Wroclawski")
        self.assertEqual(meta["sample"]["name"], "HK14_CN")
        self.assertEqual(meta["sample"]["comment"], "1mm")
        self.assertEqual(meta["sample"]["description"], "TRIS 10mM NaF 5mM CN 50uM Hk14")
        self.assertEqual(meta["parameters"]["sensitivity"], "200 mdeg/1.0 dOD")
        self.assertEqual(meta["parameters"]["bandwidth"], "2.00 nm")
        self.assertEqual(meta["parameters"]["response"], "2 sec")
        self.assertEqual(meta["parameters"]["scanning_speed"], "200 nm/min")

    def test_sample_names_populated_from_metadata(self):
        self.assertEqual(self.hg_file.sample_name, "HK14_CN")
        self.assertEqual(self.hg_file.comment, "1mm")
        self.assertEqual(self.fl_file.sample_name, "photonic wire")
        self.assertEqual(self.fl_file.comment, "")
        self.assertEqual(self.cd_file.sample_name, "1A")
        self.assertEqual(self.cd_file.comment, "")
        self.assertEqual(self.jwb_file.sample_name, "")
        self.assertEqual(self.jwb_file.comment, "")

    def test_jwb_multi_scan_metadata(self):
        meta = self.jwb_file.metadata
        self.assertEqual(meta["instrument"]["model"], "V-730")
        self.assertEqual(meta["instrument"]["serial_number"], "B184861798")
        self.assertEqual(meta["operator"]["institution"], "北海道大学")

        temp_ctrl = meta["parameters"].get("temperature_control", {})
        self.assertEqual(temp_ctrl.get("scans"), 8)
        self.assertEqual(temp_ctrl.get("start_temperature"), 25.0)
        self.assertEqual(temp_ctrl.get("end_temperature"), 60.0)
        self.assertEqual(len(temp_ctrl.get("scan_temperatures", [])), 8)
        self.assertAlmostEqual(temp_ctrl["scan_temperatures"][0], 24.98, places=1)
        self.assertAlmostEqual(temp_ctrl["scan_temperatures"][-1], 60.01, places=1)

    def test_metadata_default_off(self):
        # By default metadata=False, so no # comments and only comments + column headers + data
        self.hg_file.write_data(self.test_txt, write_comments=True, write_header=True)
        with open(self.test_txt, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        self.assertEqual(lines[0], "HK14_CN")
        self.assertEqual(lines[1], "1mm")
        self.assertTrue(lines[2].startswith("WAVELENGTH"))
        self.assertFalse(any(l.startswith("# ") for l in lines))
        self.assertFalse(os.path.exists(self.test_json))

    def test_metadata_header_mode(self):
        # metadata="header": writes #-prefixed metadata at the very top
        self.hg_file.write_data(self.test_txt, write_comments=True, write_header=True, metadata="header")
        with open(self.test_txt, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        self.assertTrue(lines[0].startswith("# --- Measurement Information ---"))
        header_comments = [l for l in lines if l.startswith("# ")]
        self.assertTrue(any("J-1500" in l for l in header_comments))
        self.assertTrue(any("Uniwersytet Wroclawski" in l for l in header_comments))

        # Sample comments appear after metadata header
        first_non_hash = next(i for i, l in enumerate(lines) if not l.startswith("# "))
        self.assertEqual(lines[first_non_hash], "HK14_CN")
        self.assertEqual(lines[first_non_hash + 1], "1mm")
        self.assertTrue(lines[first_non_hash + 2].startswith("WAVELENGTH"))

        # No json sidecar produced in "header" mode
        self.assertFalse(os.path.exists(self.test_json))

    def test_metadata_json_mode(self):
        # metadata="json": writes companion json, but no # comments in text file
        self.hg_file.write_data(self.test_txt, write_comments=True, write_header=True, metadata="json")
        with open(self.test_txt, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        self.assertEqual(lines[0], "HK14_CN")
        self.assertFalse(any(l.startswith("# ") for l in lines))

        self.assertTrue(os.path.exists(self.test_json))
        with open(self.test_json, "r", encoding="utf-8") as f:
            saved_meta = json.load(f)
        self.assertEqual(saved_meta["instrument"]["model"], "J-1500")

    def test_metadata_both_mode(self):
        # metadata="both": writes both #-prefixed header comments and json sidecar
        self.hg_file.write_data(self.test_txt, write_comments=True, write_header=True, metadata="both")
        with open(self.test_txt, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        self.assertTrue(lines[0].startswith("# --- Measurement Information ---"))
        self.assertTrue(os.path.exists(self.test_json))

    def test_column_header_flag(self):
        # write_header=False suppresses column headers row
        self.hg_file.write_data(self.test_txt, write_comments=True, write_header=False, metadata=False)
        with open(self.test_txt, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        self.assertEqual(lines[0], "HK14_CN")
        self.assertEqual(lines[1], "1mm")
        self.assertFalse(any("WAVELENGTH" in l for l in lines))


if __name__ == "__main__":
    unittest.main()
