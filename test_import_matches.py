import io
import textwrap
from datetime import date
from pathlib import Path

import pytest

from import_matches import MatchResult, RowError, import_matches


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def csv_file(tmp_path: Path, content: str) -> Path:
    """Write *content* to a temp CSV and return its path."""
    p = tmp_path / "matches.csv"
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


VALID_CSV = """\
    date,home_team,away_team,home_score,away_score
    2024-01-15,Arsenal,Chelsea,2,1
    2024-01-22,Liverpool,Manchester City,0,0
"""


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestValidImport:
    def test_returns_correct_count(self, tmp_path):
        results = import_matches(csv_file(tmp_path, VALID_CSV))
        assert len(results) == 2

    def test_first_row_fields(self, tmp_path):
        m = import_matches(csv_file(tmp_path, VALID_CSV))[0]
        assert m == MatchResult(
            date=date(2024, 1, 15),
            home_team="Arsenal",
            away_team="Chelsea",
            home_score=2,
            away_score=1,
        )

    def test_draw_is_accepted(self, tmp_path):
        m = import_matches(csv_file(tmp_path, VALID_CSV))[1]
        assert m.home_score == 0 and m.away_score == 0

    def test_zero_zero_draw(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-03-01,Barca,Real,0,0\n"
        results = import_matches(csv_file(tmp_path, content))
        assert results[0].home_score == 0

    def test_slash_date_format(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n15/01/2024,Arsenal,Chelsea,2,1\n"
        m = import_matches(csv_file(tmp_path, content))[0]
        assert m.date == date(2024, 1, 15)

    def test_dmy_dash_date_format(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n15-01-2024,Arsenal,Chelsea,2,1\n"
        m = import_matches(csv_file(tmp_path, content))[0]
        assert m.date == date(2024, 1, 15)

    def test_whitespace_trimmed_from_team_names(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-01-01, Arsenal , Chelsea ,1,0\n"
        m = import_matches(csv_file(tmp_path, content))[0]
        assert m.home_team == "Arsenal"
        assert m.away_team == "Chelsea"

    def test_empty_file_returns_empty_list(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n"
        results = import_matches(csv_file(tmp_path, content))
        assert results == []


# ---------------------------------------------------------------------------
# Missing-header tests
# ---------------------------------------------------------------------------

class TestMissingHeader:
    def test_missing_date_column(self, tmp_path):
        content = "home_team,away_team,home_score,away_score\nArsenal,Chelsea,1,0\n"
        with pytest.raises(ValueError, match="date"):
            import_matches(csv_file(tmp_path, content))

    def test_missing_score_columns(self, tmp_path):
        content = "date,home_team,away_team\n2024-01-01,Arsenal,Chelsea\n"
        with pytest.raises(ValueError, match="home_score"):
            import_matches(csv_file(tmp_path, content))

    def test_truly_empty_file(self, tmp_path):
        p = tmp_path / "empty.csv"
        p.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            import_matches(p)


# ---------------------------------------------------------------------------
# Invalid-row tests — each should raise RowError, not silently pass
# ---------------------------------------------------------------------------

class TestInvalidRows:
    def test_non_integer_home_score(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-01-01,Arsenal,Chelsea,two,1\n"
        with pytest.raises(RowError, match="home_score"):
            import_matches(csv_file(tmp_path, content))

    def test_non_integer_away_score(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-01-01,Arsenal,Chelsea,1,?\n"
        with pytest.raises(RowError, match="away_score"):
            import_matches(csv_file(tmp_path, content))

    def test_negative_score(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-01-01,Arsenal,Chelsea,-1,0\n"
        with pytest.raises(RowError, match="negative"):
            import_matches(csv_file(tmp_path, content))

    def test_blank_home_team(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-01-01,,Chelsea,1,0\n"
        with pytest.raises(RowError, match="home_team"):
            import_matches(csv_file(tmp_path, content))

    def test_blank_away_team(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-01-01,Arsenal,,1,0\n"
        with pytest.raises(RowError, match="away_team"):
            import_matches(csv_file(tmp_path, content))

    def test_same_home_and_away_team(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n2024-01-01,Arsenal,Arsenal,1,0\n"
        with pytest.raises(RowError, match="differ"):
            import_matches(csv_file(tmp_path, content))

    def test_invalid_date_format(self, tmp_path):
        content = "date,home_team,away_team,home_score,away_score\n01-2024-15,Arsenal,Chelsea,1,0\n"
        with pytest.raises(RowError, match="date"):
            import_matches(csv_file(tmp_path, content))

    def test_row_error_includes_row_number(self, tmp_path):
        content = (
            "date,home_team,away_team,home_score,away_score\n"
            "2024-01-01,Arsenal,Chelsea,1,0\n"   # row 2 — valid
            "2024-01-02,Liverpool,City,bad,0\n"  # row 3 — invalid
        )
        with pytest.raises(RowError) as exc_info:
            import_matches(csv_file(tmp_path, content))
        assert exc_info.value.row_number == 3

    def test_first_bad_row_stops_import(self, tmp_path):
        """Import stops at the first invalid row; later rows are not processed."""
        content = (
            "date,home_team,away_team,home_score,away_score\n"
            "2024-01-01,Arsenal,Arsenal,1,0\n"   # row 2 — same team
            "2024-01-02,Liverpool,City,1,0\n"    # row 3 — valid but should not reach
        )
        with pytest.raises(RowError):
            import_matches(csv_file(tmp_path, content))


# ---------------------------------------------------------------------------
# Duplicate-fixture tests
# ---------------------------------------------------------------------------

class TestDuplicateFixtures:
    def test_duplicate_raises_row_error(self, tmp_path):
        content = (
            "date,home_team,away_team,home_score,away_score\n"
            "2024-01-01,Arsenal,Chelsea,1,0\n"   # row 2
            "2024-01-01,Arsenal,Chelsea,2,1\n"   # row 3 — duplicate fixture
        )
        with pytest.raises(RowError, match="duplicate"):
            import_matches(csv_file(tmp_path, content))

    def test_duplicate_row_error_has_correct_row_number(self, tmp_path):
        content = (
            "date,home_team,away_team,home_score,away_score\n"
            "2024-01-01,Arsenal,Chelsea,1,0\n"
            "2024-01-02,Liverpool,City,0,0\n"
            "2024-01-01,Arsenal,Chelsea,2,1\n"   # row 4 — duplicate
        )
        with pytest.raises(RowError) as exc_info:
            import_matches(csv_file(tmp_path, content))
        assert exc_info.value.row_number == 4

    def test_same_teams_different_date_is_not_duplicate(self, tmp_path):
        content = (
            "date,home_team,away_team,home_score,away_score\n"
            "2024-01-01,Arsenal,Chelsea,1,0\n"
            "2024-02-01,Arsenal,Chelsea,2,1\n"
        )
        results = import_matches(csv_file(tmp_path, content))
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Chronological ordering tests
# ---------------------------------------------------------------------------

class TestChronologicalOrder:
    def test_out_of_order_csv_sorted_on_return(self, tmp_path):
        content = (
            "date,home_team,away_team,home_score,away_score\n"
            "2024-03-01,Arsenal,Chelsea,1,0\n"
            "2024-01-15,Liverpool,City,2,2\n"
            "2024-02-10,Spurs,Everton,0,1\n"
        )
        results = import_matches(csv_file(tmp_path, content))
        dates = [m.date for m in results]
        assert dates == sorted(dates)

    def test_already_sorted_csv_stays_sorted(self, tmp_path):
        results = import_matches(csv_file(tmp_path, VALID_CSV))
        dates = [m.date for m in results]
        assert dates == sorted(dates)
