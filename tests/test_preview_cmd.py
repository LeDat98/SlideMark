"""LibreOffice command line: valid profile URL on every OS, executable found outside PATH."""

from __future__ import annotations

import subprocess
from pathlib import Path, PureWindowsPath

import pytest

from slidemark import preview


def test_profile_is_a_valid_file_url(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        (tmp_path / "out" / "d.pdf").write_bytes(b"%PDF")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(preview.subprocess, "run", fake_run)
    preview.pptx_to_pdf(tmp_path / "d.pptx", tmp_path / "out")
    arg = next(a for a in seen["cmd"] if a.startswith("-env:UserInstallation="))
    assert arg.startswith("-env:UserInstallation=file:///")  # "file://C:\\..." breaks LibreOffice on Windows


def test_windows_profile_url_shape():
    url = PureWindowsPath(r"C:\Users\me\AppData\Local\Temp\slidemark-lo-1").as_uri()
    assert url == "file:///C:/Users/me/AppData/Local/Temp/slidemark-lo-1"


def test_find_soffice_env_override(monkeypatch, tmp_path):
    exe = tmp_path / "soffice.exe"
    exe.write_text("")
    monkeypatch.setenv("SLIDEMARK_SOFFICE", str(exe))
    assert preview.find_soffice() == str(exe)


def test_find_soffice_default_install_folder(monkeypatch, tmp_path):
    exe = tmp_path / "LibreOffice" / "program" / "soffice.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    monkeypatch.delenv("SLIDEMARK_SOFFICE", raising=False)
    monkeypatch.setattr(preview.shutil, "which", lambda name: None)
    monkeypatch.setattr(preview, "_KNOWN", [Path(exe)])
    assert preview.find_soffice() == str(exe)
    assert preview.have_soffice()


@pytest.mark.skipif(preview.find_soffice() is None, reason="LibreOffice not installed")
def test_real_conversion_still_works(tmp_path):
    from slidemark.build import build

    build("# Hello\n- one\n", tmp_path / "a.pptx")
    assert preview.pptx_to_pdf(tmp_path / "a.pptx", tmp_path).exists()
