"""Contract tests for the public token schema (theme.py): presets are data, tokens apply, never raise."""

from slidemark.theme import (
    DEFAULT,
    JP_BUSINESS,
    PRESET_DIR,
    apply_tokens,
    available,
    canonical_token,
    get_theme,
    schema_table,
)


def test_presets_are_yaml_data():
    names = {p.stem for p in PRESET_DIR.glob("*.yaml")}
    assert {"default", "midnight", "jp-business"} <= names
    assert set(available()) >= names | {"none"}


def test_none_is_schema_defaults():
    none = get_theme("none")
    assert none.title_band is None and none.heading_band is None
    assert none.colors["primary"] != DEFAULT.colors["primary"]


def test_jp_business_band_is_a_token():
    assert JP_BUSINESS.title_band == "primary" and JP_BUSINESS.classes["card"].radius == 0


def test_apply_tokens_paths():
    th, diags = apply_tokens(
        DEFAULT,
        {
            "colors.brand": "#FF5A1F",
            "classes.hero.fill": "linear-gradient(135deg, #7C5CFF, #00D1B2)",
            "classes.card.shadow": "0 8 24 #00000055",
            "title_band": "brand",
            "layout.top_gap": "0.4in",
            "palette": "brand,primary",
            "sizes.body": "16",
        },
    )
    assert not diags
    assert th.colors["brand"] == "#FF5A1F" and th.title_band == "brand"
    assert th.classes["hero"].fill.startswith("linear-gradient")
    assert th.classes["card"].shadow == "0 8 24 #00000055" and th.classes["card"].radius == 6
    assert th.layout.top_gap == "0.4in" and th.palette == ["brand", "primary"] and th.sizes["body"] == 16


def test_bad_token_value_is_a_diagnostic():
    th, diags = apply_tokens(DEFAULT, {"min_font_size": "abc", "colors.primary": "#123456"})
    assert th.min_font_size == DEFAULT.min_font_size and th.colors["primary"] == "#123456"
    assert [d.rule for d in diags] == ["bad-token"]


def test_canonical_token_hints():
    assert canonical_token("style", "title.band") == ("title_band", "")
    assert canonical_token("style", "table.header.fill") == ("table_header_fill", "")
    assert canonical_token("style", "radius")[0] == "classes.card.radius"
    path, hint = canonical_token("style", "titel_band")
    assert path is None and "title_band" in hint
    assert canonical_token("fonts", "heding")[1].startswith("did you mean 'heading'")


def test_schema_table_lists_layout_and_render():
    paths = {p for p, _ in schema_table()}
    assert {"colors.primary", "fonts.ea", "layout.top_gap", "render.connector_width", "title_band"} <= paths
