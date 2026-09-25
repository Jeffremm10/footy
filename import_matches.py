"""
Import match results from a CSV file.

Expected columns: date, home_team, away_team, home_score, away_score
Invalid rows raise ImportError — data-quality problems should be visible.
"""

import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


REQUIRED_COLUMNS = {"date", "home_team", "away_team", "home_score", "away_score"}

# Team name normalization: friendly names → canonical names
TEAM_ALIASES = {
    "Man Utd": "Manchester United",
    "Man City": "Manchester City",
    "Man U": "Manchester United",
    "Utd": "Manchester United",
    "City": "Manchester City",
    "Spurs": "Tottenham Hotspur",
    "Everton": "Everton",
    "Liverpool": "Liverpool",
    "Arsenal": "Arsenal",
    "Chelsea": "Chelsea",
    "Barca": "FC Barcelona",
    "Barcelona": "FC Barcelona",
    "Real": "Real Madrid",
    "Real Madrid": "Real Madrid",
    "Bayern": "FC Bayern Munich",
    "PSG": "Paris Saint-Germain",
}


@dataclass(frozen=True)
class MatchResult:
    date: date
    home_team: str
    away_team: str
    home_score: int
    away_score: int


class RowError(ValueError):
    """Raised when a CSV row fails validation."""

    def __init__(self, row_number: int, reason: str):
        self.row_number = row_number
        self.reason = reason
        super().__init__(f"Row {row_number}: {reason}")


def _parse_score(value: str, field: str, row_number: int) -> int:
    try:
        score = int(value)
    except ValueError:
        raise RowError(row_number, f"{field} must be an integer, got {value!r}")
    if score < 0:
        raise RowError(row_number, f"{field} cannot be negative, got {score}")
    return score


def _parse_date(value: str, row_number: int) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise RowError(row_number, f"date {value!r} does not match YYYY-MM-DD, DD/MM/YYYY, or DD-MM-YYYY")


def _normalize_team_name(name: str) -> str:
    """Normalize a team name using the TEAM_ALIASES mapping."""
    return TEAM_ALIASES.get(name, name)


def _parse_team(value: str, field: str, row_number: int) -> str:
    name = value.strip()
    if not name:
        raise RowError(row_number, f"{field} must not be blank")
    return _normalize_team_name(name)


def _validate_row(row: dict, row_number: int) -> MatchResult:
    missing = REQUIRED_COLUMNS - row.keys()
    if missing:
        raise RowError(row_number, f"missing columns: {sorted(missing)}")

    match_date = _parse_date(row["date"], row_number)
    home_team = _parse_team(row["home_team"], "home_team", row_number)
    away_team = _parse_team(row["away_team"], "away_team", row_number)
    home_score = _parse_score(row["home_score"].strip(), "home_score", row_number)
    away_score = _parse_score(row["away_score"].strip(), "away_score", row_number)

    if home_team == away_team:
        raise RowError(row_number, f"home_team and away_team must differ, both are {home_team!r}")

    return MatchResult(
        date=match_date,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
    )


def import_matches(path: Path) -> list[MatchResult]:
    """
    Parse *path* and return a list of MatchResult objects sorted chronologically.

    Raises RowError for the first invalid row encountered, including duplicate
    fixtures (same date, home_team, away_team).
    Raises ValueError if required columns are absent from the header.
    """
    results: list[MatchResult] = []
    seen: dict[tuple, int] = {}  # fixture key -> first row number

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        if reader.fieldnames is None:
            raise ValueError(f"{path}: file is empty")

        header = {f.strip() for f in reader.fieldnames}
        missing = REQUIRED_COLUMNS - header
        if missing:
            raise ValueError(f"{path}: header missing columns: {sorted(missing)}")

        for row_number, raw_row in enumerate(reader, start=2):
            row = {k.strip(): v for k, v in raw_row.items() if k is not None}
            match = _validate_row(row, row_number)
            key = (match.date, match.home_team, match.away_team)
            if key in seen:
                raise RowError(
                    row_number,
                    f"duplicate fixture: {match.home_team} vs {match.away_team} on {match.date} "
                    f"already seen at row {seen[key]}",
                )
            seen[key] = row_number
            results.append(match)

    results.sort(key=lambda m: m.date)
    return results


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        sys.exit("usage: python import_matches.py <file.csv>")

    path = Path(args[0])
    if not path.exists():
        sys.exit(f"error: {path} not found")

    try:
        matches = import_matches(path)
    except (ValueError, RowError) as exc:
        sys.exit(f"error: {exc}")

    print(f"Imported {len(matches)} match(es)")
    for m in matches:
        print(f"  {m.date}  {m.home_team} {m.home_score}–{m.away_score} {m.away_team}")


if __name__ == "__main__":
    main()
