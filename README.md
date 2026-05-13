# Liga MX Auto-Update — Córners y Tarjetas

Genera automáticamente un CSV **diario** con estadísticas por partido y equipo (córners a favor/en contra/total, amarillas y rojas), usando cualquier **SportAPI compatible** y **GitHub Actions**.

## Qué obtienes

- Carpeta `data/` con archivos `partidos_YYYY-MM-DD.csv` commiteados automáticamente.
- Cada fila = una vista del partido desde un **equipo** (útil para métricas "a favor/en contra").
- Campos: fixture, fecha, local/visita, goles, córners, amarillas, rojas.

## Estructura

```
liga-mx-autoupdate/
├── fetch_stats.py           # Script principal (genera CSV)
├── sportapi_adapter.py      # Adaptador genérico para tu SportAPI
├── team_loader.py           # Obtiene IDs de equipos (Liga/Season)
├── requirements.txt
├── config.example.env       # Plantilla de variables de entorno
├── data/                    # CSVs generados (commiteados por el bot)
└── .github/workflows/cron.yml
```

## Configuración

### 1. Secrets en GitHub

En tu repo → **Settings → Secrets and variables → Actions** crea los siguientes secrets:

| Secret | Obligatorio | Descripción |
|--------|-------------|-------------|
| `SPORTAPI_BASE_URL` | ✅ | URL base de tu SportAPI (ej. `https://api-football-v1.p.rapidapi.com/v3`) |
| `SPORTAPI_KEY` | ✅ | Tu API key |
| `LEAGUE_ID` | — | ID de la liga (default: `262` para Liga MX) |
| `SEASON` | — | Temporada (default: `2025`) |
| `FROM_DATE` | — | Fecha inicio rango (default: `2025-07-01`) |
| `TO_DATE` | — | Fecha fin rango (default: `2025-12-20`) |
| `AUTH_HEADER_TYPE` | — | Tipo de auth (default: `Bearer`). Usa `""` si tu API usa header plano |
| `AUTH_HEADER_NAME` | — | Nombre del header (default: `Authorization`). Ej. `x-rapidapi-key` |
| `ENDPOINT_FIXTURES` | — | Ruta de fixtures (default: `/fixtures`) |
| `ENDPOINT_FIXTURE_STATS` | — | Ruta de stats por fixture (default: `/fixtures/statistics`) |
| `ENDPOINT_TEAMS` | — | Ruta de equipos (default: `/teams`) |
| `ENDPOINT_STANDINGS` | — | Ruta de standings como alternativa (default: `/standings`) |
| `STAT_LABEL_CORNERS` | — | Etiqueta de córners en tu API (default: `Corner Kicks`) |
| `STAT_LABEL_YELLOW` | — | Etiqueta de amarillas (default: `Yellow Cards`) |
| `STAT_LABEL_RED` | — | Etiqueta de rojas (default: `Red Cards`) |

### 2. Ejemplo para API-Football (RapidAPI)

```
SPORTAPI_BASE_URL=https://api-football-v1.p.rapidapi.com/v3
SPORTAPI_KEY=<tu_rapidapi_key>
AUTH_HEADER_NAME=x-rapidapi-key
AUTH_HEADER_TYPE=           # vacío — el adapter envía solo el key sin prefijo
```

> Para RapidAPI también necesitas el header `x-rapidapi-host`. Agrégalo en `sportapi_adapter.py` dentro de `_headers()` si tu proveedor lo requiere.

## Probar en local

1. Copia el ejemplo de config y ajusta tus valores:
   ```bash
   cp config.example.env .env
   # edita .env con tu BASE_URL, KEY, etc.
   ```

2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecuta:
   ```bash
   python fetch_stats.py
   ```
   → Genera `data/partidos_YYYY-MM-DD.csv`

## Automatización (GitHub Actions)

El workflow `cron.yml` corre **diario a las 12:00 UTC** (~06:00 hora México). Puedes cambiar el horario editando la línea `cron:` en el workflow.

Al terminar, el bot commitea automáticamente los CSV nuevos al repo con el mensaje `auto-update YYYY-MM-DD`.

También puedes dispararlo manualmente desde **Actions → fetch-liga-mx → Run workflow**.

## Notas

- Algunas APIs publican las estadísticas unos minutos después del `FT`. El cron diario lo captura sin problema.
- Si tu API nombra distinto los campos de stats (ej. `"Corner Kicks"` vs `"corners"`), ajusta los secrets `STAT_LABEL_*` o modifica directamente el adapter.
- El adaptador prueba primero `ENDPOINT_TEAMS` y si no devuelve resultados usa `ENDPOINT_STANDINGS` para obtener los IDs de equipos.

## Esquema del CSV

| Columna | Descripción |
|---------|-------------|
| `fixture_id` | ID del partido en la API |
| `fecha` | ISO datetime del partido |
| `home` | Nombre del equipo local |
| `away` | Nombre del equipo visitante |
| `condicion` | `"Local"` o `"Visitante"` (perspectiva de la fila) |
| `goles_for` | Goles del equipo de la fila |
| `goles_against` | Goles del rival |
| `corners_for` | Córners del equipo de la fila |
| `corners_against` | Córners del rival |
| `corners_total` | Suma de ambos |
| `amarillas_for` | Amarillas del equipo de la fila |
| `amarillas_against` | Amarillas del rival |
| `rojas_for` | Rojas del equipo de la fila |
| `rojas_against` | Rojas del rival |
