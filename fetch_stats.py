# fetch_stats.py — versión forzada sin type hints problemáticos
import os, csv, datetime, time
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

def to_row_v2(fix, stats_response, team_id):
    b = extract_basic_fields(fix)
    if b["status_short"] not in ("FT", "AET", "PEN"):
        return None

    is_home = (b["home_id"] == team_id)
    gf = b["goals_home"] if is_home else b["goals_away"]
    ga = b["goals_away"] if is_home else b["goals_home"]

    home_stats, away_stats = [], []
    home_id, away_id = b["home_id"], b["away_id"]
    for entry in stats_response or []:
        tid = (entry.get("team") or {}).get("id") or entry.get("team_id")
        st  = entry.get("statistics", entry.get("stats", []))
        if tid == home_id: home_stats = st
        if tid == away_id: away_stats = st

    c_for  = get_stat(home_stats if is_home else away_stats, STAT_LABELS["corners"])
    c_agn  = get_stat(away_stats if is_home else home_stats,   STAT_LABELS["corners"])
    c_tot  = (c_for or 0) + (c_agn or 0) if (c_for is not None and c_agn is not None) else None
    y_for  = get_stat(home_stats if is_home else away_stats, STAT_LABELS["yellow"])
    y_agn  = get_stat(away_stats if is_home else home_stats,   STAT_LABELS["yellow"])
    r_for  = get_stat(home_stats if is_home else away_stats, STAT_LABELS["red"])
    r_agn  = get_stat(away_stats if is_home else home_stats,   STAT_LABELS["red"])

    return [
        b["fixture_id"], b["fixture_date"],
        b["home_name"], b["away_name"],
        "Local" if is_home else "Visitante",
        gf, ga,
        c_for, c_agn, c_tot,
        y_for, y_agn, r_for, r_agn
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
                row = to_row_v2(fix, stats, team)  # <- usamos la nueva función
                if row:
                    w.writerow(row)
                time.sleep(0.4)

    print("OK:", out_path)

if __name__ == "__main__":
    main()
