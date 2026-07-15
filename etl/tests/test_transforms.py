"""Unit tests for the pure ETL transforms (no DB needed).

Run from repo root:  python -m pytest etl/tests
"""

import pandas as pd

from etl.ingest.fbref_kaggle import CANON, _normalize
from etl.load.normalize import normalize_name


class TestNormalizeName:
    def test_strips_accents(self):
        assert normalize_name("Højbjerg") == "hojbjerg"
        assert normalize_name("Öztunali") == "oztunali"
        assert normalize_name("Sørensen") == "sorensen"

    def test_lowercase_and_punctuation(self):
        assert normalize_name("O'Brien") == "o brien"
        assert normalize_name("Nicolás Otamendi") == "nicolas otamendi"

    def test_collapses_whitespace(self):
        assert normalize_name("  Kevin   De  Bruyne ") == "kevin de bruyne"

    def test_empty_and_none(self):
        assert normalize_name(None) == ""
        assert normalize_name("") == ""

    def test_stable_for_matching(self):
        # same person, different source spellings -> same key
        assert normalize_name("Rúben Dias") == normalize_name("Ruben Dias")


class TestFbrefKaggleNormalize:
    def _row(self, **kw):
        base = {"player": "X", "born": 1996, "Tackles attempted": 3.0,
                "Shot creating actions p 90": 2.0, "Avg Mins per Match": 900,
                "Pass completion %": 80.0}
        base.update(kw)
        return pd.DataFrame([base])

    def test_output_has_canonical_columns(self):
        mapping = {"player": "player", "born": "born", "Tackles attempted": "tackles"}
        out = _normalize(self._row(), mapping, "2223", set())
        assert list(out.columns) == CANON
        assert out.iloc[0]["tackles"] == 3.0

    def test_per90_converted_to_total(self):
        # 2.0 SCA/90 over 10 nineties (900 min) -> 20 total
        mapping = {"player": "player", "born": "born",
                   "Shot creating actions p 90": "sca", "Avg Mins per Match": "minutes"}
        out = _normalize(self._row(), mapping, "2223", {"sca"})
        assert out.iloc[0]["sca"] == 20.0  # 2.0 * (900/90)

    def test_nineties_derived_from_minutes(self):
        mapping = {"player": "player", "born": "born", "Avg Mins per Match": "minutes"}
        out = _normalize(self._row(), mapping, "2223", set())
        assert out.iloc[0]["nineties"] == 10.0

    def test_rate_column_not_scaled(self):
        mapping = {"player": "player", "born": "born",
                   "Pass completion %": "pass_cmp_pct", "Avg Mins per Match": "minutes"}
        out = _normalize(self._row(), mapping, "2223", set())
        assert out.iloc[0]["pass_cmp_pct"] == 80.0
