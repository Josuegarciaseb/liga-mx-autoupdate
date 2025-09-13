import os, time, requests
from typing import Dict, Any, List, Optional

BASE_URL = os.getenv("SPORTAPI_BASE_URL", "").rstrip("/")
API_KEY  = os.getenv("SPORTAPI_KEY", "")

# Auth configurable por secretos
AUTH_HEADER_TYPE = os.getenv("AUTH_HEADER_TYPE", "Bearer")
AUTH_HEADER_NAME = os.getenv("AUTH_HEADER_NAME", "Authorization")

# Endpoints configurables
EP_FIXTURES      = os.getenv("ENDPOINT_FIXTURES", "/fixtures")
EP_FIXTURE_STATS = os.getenv("ENDPOINT_FIXTURE_STATS", "/fixtures/statistics")
EP_TEAMS         = os.getenv("ENDPOINT_TEAMS", "/teams")
EP_STANDINGS     = os.getenv("ENDPOINT_STANDINGS", "/standings")

# Etiquetas de estadísticas (ajusta a tu SportAPI, puedes sobreescribir por secretos)
STAT_LABELS = {
    "corners": os.getenv("STAT_LABEL_CORNERS", "Corner Kicks"),
    "yellow":  os.getenv("STAT_LABEL_YELLOW",  "Yellow Cards"),
    "red":     os.getenv("STAT_LABEL_RED",     "Red Cards"),
}

# Mapeos de campos habituales; ajusta si tu SportAPI usa otras rutas
FIELD_MAP = {
    "status_short_path": ["fixture", "status", "short"],  # p.ej. "FT"
    "fixture_id_path":   ["fixture", "id"],
    "fixture_date_path": ["fixture", "date"],
    "home_team_id_path": ["teams", "home", "id"],
    "home_team_name_path": ["teams", "home", "name"],
    "away_team_id_path": ["teams", "away", "id"],
    "away_team_name_path": ["teams", "away", "name"],
    "goals_home_path": ["goals", "home"],
    "goals_away_path": ["goals", "away"],
}

def _headers():
    assert API_KEY, "Falta SPORTAPI_KEY"
    if AUTH_HEADER_NAME.lower() == "authorization":
        return {AUTH_HEADER_NAME: f"{AUTH_HEADER_TYPE} {API_KEY}"}
    return {AUTH_HEADER_NAME: API_KEY}

def api_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    assert BASE_URL, "Falta SPORTAPI_BASE_URL"
    url = f"{BASE_URL}/{path.lstrip('/')}"
    for attempt in range(3):
        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                raise RuntimeError(f"Respuesta no JSON en {url}")
        time.sleep(2 * (attempt + 1))
    r.raise_for_status()

def _dig(obj: Dict[str, Any], path: List[str]) -> Any:
    cur = obj
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

def extract_basic_fields(fixture: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status_short": _dig(fixture, FIELD_MAP["status_short_path"]),
        "fixture_id":   _dig(fixture, FIELD_MAP["fixture_id_path"]),
        "fixture_date": _dig(fixture, FIELD_MAP["fixture_date_path"]),
        "home_id":      _dig(fixture, FIELD_MAP["home_team_id_path"]),
        "home_name":    _dig(fixture, FIELD_MAP["home_team_name_path"]),
        "away_id":      _dig(fixture, FIELD_MAP["away_team_id_path"]),
        "away_name":    _dig(fixture, FIELD_MAP["away_team_name_path"]),
        "goals_home":   _dig(fixture, FIELD_MAP["goals_home_path"]),
        "goals_away":   _dig(fixture, FIELD_MAP["goals_away_path"]),
    }

def list_fixtures_by_team(league_id: int, season: int, team_id: int, date_from: str=None, date_to: str=None):
    params = {"league": league_id, "season": season, "team": team_id}
    if date_from: params["from"] = date_from
    if date_to:   params["to"]   = date_to
    js = api_get(EP_FIXTURES, params)
    # La mayoría de APIs retornan bajo 'response' o 'data':
    return js.get("response", js.get("data", js.get("fixtures", [])))

def fixture_statistics(fixture_id: int):
    js = api_get(EP_FIXTURE_STATS, {"fixture": fixture_id})
    # La mayoría de APIs retornan una lista de entradas (home/away)
    return js.get("response", js.get("data", js.get("statistics", [])))

def list_teams(league_id: int, season: int) -> List[Dict[str, Any]]:
    # Intento 1: endpoint TEAMS
    js = api_get(EP_TEAMS, {"league": league_id, "season": season})
    teams = js.get("response", js.get("data"))
    if isinstance(teams, list) and teams:
        return teams

    # Intento 2: endpoint STANDINGS (transformar a lista de equipos)
    js2 = api_get(EP_STANDINGS, {"league": league_id, "season": season})
    data = js2.get("response", js2.get("data"))
    out = []
    if isinstance(data, list):
        # Muchos standings retornan una lista con 'league'->'standings'->[ [ {team:{id,name},...}, ... ] ]
        for blk in data:
            league = blk.get("league") if isinstance(blk, dict) else None
            groups = None
            if league and isinstance(league, dict):
                groups = league.get("standings")
            else:
                groups = blk.get("standings") if isinstance(blk, dict) else None
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, list):
                        for row in group:
                            team = (row or {}).get("team", {})
                            if team:
                                out.append({"team": team})
    return out

def extract_team_id_and_name(team_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Caso 1: /teams devuelve algo como {"team": {"id": 123, "name": "Cruz Azul"}, ...}
    if "team" in team_entry and isinstance(team_entry["team"], dict):
        t = team_entry["team"]
        return {"id": t.get("id"), "name": t.get("name")}
    # Caso 2: /teams devuelve {"id": 123, "name": "Cruz Azul"} plano
    if "id" in team_entry and "name" in team_entry:
        return {"id": team_entry.get("id"), "name": team_entry.get("name")}
    return None

def get_stat(stats_list: List[Dict[str, Any]], label: str) -> Optional[int]:
    # Muchas APIs usan [{"type":"Corner Kicks","value":10}, ...] o {"name":"corners","value":10}
    for it in stats_list or []:
        cand = (it.get("type") or it.get("name") or it.get("code") or "").strip().lower()
        if cand == label.strip().lower():
            v = it.get("value")
            if isinstance(v, int): return v
            try: return int(v)
            except Exception: return None
    # fallback: algunas APIs usan claves directas {"corners": 10, "yellowcards": 2, ...}
    if isinstance(stats_list, dict):  # en caso de que traiga un dict en vez de lista
        v = stats_list.get(label)
        if isinstance(v, int): return v
        try: return int(v)
        except Exception: return None
    return None
