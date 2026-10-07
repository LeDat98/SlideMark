"""The preview fontconfig file: well-formed, maps Office / brand families, is passed to LibreOffice."""

import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from slidemark import preview


def _prefer() -> dict[str, list[str]]:
    root = ET.parse(preview.FONTS_CONF).getroot()
    return {a.findtext("family"): [f.text for f in a.find("prefer")] for a in root.iter("alias")}


def test_fonts_conf_maps_office_families():
    p = _prefer()
    for cjk in ("Meiryo", "Yu Gothic", "MS PGothic", "Hiragino Sans"):
        assert p[cjk][0] == "IPAPGothic"
    assert p["MS Gothic"][0] == "IPAGothic"
    for sans in ("Arial", "Inter", "Montserrat", "Helvetica"):
        assert p[sans][0] == "Liberation Sans"
    for serif in ("Georgia", "Times New Roman"):
        assert p[serif][0] == "Liberation Serif"
    assert p["sans-serif"][0] == "Liberation Sans"


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="fontconfig is a Linux thing")
def test_pptx_to_pdf_passes_the_conf(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, **kw):
        seen.append(kw["env"].get("FONTCONFIG_FILE"))
        (tmp_path / "x.pdf").write_bytes(b"%PDF")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(preview.subprocess, "run", fake_run)
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    (tmp_path / "x.pptx").write_bytes(b"")
    preview.pptx_to_pdf(tmp_path / "x.pptx", tmp_path)
    monkeypatch.setenv("FONTCONFIG_FILE", "/my/own.conf")
    preview.pptx_to_pdf(tmp_path / "x.pptx", tmp_path)
    assert seen == [str(preview.FONTS_CONF), "/my/own.conf"]
