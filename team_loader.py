import os
from typing import List
from sportapi_adapter import list_teams, extract_team_id_and_name

LEAGUE_ID = int(os.getenv("LEAGUE_ID", "262"))
SEASON    = int(os.getenv("SEASON", "2025"))

def get_all_team_ids() -> List[int]:
    teams_raw = list_teams(LEAGUE_ID, SEASON)
    ids = []
    for entry in teams_raw or []:
        pair = extract_team_id_and_name(entry)
        if not pair: 
            # intenta otras formas comunes
            t = entry.get("team") if isinstance(entry, dict) else None
            if isinstance(t, dict) and "id" in t:
                ids.append(t["id"]); 
                continue
        else:
            if pair.get("id") is not None:
                ids.append(pair["id"])
    # Unicos y ordenados
    ids = sorted(list({int(i) for i in ids if isinstance(i, (int, str)) and str(i).isdigit()}))
    return ids
