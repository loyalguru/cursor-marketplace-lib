# Preview deployment

Use after the QA scope matrix exists. Prefer values from
`state/{repo}/variables/preview.json` and skill defaults
([project-config.md](project-config.md)). Never hardcode cloud project IDs,
regions, numeric project numbers, VPN profile names, or hostname patterns —
derive them from preview URLs or the repo under test.

## Reuse vs redeploy (mandatory before `/preview`)

Do **not** blindly comment `PREVIEW_COMMENT`. Decide first:

1. Collect:
   - `last_commit_at`: committed date of the PR head SHA.
   - `deploy_at`: `createdAt` of the latest successful preview bot comment
     (body that exposes a console or `*.run.app` URL). Prefer the newest
     comment whose parsed service is usable; if several services exist for
     the same PR, prefer the one matching `gcp.service` in
     `preview.json`, else the newest whose smoke will pass.
   - `PREVIEW_TZ` (default `Europe/Madrid`) and `PREVIEW_SHUTDOWN_HOUR`
     (default `18`) from skill defaults.
2. Run:

   ```bash
   python3 "$SKILL_ROOT/scripts/lib/decide_preview.py" \
     --last-commit-at '<iso8601>' \
     --deploy-at '<iso8601-or-omit>' \
     --tz "${PREVIEW_TZ:-Europe/Madrid}" \
     --shutdown-hour "${PREVIEW_SHUTDOWN_HOUR:-18}"
   # add --force-reuse when the user confirms preview is already up
   # add --smoke-failed after a failed L0 attempt on a reuse candidate
   ```

3. Interpret `ACTION`:
   - `redeploy` → trigger below (`REASON`: `no_deploy_comment`,
     `commits_after_deploy`, `post_shutdown_required`, or `smoke_failed`).
   - `reuse` → skip trigger; resolve URL from the chosen deploy comment /
     state; smoke L0. If smoke fails, re-run with `--smoke-failed` then
     redeploy.

**Shutdown rule:** previews tear down at `PREVIEW_SHUTDOWN_HOUR` local time
in `PREVIEW_TZ`. If `now` is on or after that instant **today** and the latest
successful deploy is **before** that instant, redeploy even when the PR head
has not changed.

### Trigger (only when `ACTION=redeploy`)

1. Trigger preview using `PREVIEW_COMMENT` (or the repo’s documented command).
2. Wait for the workflow reaction / successful deploy comment or check.

## Resolve URL and smoke

1. **Discover cloud project/region/service from URLs** (do not hardcode):
   - Take the console or service URL from the deploy comment (or paste).
   - Run:

     ```bash
     python3 "$SKILL_ROOT/scripts/lib/parse_preview_url.py" '<url-or-comment-text>'
     ```

     Console URLs like
     `…/run/detail/<region>/<service>/…?project=<gcp-project-id>` yield
     `GCP_PROJECT`, `GCP_REGION`, and `GCP_SERVICE`.
   - Persist non-empty values into `state/{repo}/variables/preview.json` as
     `gcp.project` / `gcp.region` / `gcp.service` when missing or stale.
   - Fallback if the comment has no `?project=`: search the **current repo**
     CI/preview workflow for `project=` / `CLOUDSDK_CORE_PROJECT` /
     equivalent, then confirm with the user if ambiguous.
   - A `*.run.app` hostname alone exposes **project number**, not project id;
     use it for `baseUrl` / region / service, and still obtain `gcp.project`
     from the console URL or repo workflow.
2. Resolve the API base URL — **order matters** (`gcloud` must not block):
   1. HTTPS `*.run.app` URL from the comment / `parse_preview_url.py` (`URL=`).
   2. Else reuse `baseUrl` in `preview.json` when its host service matches
      `gcp.service`.
   3. Else rebuild
      `https://{service}-{projectNumber}.{region}.run.app` when service,
      project **number** (from a prior `baseUrl` or parser), and region are known
      (`parse_preview_url.build_run_app_url`).
   4. Optionally try `gcloud run services describe … --format='value(status.url)'`
      when `gcloud` auth works. On auth/refresh errors, log and continue with
      steps 1–3 — **never** treat a `gcloud` failure as “preview not deployed”.
   5. Ask the user only if still unresolved.
3. Update `baseUrl` (and discovered `gcp.*`) in
   `state/{repo}/variables/preview.json`; keep credentials in `.env` only.
4. Smoke `GET {SMOKE_PATH}` (skill default `/ping`). This is the source of truth
   that the preview is alive. An HTML provider 404 usually means network/ingress,
   not an API assertion failure — treat as smoke failure → redeploy path.
5. Deployment failure stops the workflow and success transitions on the
   tracker.

`gcloud` is **optional**. Auth/refresh failures must not block preview reuse
or URL resolution.
