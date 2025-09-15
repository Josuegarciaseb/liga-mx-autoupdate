import os, csv, datetime, time
from typing import List, Dict, Any, Optional
from sportapi_adapter import (
    list_fixtures_by_team, fixture_statistics, extract_basic_fields,
    STAT_LABELS, get_stat
)
from team_loader import get_all_team_ids

LEAGUE_ID = int(os.getenv("LEAGUE_ID", "262"))
SEASON    = int(os.getenv("SEASON", "2025"))
FROM_DATE = os.getenv("FROM_DATE", "2025-07-01")
TO_DATE   = os.getenv("TO_DATE",   "2025-12-20")

OUT_DIR = "data"

def to_row(
    fix: Dict[str, Any],
    stats_response: List[Dict[str, Any]],
    team_id: int
) -> Optional[List[Any]]:
    """
    Convierte un fixture + estadísticas en una fila lista para guardar en CSV.

    fix: diccionario con datos básicos del fixture
    stats_response: lista de diccionarios con estadísticas
    team_id: id del equipo (local o visitante)
    """
    if not fix or not stats_response:
        return None

    fixture_id = fix.get("fixture_id")
    date = fix.get("fixture_date")
    home_team = fix.get("home_name")
    away_team = fix.get("away_name")
    goals_home = fix.get("goals_home")
    goals_away = fix.get("goals_away")

    # Buscar estadísticas específicas
    corners = None
    yellows = None
    reds = None
    for s in stats_response:
        stype = (s.get("type") or s.get("name") or "").lower()
        if "corner" in stype:
            corners = s.get("value")
        elif "yellow" in stype:
            yellows = s.get("value")
        elif "red" in stype:
            reds = s.get("value")

    return [
        fixture_id,
        date,
        home_team,
        away_team,
        goals_home,
        goals_away,
        team_id,
        corners,
        yellows,
        reds,
    ]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = f"{OUT_DIR}/partidos_{datetime.date.today().isoformat()}.csv"

    team_ids = get_all_team_ids()
    if not team_ids:
        raise SystemExit("No se encontraron team_ids. Revisa ENDPOINT_TEAMS/ENDPOINT_STANDINGS y tus credenciales.")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "fixture_id","fecha","home","away","condicion",
            "goles_for","goles_against",
            "corners_for","corners_against","corners_total",
            "amarillas_for","amarillas_against","rojas_for","rojas_against"
        ])

        for team in team_ids:
            fixtures = list_fixtures_by_team(LEAGUE_ID, SEASON, team, FROM_DATE, TO_DATE)
            for fix in fixtures:
                fixture_id = (fix.get("fixture", {}) or {}).get("id") or fix.get("id")
                if not fixture_id:
                    continue
                stats = fixture_statistics(fixture_id)
                row = to_row(fix, stats, team)
                if row:
                    w.writerow(row)
                time.sleep(0.4)  # cuida el rate limit si cargas muchos equipos

    print("OK:", out_path)

if __name__ == "__main__":
    main()
