# sportapi_adapter.py
import os, time, requests
from typing import Dict, Any, List, Optional

BASE_URL = os.getenv("SPORTAPI_BASE_URL", "").rstrip("/")
API_KEY  = os.getenv("SPORTAPI_KEY", "")

# Auth configurable por secretos
AUTH_HEADER_TYPE = os.getenv("AUTH_HEADER_TYPE", "Bearer")
AUTH_HEADER_NAME = os.getenv("AUTH_HEADER_NAME", "Authorization")

# Header extra opcional (ej. x-rapidapi-host para RapidAPI)
EXTRA_HEADER_NAME  = os.getenv("EXTRA_HEADER_NAME", "")
EXTRA_HEADER_VALUE = os.getenv("EXTRA_HEADER_VALUE", "")

# Endpoints configurables
EP_FIXTURES      = os.getenv("ENDPOINT_FIXTURES",       "/fixtures")
EP_FIXTURE_STATS = os.getenv("ENDPOINT_FIXTURE_STATS",  "/fixtures/statistics")
EP_TEAMS         = os.getenv("ENDPOINT_TEAMS",          "/teams")
EP_STANDINGS     = os.getenv("ENDPOINT_STANDINGS",      "/standings")

# Etiquetas de estadísticas (ajustables por secretos)
STAT_LABELS = {
    "corners": os.getenv("STAT_LABEL_CORNERS", "Corner Kicks"),
    "yellow":  os.getenv("STAT_LABEL_YELLOW",  "Yellow Cards"),
    "red":     os.getenv("STAT_LABEL_RED",     "Red Cards"),
}

# Rutas de campos dentro de la respuesta de fixtures
FIELD_MAP = {
    "status_short_path":   ["fixture", "status", "short"],
    "fixture_id_path":     ["fixture", "id"],
    "fixture_date_path":   ["fixture", "date"],
    "home_team_id_path":   ["teams", "home", "id"],
    "home_team_name_path": ["teams", "home", "name"],
    "away_team_id_path":   ["teams", "away", "id"],
    "away_team_name_path": ["teams", "away", "name"],
    "goals_home_path":     ["goals", "home"],
    "goals_away_path":     ["goals", "away"],
}


# ── Internos ─────────────────────────────────────────────────────────────────

def _headers() -> Dict[str, str]:
    assert API_KEY, "Falta SPORTAPI_KEY"
    h = {
        AUTH_HEADER_NAME: f"{AUTH_HEADER_TYPE} {API_KEY}".strip()
        if AUTH_HEADER_TYPE
        else API_KEY
    }
    if EXTRA_HEADER_NAME and EXTRA_HEADER_VALUE:
        h[EXTRA_HEADER_NAME] = EXTRA_HEADER_VALUE
    return h


def api_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    assert BASE_URL, "Falta SPORTAPI_BASE_URL"
    url = f"{BASE_URL}/{path.lstrip('/')}"
    last_status = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=_headers(), params=params, timeout=30)
            last_status = r.status_code
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    raise RuntimeError(f"Respuesta no JSON en {url}")
            # 429 = rate limit → espera más antes de reintentar
            wait = 10 if r.status_code == 429 else 2 * (attempt + 1)
            print(f"  [warn] HTTP {r.status_code} en {url} params={params} "
                  f"(intento {attempt+1}/3, esperando {wait}s)")
            time.sleep(wait)
        except requests.exceptions.RequestException as e:
            print(f"  [error] Conexión fallida en {url}: {e} (intento {attempt+1}/3)")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(
        f"Falló después de 3 intentos: {url} | último status={last_status} | params={params}"
    )


def _dig(obj: Any, path: List[str]) -> Any:
    cur = obj
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


# ── Públicas ─────────────────────────────────────────────────────────────────

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


def list_fixtures_by_team(
    league_id: int,
    season: int,
    team_id: int,
    date_from: str = None,
    date_to: str = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"league": league_id, "season": season, "team": team_id}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    js = api_get(EP_FIXTURES, params)
    return js.get("response", js.get("data", js.get("fixtures", [])))


def fixture_statistics(fixture_id: int) -> List[Dict[str, Any]]:
    js = api_get(EP_FIXTURE_STATS, {"fixture": fixture_id})
    return js.get("response", js.get("data", js.get("statistics", [])))


def list_teams(league_id: int, season: int) -> List[Dict[str, Any]]:
    # Intento 1: endpoint /teams
    js = api_get(EP_TEAMS, {"league": league_id, "season": season})
    teams = js.get("response", js.get("data"))
    if isinstance(teams, list) and teams:
        return teams

    # Intento 2: endpoint /standings como fallback
    print("  [info] /teams sin resultados, intentando /standings…")
    js2 = api_get(EP_STANDINGS, {"league": league_id, "season": season})
    data = js2.get("response", js2.get("data"))
    out = []
    if isinstance(data, list):
        for blk in data:
            league_blk = blk.get("league") if isinstance(blk, dict) else None
            groups = (
                league_blk.get("standings")
                if isinstance(league_blk, dict)
                else blk.get("standings") if isinstance(blk, dict) else None
            )
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, list):
                        for row in group:
                            team = (row or {}).get("team", {})
                            if team:
                                out.append({"team": team})
    return out


def extract_team_id_and_name(team_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Formato {"team": {"id": 123, "name": "Cruz Azul"}, ...}
    if "team" in team_entry and isinstance(team_entry["team"], dict):
        t = team_entry["team"]
        return {"id": t.get("id"), "name": t.get("name")}
    # Formato plano {"id": 123, "name": "Cruz Azul"}
    if "id" in team_entry and "name" in team_entry:
        return {"id": team_entry.get("id"), "name": team_entry.get("name")}
    return None


def get_stat(stats_list: Any, label: str) -> Optional[int]:
    """
    Busca una estadística por etiqueta en la lista devuelta por la API.
    Soporta listas tipo [{"type": "Corner Kicks", "value": 10}, ...]
    y también dicts planos {"corners": 10}.
    """
    if isinstance(stats_list, dict):
        # Fallback: algunas APIs retornan un dict en lugar de lista
        v = stats_list.get(label)
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    for it in stats_list or []:
        cand = (
            it.get("type") or it.get("name") or it.get("code") or ""
        ).strip().lower()
        if cand == label.strip().lower():
            v = it.get("value")
            if isinstance(v, int):
                return v
            try:
                return int(v)
            except (TypeError, ValueError):
                return None
    return None
