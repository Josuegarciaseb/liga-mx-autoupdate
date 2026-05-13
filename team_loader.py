# team_loader.py
import os
from typing import List
from sportapi_adapter import list_teams, extract_team_id_and_name

LEAGUE_ID = int(os.getenv("LEAGUE_ID", "262"))
SEASON    = int(os.getenv("SEASON",    "2025"))


def get_all_team_ids() -> List[int]:
    """
    Devuelve lista de IDs de equipo únicos y ordenados para la liga/temporada.
    Delega toda la lógica de extracción a extract_team_id_and_name para
    evitar duplicar código.
    """
    teams_raw = list_teams(LEAGUE_ID, SEASON)
    ids: List[int] = []

    for entry in teams_raw or []:
        pair = extract_team_id_and_name(entry)
        if pair and pair.get("id") is not None:
            ids.append(pair["id"])
        else:
            print(f"  [warn] No se pudo extraer team_id de: {entry}")

    # Únicos, enteros válidos, ordenados
    unique_ids = sorted({
        int(i) for i in ids
        if isinstance(i, (int, str)) and str(i).isdigit()
    })

    if not unique_ids:
        print("  [error] get_all_team_ids() devolvió lista vacía.")
    else:
        print(f"  [info] {len(unique_ids)} equipos cargados: {unique_ids}")

    return unique_ids
