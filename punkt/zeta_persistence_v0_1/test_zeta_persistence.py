import os
import unittest
from unittest.mock import patch

import zeta_persistence as zp


class ZetaPersistenceTests(unittest.TestCase):
    def test_document_fingerprint_is_locked(self) -> None:
        self.assertEqual(
            (zp.PAGES, zp.SECTIONS, zp.APPENDICES, zp.EQUATIONS),
            (71, 8, 2, 190),
        )
        self.assertEqual(len(zp.PRIMES), zp.SECTIONS)

    def test_phase_does_not_close_over_probe_window(self) -> None:
        phases = [zp.system_phase(frame) for frame in range(512)]
        rounded = {round(value, 12) for value in phases}
        self.assertEqual(len(rounded), len(phases))

    def test_zero_lattice_is_deterministic(self) -> None:
        first = [zp.zero_location(index, 7.25) for index in range(-4, 5)]
        second = [zp.zero_location(index, 7.25) for index in range(-4, 5)]
        self.assertEqual(first, second)

    def test_fixed_terminal_render_is_deterministic(self) -> None:
        fixed = os.terminal_size((80, 24))
        with patch.object(zp.shutil, "get_terminal_size", return_value=fixed):
            first = zp.render(19)
            second = zp.render(19)
        self.assertEqual(first, second)
        self.assertIn("PERSISTENCE WITHOUT RECURRENCE", first)
        self.assertIn("NO FIXED POINT", first)

    def test_time_changes_the_field(self) -> None:
        fixed = os.terminal_size((80, 24))
        with patch.object(zp.shutil, "get_terminal_size", return_value=fixed):
            frame_zero = zp.render(0)
            frame_one = zp.render(1)
        self.assertNotEqual(frame_zero, frame_one)


if __name__ == "__main__":
    unittest.main()
