# fetch_stats.py
import os, csv, datetime, time, glob
from dotenv import load_dotenv
load_dotenv()
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

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_seen_fixture_ids():
    """
    Lee todos los CSV existentes en data/ y devuelve el conjunto de
    fixture_ids ya procesados. Permite fetch incremental: no se vuelven
    a descargar partidos que ya están guardados.
    """
    seen = set()
    for path in glob.glob(f"{OUT_DIR}/partidos_*.csv"):
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fid = row.get("fixture_id")
                    if fid:
                        seen.add(int(fid))
        except Exception as e:
            print(f"  [warn] No se pudo leer {path}: {e}")
    return seen


def to_rows(fix, stats_response, home_id, away_id):
    """
    Genera DOS filas por partido (perspectiva local + visitante).
    Retorna lista vacía si el partido no está terminado.
    """
    b = extract_basic_fields(fix)
    if b["status_short"] not in ("FT", "AET", "PEN"):
        return []

    # Separar stats por equipo
    home_stats, away_stats = [], []
    for entry in stats_response or []:
        tid = (entry.get("team") or {}).get("id") or entry.get("team_id")
        st  = entry.get("statistics", entry.get("stats", []))
        if tid == home_id:
            home_stats = st
        if tid == away_id:
            away_stats = st

    # Avisar si no hay stats (partido reciente sin datos aún)
    if not home_stats and not away_stats:
        print(f"  [warn] fixture {b['fixture_id']} sin estadísticas todavía.")

    def build_row(is_home):
        my_stats  = home_stats if is_home else away_stats
        opp_stats = away_stats if is_home else home_stats
        gf = b["goals_home"] if is_home else b["goals_away"]
        ga = b["goals_away"] if is_home else b["goals_home"]
        c_for  = get_stat(my_stats,  STAT_LABELS["corners"])
        c_agn  = get_stat(opp_stats, STAT_LABELS["corners"])
        c_tot  = (c_for or 0) + (c_agn or 0) if (c_for is not None and c_agn is not None) else None
        y_for  = get_stat(my_stats,  STAT_LABELS["yellow"])
        y_agn  = get_stat(opp_stats, STAT_LABELS["yellow"])
        r_for  = get_stat(my_stats,  STAT_LABELS["red"])
        r_agn  = get_stat(opp_stats, STAT_LABELS["red"])
        return [
            b["fixture_id"], b["fixture_date"],
            b["home_name"], b["away_name"],
            "Local" if is_home else "Visitante",
            gf, ga,
            c_for, c_agn, c_tot,
            y_for, y_agn, r_for, r_agn,
        ]

    return [build_row(True), build_row(False)]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = f"{OUT_DIR}/partidos_{datetime.date.today().isoformat()}.csv"

    # IDs de equipos en la liga
    team_ids = get_all_team_ids()
    if not team_ids:
        raise SystemExit(
            "No se encontraron team_ids. "
            "Revisa ENDPOINT_TEAMS/ENDPOINT_STANDINGS y tus credenciales."
        )
    print(f"Equipos encontrados: {len(team_ids)}")

    # Fixtures ya guardados en CSVs anteriores → no se vuelven a llamar
    seen_fixture_ids = load_seen_fixture_ids()
    print(f"Fixtures ya en disco (skip): {len(seen_fixture_ids)}")

    # Recolectar todos los fixture_ids únicos primero (evita duplicados
    # por iterar todos los equipos del mismo partido)
    fixture_map = {}   # fixture_id -> fixture object
    for team in team_ids:
        fixtures = list_fixtures_by_team(LEAGUE_ID, SEASON, team, FROM_DATE, TO_DATE)
        for fix in fixtures:
            fid = (fix.get("fixture", {}) or {}).get("id") or fix.get("id")
            if fid and fid not in fixture_map:
                fixture_map[fid] = fix
        time.sleep(0.4)   # respetar rate limit entre llamadas de fixtures

    new_fixtures = {
        fid: fix for fid, fix in fixture_map.items()
        if fid not in seen_fixture_ids
    }
    print(f"Fixtures totales en rango: {len(fixture_map)} | Nuevos a procesar: {len(new_fixtures)}")

    if not new_fixtures:
        print("Nada nuevo. Sin cambios.")
        return

    rows_written = 0
    # Abrir en modo append si el archivo ya existe (reintentos del día)
    file_mode = "a" if os.path.exists(out_path) else "w"
    with open(out_path, file_mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if file_mode == "w":
            w.writerow([
                "fixture_id", "fecha", "home", "away", "condicion",
                "goles_for", "goles_against",
                "corners_for", "corners_against", "corners_total",
                "amarillas_for", "amarillas_against", "rojas_for", "rojas_against",
            ])

        for fid, fix in new_fixtures.items():
            b = extract_basic_fields(fix)
            if b["status_short"] not in ("FT", "AET", "PEN"):
                continue   # partido no terminado, se capturará mañana

            stats = fixture_statistics(fid)
            rows = to_rows(fix, stats, b["home_id"], b["away_id"])
            for row in rows:
                w.writerow(row)
                rows_written += 1
            time.sleep(0.4)

    print(f"OK: {out_path} — {rows_written} filas escritas ({rows_written // 2} partidos)")


if __name__ == "__main__":
    main()
