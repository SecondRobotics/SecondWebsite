# Second Robotics premium hosting: launch readiness

Assessment date: October 28, 2026.

**Recommendation: do not launch paid subscriptions yet.** Most of the feature exists, but the three release candidates have not been assembled, several normal user actions fail across service boundaries, and billing/recovery paths still have correctness gaps. The next milestone should be a coordinated private beta with Polar sandbox billing, followed by a public launch after the gates below pass.

This is a repository, history, PR, and targeted code review. It does not establish what is currently deployed or configured on production hosts. No application code was changed, no stash was applied to your checkouts, no branches were switched, and no deployment or real billing operation was performed. Tests and reproductions used disposable environments and copies where necessary. This report is the only intentional repository addition from this assessment.

## Where the work actually is

| Repository | Current local state | Remote/review state | What to recover or integrate |
| --- | --- | --- | --- |
| SecondWebsite | `polar-subscriptions` at `9442fed`, plus local changes | [Draft PR #62](https://github.com/SecondRobotics/SecondWebsite/pull/62), open and reported mergeable when inspected. Its committed head has a successful test check. | Local API-key guard, Polar usage retry state/command, migration `0004`, admin/test/CI changes. Integrate six newer commits from remote `main`. |
| xRCRankedBot | Clean `main` at `66a707c` | Current main includes October game/autocomplete fixes. No open migration PR; the only open PR found was dependency PR #84. | Migration is in **`stash@{0}`**, based on `orchestrator-service` at `d437db3`. Several essential new files are in the stash's untracked-files parent. Recover onto current main carefully. |
| xRCServerOrchestrator | `main` at `aa276a4`, one commit ahead of `origin/main`, plus substantial local changes | GitHub `main` remains `cda4a4e`. No non-Dependabot PR was found. | Push/review the binary-diagnostics commit and integration changes: website callbacks/auth, casual lifecycle/idempotency, games endpoint, restart default, tests. |

Important recovery identifiers:

```text
Bot migration stash:        42f72f2f8abb38f21942e2008350a4fdc9239736
Bot stash untracked tree:   6b30ab4f138d2bb467109eef9dbcb0e459bc6ec4
Bot migration base branch:  d437db311117b3bd6eb906dfcbeb8b7a1ede209b
Website subscription head:  9442fed5efc63b9ca417320fed37a1fcb94e8030
Website remote main:       0cb4eb66fd82ebd1045a0e55eeefa45b0a4a38d7
Bot remote main:           66a707ca9ed49e0dbf70bfbe34179d169a9d0dbd
Orchestrator remote main:  cda4a4e784fbdac310092648def2bc32c4639639
```

The bot stash includes new `orchestrator_client.py`, `website_client.py`, `cogs/casual.py`, orchestration tests, and CI. It removes the old hangout cog and changes ranked/server flows. Checking out `orchestrator-service` alone does **not** restore the migration. The stash was reviewed by extracting both the tracked snapshot and its untracked-files tree into a temporary directory.

The website branch is seven feature commits ahead of the common ancestor and lacks six commits now on remote main, including high-score client gates, BioBuzz ranked/high-score changes, and the wheel update. The locally cached `origin/main` is stale; its apparent two-commit divergence understates the current remote divergence. [Current website main](https://github.com/SecondRobotics/SecondWebsite/tree/main).

## Decisions recovered from earlier chats

Reviewed the subscription design chat, the orchestrator and bot implementation chats, and the July 7 launch review/follow-up.

- **Polar is the v1 paid provider**, using its Python SDK and credits/meter system. GitHub Sponsors and native Discord subscriptions are future possibilities, not unfinished v1 requirements.
- **Casual hosting goes through the website**, whether initiated on the site or in Discord. The website owns entitlement checks, reservations, and usage records. The orchestrator owns actual game processes.
- Ranked hosting stays free and launches directly from the bot to the orchestrator. Admin hosting remains staff-controlled.
- Bot/orchestrator calls into the website use the existing shared `API_KEY` in `X-API-KEY`; calls to the orchestrator use bearer tokens with scopes.
- **In-memory orchestrator state is intentional.** You explicitly accepted closing all servers on restart and relaunching them afterward. Persistence is not a prerequisite; reliable shutdown, website cleanup, and Discord recovery are.
- Migration baseline repair is a known deployment task. Legacy migration files were previously inconsistent/untracked; rehearse the existing-database transition rather than blindly applying a fresh-database recipe.
- Sandbox testing was accepted. The premium navbar link was deliberately hidden for initial direct-link production testing. `/subscriptions/` remains accessible.
- Agent handoff docs were not intended to be committed merely because they exist locally. Documentation cleanup is not itself a launch blocker.

The July follow-up implemented the API-key guard, retryable Polar usage, bot player/OPR compatibility, and the default restart mode. Those changes are present, but largely remain local or stashed. Its prior “implemented” conclusion should not be read as “integrated and launch verified.”

## What is already implemented

| Area | Implemented behavior | Qualification |
| --- | --- | --- |
| Plans and entitlements | Database-configured plans, price/product/role IDs, monthly allowance, session/concurrency limits, priority selection, comp/provider-neutral entitlements, Django admin | Polar products/benefits still need matching configuration. Adding a provider choice does not implement that provider's billing integration. |
| Billing integration | SDK checkout, signed webhook validation, subscription upserts, meter balance reads, usage ingestion with stable session external IDs | Existing tests mock Polar. A real sandbox billing lifecycle remains unverified here. |
| Website casual hosting | Subscription page, plan/balance/session display, launch and stop forms, authenticated/service APIs, credit reservations, lifecycle callbacks | Start/stop contracts and recovery need fixes below. The page requires refresh for updated state. |
| Usage resilience | Local ledger, one usage entry per session, rounding, pending/failed/sent fields, retry command, admin visibility | Local changes; pending usage is not currently held against the spendable Polar balance. Ingestion still runs inline; exceptions are contained. |
| Orchestrator | Process launch/stop/restart/kill, port allocation, logs/chat/player/score APIs, moderation scopes, admin UI, metrics/readiness, binary updater, runtime limits, events, website callbacks with retries | Core exists on remote; important website-integration behavior is uncommitted locally. Real binary/host behavior needs a smoke test. |
| Bot migration | Orchestrator and website clients; ranked/admin launch/stop/status/moderation paths; website-proxied casual start/status/stop; inactivity and score events; old hangouts removed | In stash. Unit tests pass, but it predates newer main changes and has stale-cache behavior. |
| Previous display fixes | Accepts orchestrator `playerName`/`ipAddress` and split `redOpr`/`blueOpr` | Present in bot stash and covered by tests. |

The seeded tiers remain Supporter at $5/month, 360 credits and 120-minute sessions; Host at $12/month, 1,500 credits and 240-minute sessions. These are code defaults, not verification of live Polar pricing. Both default to one concurrent server, and one credit represents a runtime minute with five-minute rounding.

## Launch blockers and required fixes

### 1. P1 — Discord casual launch is rejected by the orchestrator

The website constructs `actor.type = "discord_bot"` for a bot-origin launch. The orchestrator only accepts `discord_user`, `website_user`, `service`, and `system`.

Evidence: [website launch actor](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:334), [orchestrator actor schema](/Users/nick/GitHub/xRCServerOrchestrator/src/services/launchSchemas.ts:3).

**Reproduction:** sending the website's bot-origin payload to the actual Fastify route with the fake runner returned HTTP 400 `VALIDATION_FAILED` at `actor.type`.

**Required:** agree on an accepted actor representation, preserve the initiating Discord identity, and test bot → website → actual orchestrator validation. Current unit mocks accept invalid payloads.

### 2. P1 — Website-proxied stop requests omit a required actor

Website UI/API callers invoke `request_stop_server_session` without an actor. The website client then sends only `reason`, while the orchestrator stop schema requires `actor`. This affects website stops and casual stops proxied from Discord.

Evidence: [stop service](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:574), [outgoing stop payload](/Users/nick/GitHub/SecondWebsite/subscriptions/orchestrator.py:83), [required actor](/Users/nick/GitHub/xRCServerOrchestrator/src/services/launchSchemas.ts:68).

**Reproduction:** a valid website-style launch returned HTTP 201; stopping that session using the website's payload returned HTTP 400 `VALIDATION_FAILED`, `actor: Required`.

**Required:** supply the appropriate actor or define a deliberate server-side default. Test both entry points against real request validation.

### 3. P1 — Failed Polar usage becomes spendable again

For Polar users, `available_credits` subtracts open-session allocations from the remote meter balance, but does not subtract stopped-session usage waiting for successful Polar sync. Once a session stops, its reservation disappears even if ingestion failed. The same risk needs consideration during meter-processing delay after ingestion succeeds.

Evidence: [available credits](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:108), [usage sync](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:410).

**Reproduction:** a user with a remote balance of 60 consumed 60 minutes; ingestion failed and the ledger correctly recorded 60 failed credits. The website nevertheless reported 60 available credits and authorized another 60-minute session.

**Required:** reconcile unreflected local usage with Polar balance and active reservations. Retain a hold until usage is safely reflected, without subtracting already-reflected usage twice. Cover outages, retry, delayed meter updates, and concurrent launch requests.

### 4. P1 — Callback ordering can resurrect completed sessions

The orchestrator sends callbacks independently with retries. A delayed `ready` or `launch_accepted` event can arrive after `stopped`; the website unconditionally sets the session back to running/launching. The launch-response handler also unconditionally writes `launching`, potentially overwriting an earlier ready/terminal callback. Event-ID deduplication does not protect against different events arriving out of order.

Evidence: [launch response update](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:340), [callback transitions](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:490), [independent callback sends](/Users/nick/GitHub/xRCServerOrchestrator/src/services/serverManager.ts:655).

**Reproduction:** process `stopped`, then an older `ready` with a different event ID. The website ends up `running` while a usage ledger entry already exists.

**Required:** enforce legal/monotonic lifecycle transitions, terminal-state protection, and freshness/ordering rules. Test delayed delivery and callbacks racing launch/stop responses.

### 5. P1 — Failed Polar webhooks are acknowledged on retry without reprocessing

`process_polar_webhook` writes an event before processing. On failure it preserves that event as failed. A later delivery with the same ID immediately returns the existing record, and the HTTP view responds successfully. Fixing a missing plan mapping then redelivering does not repair the entitlement.

Evidence: [webhook deduplication and failure path](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:611), [HTTP response](/Users/nick/GitHub/SecondWebsite/subscriptions/views.py:108).

**Reproduction:** deliver a subscription event with an unmapped product, add the product mapping, then redeliver the identical event ID. It remains failed and no entitlement is created.

**Required:** deduplicate successfully completed events, support safe retry of failed processing, and expose a replay/recovery path. Also test older subscription events arriving after newer entitlement state.

### 6. P1 — Destructive restart recovery is incomplete

The chosen restart policy is valid, but changing the default to `stop` does not finish recovery:

- Startup reconciliation sends SIGTERM to matching xRC processes without waiting for exit or escalating if they ignore it. Exceptions are logged, but reconciliation is marked complete in `finally`, so readiness can be reported despite failure.
- The website's stale-session command only selects `running`. Lost stop callbacks can leave `stopping` sessions open indefinitely; lost ready callbacks/launch races can leave `launching` sessions open indefinitely. Those sessions reserve credits and block new launches.
- Running sessions are billed using cleanup time, capped by allocation, rather than a proven actual stop time. After a crash/restart this can overstate runtime.
- Callback retries are finite and in memory. Once a terminal callback exhausts retries, there is no durable delivery/reconciliation path. A cron alone does not solve all the states above.
- The bot's event consumer handles match timer/inactivity/chat events, not server termination/restart events. Existing ranked Discord state is not automatically reconciled when the orchestrator loses its old session IDs.

Evidence: [startup reconciliation](/Users/nick/GitHub/xRCServerOrchestrator/src/services/serverManager.ts:751), [process termination](/Users/nick/GitHub/xRCServerOrchestrator/src/services/processInspector.ts:50), [website cleanup](/Users/nick/GitHub/SecondWebsite/subscriptions/services.py:592), bot stash `cogs/server.py:552`.

**Reproduction:** stale `launching` and `stopping` sessions were both ignored by `expire_stale_sessions`.

**Required:** verify processes have actually exited before accepting fresh work; keep readiness failed on reconciliation failure; reconcile every open website state with a defensible billing cutoff; define ranked Discord cleanup on restart. This can remain a simple destructive-restart design without adding persistent live-session storage.

### 7. P1 — The local billing migration fails the required CI gate

The model's unnamed `polar_status` index generates `subscriptio_polar_s_d17737_idx`; migration `0004` explicitly creates `subscriptio_polar_s_9533a3_idx`. Django detects a missing migration.

Evidence: [model index](/Users/nick/GitHub/SecondWebsite/subscriptions/models.py:238), [migration index](/Users/nick/GitHub/SecondWebsite/subscriptions/migrations/0004_usage_polar_sync_state.py:35).

**Reproduction:** `manage.py makemigrations --check --dry-run` exits 1 on both the old venv and a fresh Python 3.12/Django 5.2.18 environment. Django 5 proposes a `RenameIndex` migration.

**Required:** align model/migration index names or add the appropriate migration, then pass the gate. This is separate from the already-known production baseline rehearsal.

### 8. P1 — Assemble the release without losing newer games or the dropdown fix

The recovered bot migration and orchestrator know game codes through `22`. Bot main also supports Override (`23`) and BioBuzz (`24`). The migration still uses fixed `@app_commands.choices` lists, including its new casual command. Blindly restoring old config loses games; adding newer games while retaining fixed choices risks reintroducing the October startup failure.

Evidence: [orchestrator catalog](/Users/nick/GitHub/xRCServerOrchestrator/src/config/games.ts:3), [current bot catalog](/Users/nick/GitHub/xRCRankedBot/config.py:101), bot stash `cogs/casual.py:83` and its ranked/server decorators.

**Reproduction:** actual orchestrator route requests for codes `23` and `24` both returned HTTP 400 `Unknown gameCode`.

**Required:** recover the stash onto current bot main, preserve its autocomplete/tests/CI and game names, give the new casual command compatible selection, update the orchestrator catalog and binary, and integrate current website main. Verify slash-command registration and launching both newer games. Commit and review all three resulting release candidates.

## Other remaining work

- **Bot casual status cache:** `_get_active_website_session` returns a cached active record without refreshing it. After automatic expiry or a website stop, `/casual_status` can indefinitely show an old launching/running session. Query the website or use bounded cache freshness. Also review the bot's 180-minute input ceiling against Host's advertised 240-minute sessions. Evidence: bot stash `cogs/casual.py:71–89`.
- **Advertised benefits:** seeded Host copy promises saved presets/faster relaunch, but no preset implementation was found. `discord_role_id` is stored/admin-editable; no role-sync implementation was found in these repositories. Either configure/test Polar's Discord benefit externally, implement missing benefits, or change launch copy. Do not sell promises without a working delivery path.
- **Orchestrator retry test:** one complete check run failed and a rerun passed. The test waits for any two fetches, then asserts two `launch_accepted` fetches; a different callback can satisfy the wait early. Wait for the specific retried event. Evidence: [retry test](/Users/nick/GitHub/xRCServerOrchestrator/test/api.test.ts:408).
- **Deployment configuration:** explicitly configure production bearer tokens/scopes; the orchestrator has a permissive default development token. Configure matching shared keys, correct base/public host URLs, real process mode/binary, paths/permissions, ports/firewall, and exactly one chat-relay owner. `/readyz` alone does not validate billing or callback credentials.
- **Recurring jobs and observability:** install and verify `sync_polar_usage` and corrected stale-session cleanup on the actual host. Alert on failed usage, failed webhooks/callbacks, stale open sessions, and failed startup reconciliation. No live scheduler configuration was verified.
- **Dependencies:** there are open dependency PRs in all three repositories. Triage them in the release dependency review; this assessment did not perform a complete vulnerability audit. Avoid assuming every dependency bump is a required compatible change.

## Verification performed

| Check | Result | What it proves / limits |
| --- | --- | --- |
| Website existing pytest suite, old `.venv` | 25 passed | Old local runtime is Python 3.9/Django 3.2; this alone was insufficient. |
| Website existing pytest suite, fresh declared dependencies | **25 passed** on Python 3.12.9/Django 5.2.18 | Fresh test database migrations execute; service tests remain heavily mocked. |
| Django system checks, fresh runtime | Passed | Settings/app checks; no live service validation. |
| Missing-migration check, fresh runtime | **Failed** | Index naming drift described above. |
| Bot recovered stash unit tests | **16 passed** | Includes 14 orchestration/client/command tests and two log-regex tests. Uses existing Python 3.9 venv; not the final merged bot candidate or its CI runtime. |
| Bot current main tests in existing venv | Blocked at import: missing `psutil` | Environment deficiency; does not establish a product regression. Final merged candidate needs a fresh Python 3.10 dependency install and full tests. |
| Orchestrator admin + TypeScript build | Passed | Temporary source copy with installed local dependencies; Node 24 locally versus Node 22 in CI. |
| Orchestrator API suite | 19/20 on first check, **20/20 on rerun** | Retry-test race above. Fake processes, not real xRC. |
| Targeted website reproductions | **Four confirmed**, including on fresh runtime | Failed usage reuse; delayed-ready resurrection; failed-webhook replay; cleanup ignoring launching/stopping. Assertions intentionally check for the observed defects. |
| Actual Fastify route contract probes | **Four failures confirmed** | Invalid Discord actor, missing stop actor, missing Override, missing BioBuzz. No real game process or billing calls. |
| Website PR #62 committed-head CI | Successful `test` check at `9442fed` | Does not cover local retry/guard/migration changes. [CI run](https://github.com/SecondRobotics/SecondWebsite/actions/runs/28843125089). |
| Bot current remote main CI | Successful `test` and `check-lock` checks at `66a707c` | Does not cover the stashed migration or its eventual integration. |
| Orchestrator current remote main CI | **Failed** `build-and-test` at `cda4a4e` | [Existing failed job](https://github.com/SecondRobotics/xRCServerOrchestrator/actions/runs/26490784587/job/78077388472). Retained annotation: long-poll event test expected HTTP 200, received 404 (`test/api.test.ts:230`). Full logs have expired (HTTP 410). The local candidate results above are separate; require fresh CI on the assembled release. |

The modern Python environment and orchestrator/bot copies were disposable. No production SQLite migration, live checkout, real Polar ingestion, Discord registration, game-client join, or remote restart was exercised. Existing green unit tests do not imply the services work together; the contract probes demonstrate why an integration test is necessary.

## Recommended completion sequence

1. **Recover and pin release candidates.** Preserve the bot stash, recover it onto current main, integrate website main, and put orchestrator local changes into reviewable commits. Include untracked implementation files and migration `0004`; exclude unrelated generated static files and temporary handoff docs as appropriate. Record all three SHAs.
2. **Fix the blockers above.** Start with actor contracts and migration drift, then accounting, webhook/callback ordering, and restart/reconciliation. Add targeted regression tests and one actual-schema integration test between website and orchestrator. Resolve catalog/autocomplete drift as part of assembly.
3. **Run the intended CI environments.** Website Python 3.12 with declared dependencies; bot Python 3.10 with its merged tests; orchestrator Node 22 with `npm ci` and `npm run check`. Require clean migration checks. Rehearse the baseline transition on a copy of the current production SQLite database, then verify ordinary migrations and seeded plans. Back up before production migration.
4. **Run a small sandbox acceptance matrix.** Use Polar sandbox products/meter/credits benefits and a test Discord guild. Verify checkout → signed entitlement event → launch from website and Discord → ready → client join → stop → one ledger entry → one reflected Polar charge. Confirm balance subtraction and five-minute rounding. Test no entitlement, exhausted balance, concurrency, max duration, failed launch, and subscription cancellation/end-of-period behavior.
5. **Exercise failure recovery.** Drop/reorder callbacks; make Polar unavailable while stopping; restore it and retry without overspending/double charging. Restart/kill the orchestrator with one casual and one ranked session active: all old processes must die, paid sessions must finalize once, credits/concurrency must recover, Discord match resources must be cleared, and fresh launches must succeed. Test callbacks exhausted while the website is down.
6. **Real xRC/ranked smoke.** Use the actual Linux binary: launch/join a casual session and a ranked match; inspect players, scoped IP visibility, chat relay, scores/OPR, match-end/inactivity workflows, ELO submission, and cleanup. Include Override and BioBuzz after catalog/binary alignment.
7. **Coordinated maintenance cutover.** Treat this as one release. Pause new launches and drain active legacy bot servers before starting an orchestrator configured to terminate existing xRC processes. Deploy/migrate the website, start the verified orchestrator, then switch the bot to the matching release. Enable recurring jobs and monitoring, and run direct-link acceptance with the navbar still hidden. Define rollback before beginning: stop new launches, drain processes, revert matching service versions, retain database backups, and reconcile outstanding billing rather than blindly rolling back schema/data.
8. **Public enablement.** Complete the hidden beta, confirm role benefits and tier copy, verify production Polar configuration and a controlled paid lifecycle, then expose the premium link and announce. Switching out of sandbox needs its own production product/meter/key/benefit verification.

## Practical readiness summary

The foundation is substantial: this is integration and reliability completion, not a project that needs to be rebuilt. The most immediate problems are concrete and reproducible. A calendar launch estimate would be premature until the bot stash is integrated and the failure-recovery fixes pass. Call the system ready only when one pinned three-repository release passes the sandbox matrix, real ranked/game smoke, migration rehearsal, and destructive-restart test.
