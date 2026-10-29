# Premium hosting release checklist

This is a coordinated website, ranked-bot, and orchestrator release. Nothing in this preparation authorizes merging or deployment. Keep the premium navbar link hidden for the initial beta.

## Prepared in code

- Recovered the bot migration without dropping the original stash; retained Override/BioBuzz and searchable game selection.
- Aligned actual casual launch/stop contracts. Added a local HTTP integration test with real Django and Fastify routes, both launch origins, callbacks, and the two newer games.
- Protected terminal states and launch/stop response races, made failed Polar webhooks replayable, and rejected stale entitlement updates.
- Recorded billing periods on reservations, serialized reservation decisions per user (including SQLite), and kept uncertain launch outcomes reserved until reconciliation.
- Moved Polar ingestion to the scheduled worker. A durable local hold protects credits during ingestion failures and meter aggregation delay. Portal credit grants still affect available balance.
- Added conservative reconciliation for every open session state. Network failure does not prove a process stopped. A reachable orchestrator with a missing session finalizes only last-confirmed runtime.
- Added a file-backed callback outbox that survives restart, process-exit verification/escalation, failed-start cleanup, and bot cleanup of lost ranked sessions.
- Preserved previous score files in archives before port reuse. Scoped event/IP and raw-log reads. Removed the unimplemented saved-presets promise from default Host copy.

## Actions needed from Nick, in order

### 1. Finish the existing Polar sandbox configuration

Local configuration already specifies `POLAR_SERVER=sandbox`, an access token, and a meter ID. Do not paste secrets into chat. Add missing values to the appropriate local/private configuration or secret store:

1. Configure the sandbox webhook endpoint `/subscriptions/polar/webhook/` on a reachable **test** website URL and save its signing secret as `POLAR_WEBHOOK_SECRET`. A local test receiver needs a tunnel or test host; do not point sandbox events at the live production database.
2. Ensure the token can create checkouts, read customer meters, and ingest usage events. Keep all products, meter IDs, and credentials in the same sandbox organization.
3. Map each active Django `SubscriptionPlan.polar_product_id` to its sandbox product in Django admin. Configure recurring credits to match the advertised plan: Supporter 360 and Host 1,500; one credit is one runtime minute. Configure billing-cycle expiry/no rollover and no paid overage. Verify these behaviors in sandbox rather than assuming defaults.
4. Use a **dedicated meter** for this application's `casual_server_credits` events with a sum of `metadata.credits`. Do not publish unrelated usage to it or manually inject consumption into it. The reconciliation hold uses this dedicated meter's `consumed_units`; it allows credit grants in the portal and does not release holds merely because ingestion was accepted. [Polar customer meter fields](https://polar.sh/docs/api-reference/customer-meters/get).
5. Configure and test Polar's Discord role benefit for each product, or remove the corresponding role promise from the editable plan copy. The website's role ID field does not itself grant Discord roles. Saved presets are deferred and no longer advertised by the default Host plan.
6. Configure `POLAR_CUSTOMER_PORTAL_URL` and test the manage-billing flow.

### 2. Provide an isolated Linux/Discord acceptance environment

Use a disposable Linux machine or a test host, a current xRC Linux binary supporting Override/BioBuzz, and a test Discord guild/bot identity. Do not start this orchestrator alongside live unmanaged xRC servers: the intended startup policy terminates existing xRC processes visible to its account. Isolation by host or OS account is necessary for a safe test.

Set up private configuration, without committing secrets:

| Direction | Configuration |
| --- | --- |
| Bot + orchestrator → website | Matching strong `API_KEY`; header `X-API-KEY` |
| Website → orchestrator | `ORCHESTRATOR_API_BASE_URL`, `ORCHESTRATOR_API_TOKEN`; token scopes `servers:casual:create,servers:read,servers:stop` |
| Bot → orchestrator | `ORCHESTRATOR_BASE_URL`, `ORCHESTRATOR_TOKEN`; scopes `servers:ranked:create,servers:read,servers:stop` |
| Bot privileged operations | Separate moderation/admin tokens; raw logs require `logs:read` and `moderation:read`; admin operations need their corresponding admin/create/stop/restart scopes |
| Orchestrator → website | `SECONDWEBSITE_BASE_URL` pointing at the same test website/database |
| Client connections | `SERVICE_PUBLIC_HOST`, reachable server port pool and required game traffic allowed by the test host firewall |

The local website is currently missing its orchestrator URL/token. Production mode also requires explicit non-development service tokens, a non-placeholder shared key, real process mode, and stop-on-restart reconciliation.

Choose one chat-relay owner: orchestrator webhook **or** bot event relay. Preserve runtime log/score directories and `EVENT_LOG_DIR/website-callbacks` across service restarts. Pending callbacks include connection passwords: protect the directory and its backups. No database for live orchestrator state is needed. Periodically review archived score directories and retain/remove them according to your chosen retention policy.

### 3. Run the sandbox acceptance gate before approving merges

Once the environment is ready, the candidates must demonstrate:

1. Sandbox checkout activates the correct entitlement/credits. Role benefit works and manage billing opens. Test downgrade, cancellation through period end, renewal/reset, and past-due/revoked access.
2. Website launch and Discord `/casual_start` both produce a ready real server. Join from a game client. Confirm connection/password, players, chat, and scores. Include Override and BioBuzz.
3. Stop from both entry points. Verify exactly one usage record and one Polar event per session, five-minute rounding, and eventual matching meter debit. Test max duration, exhausted balance, and concurrent launch rejection.
4. Make Polar temporarily unavailable while stopping. Confirm local finalization succeeds, credits remain held, and `sync_polar_usage` later recovers without reusing or charging the same credits twice.
5. Stop the test website long enough to exhaust immediate callback retries, restore it, and confirm the outbox replays. Restart the orchestrator with one ranked and one casual session: old processes must exit, casual usage finalizes once, Discord match resources clear, and fresh launches succeed. A mere network outage must not clear a live ranked match.
6. Complete a real ranked match: queue, roles/channels, free server launch, score/OPR display, ELO submission, inactivity behavior, and cleanup. Verify IPs are absent from ordinary event/player reads and available only to authorized moderation callers.

The automated checks cover the service contracts and mocked failure cases. They cannot prove Discord registration, a real game-client join, or live Polar benefit/meter configuration.

### 4. Rehearse against a fresh production database backup

The old local SQLite copy migrated successfully with all modeled columns and no foreign-key violations. It already contained subscriptions migrations through `0003`, so this does **not** replace testing a current backup from the actual production host.

Run against a downloaded backup, using a dependency-equipped Python 3.12 environment:

```sh
python tools/rehearse_premium_migrations.py --source /absolute/path/to/production-backup.sqlite3
```

The utility opens the source read-only, makes a disposable backup, runs `migrate --fake-initial` on the copy, and checks model columns/foreign keys. If it fails, stop and resolve the actual schema/history mismatch before approving deployment. Never delete migration records or fake missing schema changes blindly. After the baseline transition, use committed migrations normally. Back up production again immediately before any eventual migration.

### 5. Approve the reviewed release and a later coordinated cutover

After green CI, sandbox/real-game acceptance, and the current-backup rehearsal, review the three PRs together. Explicit approval to merge/deploy remains a separate step. At cutover: pause new launches, drain legacy servers, back up/migrate the website, start the orchestrator, then switch the bot to the matching release. Keep public discovery disabled during the initial beta. Record all deployed SHAs.

**The existing website workflow deploys automatically after a push to `main`. Merging its PR is therefore a deployment trigger. Keep it unmerged until the coordinated cutover is authorized, or explicitly pause that workflow first.**

Install and verify these recurring tasks on the actual host at cutover, using its Python environment and environment variables:

```cron
*/1 * * * * cd /absolute/path/to/website && /absolute/path/to/python manage.py sync_polar_usage
*/2 * * * * cd /absolute/path/to/website && /absolute/path/to/python manage.py expire_premium_sessions
```

Avoid overlapping scheduler runs; capture output and alert on failed usage/webhooks, an accumulating callback outbox, and stale open sessions. Retry corrected failed entitlement events with `python manage.py replay_subscription_webhooks`. Run `python manage.py check_premium_launch` for secret-safe local prerequisite checks; it does not contact external services or replace acceptance testing.

Switching from sandbox to production requires production product/meter/benefit IDs and keys, verification of a controlled paid lifecycle, and a separate enablement decision. Do not reuse sandbox IDs. Remove the navbar hiding only after the beta succeeds.

## Developer verification

```sh
# Website: Python 3.12 with requirements.txt installed
python manage.py makemigrations --check --dry-run
python manage.py check
python -m pytest

# Bot: Python 3.10 with requirements.txt installed
python -m unittest discover -s tests -v
python -m unittest test_regex_log -v

# Orchestrator: Node 22
npm ci
npm run check

# Local cross-service acceptance (orchestrator must already be built)
ORCHESTRATOR_REPO=/absolute/path/to/xRCServerOrchestrator python -m pytest subscriptions/test_orchestrator_integration.py -o addopts=''
```

Use dummy settings-import secrets for CI/local tests; no real Polar or Discord credentials are needed. The orchestrator CI also checks out a matching website candidate branch, falling back to website main once the coordinated work is integrated. Production deployment workflows are not invoked by release-branch pushes.
