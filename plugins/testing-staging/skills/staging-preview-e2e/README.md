# staging-preview-e2e

Skill de Cursor para hacer **QA de staging/preview** sobre el PR activo: matriz de cobertura a partir del diff y el ticket, preview (reuse/redeploy), casos `.http`, fixtures descubiertos vía API, chequeos de Sentry y reporte honesto a chat/tracker.

Es **agnóstica al producto**: cada repositorio aporta sus definiciones en `e2e_tests/http/**/*.http`. Esta skill aporta el runner, el estado local, el juicio de cobertura y el reporting.

---

## Contenido del paquete

```text
staging-preview-e2e/
  README.md                 # Este documento (instalación y distribución)
  SKILL.md                  # Instrucciones del agente (obligatorio)
  scripts/                  # Runner, bootstrap, check_tools, libs
  references/               # Cobertura, HTTP, preview, config, reporting
  assets/                   # Plantillas vacías (sin secretos)
  state/                    # Estado local mutable por repo — NO distribuir poblado
    .gitignore
    .gitkeep
    {repo}/                 # p.ej. loyal-guru-api-streaming-v2/
      .env
      variables/preview.json
```

| Incluir en el paquete | Excluir siempre |
|-----------------------|-----------------|
| `SKILL.md`, `scripts/`, `references/`, `assets/`, `README.md` | `state/{repo}/.env`, `state/{repo}/variables/*.json` con datos reales |
| `state/.gitignore`, `state/.gitkeep` | Credenciales, URLs de preview personales, API keys |

---

## Requisitos del sistema

| Herramienta | Obligatoria | Notas |
|-------------|-------------|--------|
| macOS o Linux | sí | Scripts compatibles con Bash 3.2 |
| `curl` | sí | Runner HTTP |
| `python3` ≥ 3.9 | sí | Solo stdlib (sin pip packages) |
| `gh` | sí | PR, comentarios, workflow |
| Acceso GitHub al repo bajo prueba | sí | Autenticación `gh auth` |
| VPN / red al preview | si aplica | Ingress privado |
| `gcloud` | no | Resolución opcional de URL |
| Extensión IDE `anweber.vscode-httpyac` | no | Solo Send Request manual |
| httpYac CLI | **nunca** | No instalar ni exigir |

Gestor de paquetes soportado para instalar tools faltantes: `brew`, `apt-get`, `dnf`, `yum`, `pacman`, `zypper`.

Integraciones opcionales del agente (MCP / UI): Jira/tracker, Sentry (u otro error tracker del proyecto).

---

## Instalación

La skill se distribuye con el plugin **testing-staging** del marketplace Loyal Guru.

1. En Cursor, instala o actualiza el plugin **Testing Staging**.
2. Abre una sesión de agente nueva para que descubra `staging-preview-e2e`.
3. `SKILL_ROOT` es el directorio que contiene este `SKILL.md` (cache del plugin). Los scripts lo resuelven solos desde `scripts/`.
4. El estado mutable vive fuera del cache del plugin (por defecto
   `${XDG_STATE_HOME:-~/.local/state}/cursor-staging-preview-e2e/{repo}/`);
   no se pierde al actualizar el marketplace. No se commitea.

Cada persona sigue necesitando su propio `state/` local (no commitear secretos).

---

## Arranque rápido (primera vez)

```bash
# SKILL_ROOT = directorio de este SKILL.md
SKILL_ROOT="<skill-package-dir>"

# 1) Tools
"$SKILL_ROOT/scripts/check_tools.sh"
# Si faltan required tools: confirmar en TTY, o:
#   CHECK_TOOLS_INSTALL=1 "$SKILL_ROOT/scripts/check_tools.sh"

# 2) Estado local (desde el repo de la app — requiere e2e_tests/AGENTS.md)
cd /path/to/app-repo
# Si no hay AGENTS.md, copia assets/AGENTS.*.example.md → e2e_tests/AGENTS.md
"$SKILL_ROOT/scripts/bootstrap.sh"
# Completar first-run setup (un paso + verify cada vez):
#   references/first-run-setup.md

# 3) Autenticación GitHub
gh auth status

# 4) Asegurar e2e_tests/http/**/*.http (y opcionalmente e2e_tests/AGENTS.md)
```

### `state/{repo}/.env` (mínimo)

Las claves las declara **`e2e_tests/AGENTS.md`** (YAML Authentication), no la skill.
El wizard de primer uso pide cada una y verifica con `verify_state.sh` antes de seguir.

`baseUrl` / `gcp` / fixtures → `state/{repo}/variables/preview.json`.
Knobs de deploy (`SMOKE_PATH`, `PREVIEW_*`, `JIRA_*`) → skill.

Plantillas AGENTS: [`assets/AGENTS.management.example.md`](assets/AGENTS.management.example.md),
[`assets/AGENTS.streaming.example.md`](assets/AGENTS.streaming.example.md).
Detalle: [`references/first-run-setup.md`](references/first-run-setup.md).

### Varios proyectos

Cada repo usa automáticamente `state/{nombre-del-repo}/` (slug desde `git remote get-url origin`, sin owner). Override opcional:

```bash
export E2E_STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/cursor-staging-preview-e2e/mi-api"
"$SKILL_ROOT/scripts/bootstrap.sh"
```

---

## Uso con el agente Cursor

### Cuándo se activa

La description de la skill dispara el uso cuando el usuario pide, por ejemplo:

- validar un PR en preview/staging
- QA de comportamiento API cambiado en preview
- ejecutar casos `e2e_tests/http`
- revisar Sentry durante QA de preview
- reportar resultados de staging E2E

Frases útiles:

- “Ejecuta staging-preview-e2e sobre este PR”
- “Haz QA de preview del PR actual y reporta en Jira”
- “Monta la matriz de cobertura y corre los `.http` en staging”

### Flujo que debe seguir el agente

```text
Tool check → Preconditions → Scope matrix → Parallel (preview + scaffold)
  → L0 OK → Discover fixtures vía API → Run .http (happy + errores)
  → Sentry (inesperado siempre; esperado si aplica) → Report / tracker
```

Resumen de capas (detalle en [`references/qa-coverage.md`](references/qa-coverage.md)):

| Capa | Qué prueba |
|------|------------|
| L0 | Servicio vivo (`SMOKE_PATH`) |
| L1 | Contrato HTTP (happy path) |
| L2 | Persistencia legible (read-after-write) |
| L3 | Side effects no HTTP (tests del PR / OPEN) |
| L4 | Sentry inesperado + esperado controlado |
| L5 | Errores controlados + mensajes sin fugas internas |

### Resultados

| Resultado | Deploy-ready |
|-----------|--------------|
| **PASS** | Sí (si está configurado) |
| **PASS (HTTP only; open risks)** | No |
| **FAIL** | No |

Plantilla de reporte: [`references/reporting.md`](references/reporting.md).

### Precedencia por repositorio

Si el repo bajo prueba tiene `e2e_tests/AGENTS.md`, **esas reglas ganan** en conflicto con la skill (deploy, fixtures, auth, checks extra).

---

## Uso manual del runner (sin agente)

```bash
# SKILL_ROOT = directorio de este SKILL.md
SKILL_ROOT="<skill-package-dir>"
REPO_ROOT="/path/to/app-repo"

"$SKILL_ROOT/scripts/check_tools.sh"
"$SKILL_ROOT/scripts/run.sh" "$REPO_ROOT/e2e_tests/http"
# o un archivo concreto:
"$SKILL_ROOT/scripts/run.sh" "$REPO_ROOT/e2e_tests/http/orders.http"
```

Códigos de salida de `run.sh`:

| Código | Significado |
|--------|-------------|
| `0` | Casos `.http` seleccionados OK (no implica PASS limpio de QA) |
| `1` | Fallo de aserción / producto |
| `2` | `DATA_STALE` (fixtures, URL, red, smoke) |

### Sustitución de variables

El runner carga siempre `state/{repo}/variables/preview.json` (más credenciales de `.env` y defaults de la skill). No hay adaptador `preview.env`.

### Preview reuse / redeploy

```bash
python3 "$SKILL_ROOT/scripts/lib/decide_preview.py" \
  --last-commit-at '<iso8601>' \
  --deploy-at '<iso8601-or-omit>' \
  --tz "${PREVIEW_TZ:-Europe/Madrid}" \
  --shutdown-hour "${PREVIEW_SHUTDOWN_HOUR:-18}"
```

Detalle: [`references/preview-deployment.md`](references/preview-deployment.md).

---

## Qué debe tener el repositorio de aplicación

```text
app-repo/
  e2e_tests/
    http/**/*.http     # Definiciones allowlisted (L1/L2/L5)
    AGENTS.md          # Opcional; override de reglas de la skill
```

**No** añadir al repo de aplicación: runners, state, secretos, ni documentación de esta skill (salvo `AGENTS.md` / `.http`).

Gramática de casos: [`references/http-tests.md`](references/http-tests.md).

Ejemplo mínimo:

```http
### create_resource_happy
# @qa-layer L1
# @expect status 200
POST {{baseUrl}}/example/resources
{{authHeaderKey}}: {{apiKey}}
Content-Type: application/json
Accept: application/json

{
  "code": "{{resourceCode}}"
}
```

---

## Seguridad (importante para distribución)

La skill está endurecida para uso multi-equipo:

- **No** hacer `eval` de JSON de fixtures; carga por pares NUL + keys validadas.
- Sustitución `{{var}}` solo con allowlist (auth/URL + fixtures cargados).
- HTTP solo **same-origin** respecto a `baseUrl` (anti-SSRF básico).
- Logs del runner **omiten** bodies de respuesta.
- Install de tools solo con confirmación o `CHECK_TOOLS_INSTALL=1`.
- `state/` con `umask 077` / `chmod 600`; ignorado por git salvo `.gitkeep`.

Variables de entorno del checker:

| Variable | Efecto |
|----------|--------|
| `CHECK_TOOLS_INSTALL=1` | Permite install no interactivo de tools required |
| `CHECK_TOOLS_NO_INSTALL=1` | Solo verificar; no instalar |
| `E2E_STATE_DIR` | Ruta absoluta al state de un proyecto (override del auto `{repo}/`) |
| `E2E_STATE_ROOT` | Directorio padre estable de todos los `{repo}/` (default XDG state) |

**Nunca** empaquetar ni compartir `state/{repo}/.env` real entre empresas o equipos.

---

## Tests de la skill

```bash
cd "$SKILL_ROOT/scripts/lib"
python3 -m unittest discover -v
```

---

## Adaptación a otra empresa / equipo

1. Instalar la skill (opción A o B).
2. Desde el repo de la app: `bootstrap.sh` y rellenar credenciales en `state/{repo}/.env` y `baseUrl`/fixtures en `preview.json`.
3. En cada API: crear `e2e_tests/http/` con casos del contrato.
4. Opcional: `e2e_tests/AGENTS.md` con VPN, Sentry project, etc. (los knobs `PREVIEW_*` / `JIRA_*` viven en la skill).
5. Configurar MCP de tracker/Sentry en Cursor si se usan L4 y transiciones.
6. No hardcodear project IDs, hostnames ni escenarios de un solo producto dentro de `SKILL.md` (mantenerlos en `preview.json` o en el repo de la app).

---

## Referencias internas

| Documento | Contenido |
|-----------|-----------|
| [`SKILL.md`](SKILL.md) | Contrato completo del agente |
| [`references/qa-coverage.md`](references/qa-coverage.md) | Matriz L0–L5 y PASS |
| [`references/http-tests.md`](references/http-tests.md) | Gramática `.http` y runner |
| [`references/preview-deployment.md`](references/preview-deployment.md) | Reuse/redeploy y URL |
| [`references/project-config.md`](references/project-config.md) | State por repo + AGENTS.md auth |
| [`references/first-run-setup.md`](references/first-run-setup.md) | Wizard paso a paso con verify |
| [`references/infer-project-auth.md`](references/infer-project-auth.md) | Inferir auth desde el código del repo |
| [`references/auth-from-curls.md`](references/auth-from-curls.md) | Completar AGENTS.md con curls (fallback) |
| [`references/reporting.md`](references/reporting.md) | Plantilla de informe |

---

## Soporte

Para fallos de tools, preview o `DATA_STALE`, revisar en este orden:

2. `e2e_tests/AGENTS.md` + `state/{repo}/.env` (creds del YAML) + `preview.json` (`baseUrl`) y red/VPN
3. `scripts/verify_state.sh --step all`
4. Smoke L0 (auth desde AGENTS.md manifest)
5. Fixtures en `state/{repo}/variables/preview.json`
6. Same-origin: los `.http` deben usar `{{baseUrl}}/...`
