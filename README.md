# Liga MX Auto-Update (SportAPI) — Córners y Tarjetas

Genera automáticamente un CSV **diario** con estadísticas por partido y equipo (córners a favor/en contra/total, amarillas y rojas), usando **SportAPI** y **GitHub Actions**.

## 🚀 Qué obtienes
- Carpeta `data/` con `partidos_YYYY-MM-DD.csv`.
- Cada fila = una vista del partido desde un **equipo** (útil para métricas "a favor").
- Campos: fixture, fecha, local/visita, goles, córners, amarillas, rojas.

## 🔑 Requisitos
- Cuenta y `API key` en tu **SportAPI**.
- Conocer los **endpoints** para:
  - listar fixtures de un equipo (`ENDPOINT_FIXTURES`),
  - estadísticas de un fixture (`ENDPOINT_FIXTURE_STATS`),
  - listar equipos (`ENDPOINT_TEAMS`) o standings (`ENDPOINT_STANDINGS`).

> Edita `config.example.env` con tu info y convierte los valores en **Secrets** del repo.

## 🧩 Estructura
```
liga-mx-autoupdate/
├─ fetch_stats.py           # Script principal (genera CSV)
├─ sportapi_adapter.py      # Adaptador para tu SportAPI
├─ team_loader.py           # Carga IDs de todos los equipos (Liga/Season)
├─ requirements.txt
├─ config.example.env
├─ data/
└─ .github/workflows/cron.yml
```

## ⚙️ Configuración (GitHub Secrets)
En tu repo → **Settings → Secrets and variables → Actions** crea:
- `SPORTAPI_BASE_URL`
- `SPORTAPI_KEY`

Opcionalmente también:
- `LEAGUE_ID` (default 262)
- `SEASON` (default 2025)
- `FROM_DATE` (default 2025-07-01)
- `TO_DATE` (default 2025-12-20)
- `AUTH_HEADER_TYPE` (default Bearer)
- `AUTH_HEADER_NAME` (default Authorization)
- `ENDPOINT_FIXTURES`, `ENDPOINT_FIXTURE_STATS`, `ENDPOINT_TEAMS`, `ENDPOINT_STANDINGS`
- `STAT_LABEL_CORNERS`, `STAT_LABEL_YELLOW`, `STAT_LABEL_RED`

## ▶️ Probar en local
1. Crea `.env` copiando de `config.example.env` y ajusta valores.
2. Instala deps: `pip install -r requirements.txt`
3. Ejecuta: `python fetch_stats.py` → revisa `data/partidos_YYYY-MM-DD.csv`

## 🕒 Automatización (GitHub Actions)
El workflow `cron.yml` corre diario a las 12:00 UTC (06:00 MX). Puedes ajustar el cron.

## 🧠 Notas
- Algunas APIs publican estadísticas unos minutos después de `FT`. El cron diario lo captura.
- Si tu API nombra distinto los campos, ajusta los **STAT_LABEL_*** en secrets o en el código del adapter.
- Para **todos los equipos** de Liga MX, `team_loader.py` obtiene IDs desde `ENDPOINT_TEAMS` o `ENDPOINT_STANDINGS`.

## 📄 Esquema de CSV
| Columna | Descripción |
|---|---|
| fixture_id | ID del partido |
| fecha | ISO datetime |
| home | Nombre equipo local |
| away | Nombre equipo visitante |
| condicion | "Local" si la fila corresponde al local, sino "Visitante" |
| goles_for / goles_against | Goles del equipo vs rival |
| corners_for / against / total | Córners |
| amarillas_for / against | Amarillas |
| rojas_for / against | Rojas |
