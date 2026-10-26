import contextlib
import io
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from helpers import setup_check


class TestSetupCheck(TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.dos, self.baked = root / "dos", root / "baked"
        self.dos.mkdir()
        self.baked.mkdir()
        patcher = mock.patch.multiple(setup_check, DOS_DIR=self.dos, BAKED_DIR=self.baked)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_check(self, check):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ok = check()
        return ok, err.getvalue()

    def add_game_files(self):
        for f in setup_check.REQUIRED_GAME_FILES:
            (self.dos / f).touch()

    def test_nothing_present(self):
        ok, banner = self.run_check(setup_check.check_can_bake)
        self.assertFalse(ok)
        self.assertIn("DARK.CC", banner)

        ok, banner = self.run_check(setup_check.check_can_serve)
        self.assertFalse(ok)
        self.assertIn("Step 1", banner)
        self.assertIn("just bake", banner)

    def test_game_files_but_not_baked(self):
        self.add_game_files()
        self.assertEqual(self.run_check(setup_check.check_can_bake), (True, ""))

        ok, banner = self.run_check(setup_check.check_can_serve)
        self.assertFalse(ok)
        self.assertNotIn("Step 1", banner)
        self.assertIn("Run:  just bake", banner)

    def test_baked(self):
        for p in setup_check.REQUIRED_PACKS:
            (self.baked / p).mkdir()
            (self.baked / p / "info.json").touch()
        # the game files are not needed once baked
        self.assertEqual(self.run_check(setup_check.check_can_serve), (True, ""))

    def test_failed_bake_is_not_baked(self):
        for p in setup_check.REQUIRED_PACKS:
            (self.baked / p).mkdir()
        ok, _ = self.run_check(setup_check.check_can_serve)
        self.assertFalse(ok)
