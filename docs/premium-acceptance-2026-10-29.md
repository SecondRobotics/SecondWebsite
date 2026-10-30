# Premium acceptance evidence — 2026-10-29

**Status: core integration proven; remaining launch gates are listed below. Do not merge or deploy yet.**

No production deployment, merge, production billing change, or main-guild role change was performed. The three coordinated PRs remain unmerged: website #67, bot #85, orchestrator #18.

## Candidate verification

| Candidate | Code revision | Verification |
| --- | --- | --- |
| Website | `020a90c` | 45 tests pass locally and on the Linux droplet, including real Django/Fastify HTTP contracts and three concurrent SQLite regressions; final code CI passes |
| Ranked bot | `9927f3e` | 31 tests plus 2 log-parser tests pass on Linux; CI passes |
| Orchestrator | `971a3b1` | 28 tests pass locally and in CI; build and website-contract CI pass; preceding 27-test suite also passed on the droplet |

Fresh database migrations and Django system checks pass. The test database contains copied public game/plan configuration and disposable test users; no production/customer database was copied.

## Live acceptance results

| Gate | Evidence |
| --- | --- |
| Discord OAuth | Both registered localhost redirects persist. Real login returned successfully and created an authenticated session for the intended Discord account. |
| Bot connectivity | The test bot connects and completes startup in Nick's Test Server. A real 25-second idle event poll completes without timing out. |
| Real game processes | Official xRC v21.2b starts Override (23) and BioBuzz (24), reaches `running` with readiness timestamps, then stops. Old OS processes were verified absent. |
| Sandbox checkout | Browser test-card checkout succeeded and created a real Supporter subscription. Initial custom-price checkout could remain in `confirmed` for several minutes before completing. |
| Entitlement and credits | Real signed subscription events activate the correct plan. The initial grant was 360 credits. |
| Service API launch | A Polar-backed real Override session launched through the bot's website API contract. Concurrent launch was rejected (HTTP 403, existing website contract), stop succeeded, and duplicate stop retained one ledger entry. |
| Website UI | A real BioBuzz session launched and stopped using the browser forms. |
| Actual Discord commands | `/casual_start` with Override autocomplete and 5 minutes created a real session; `/casual_status` reported it running; `/casual_stop` finalized it. |
| Usage billing | Three real subscriber sessions each produced one 5-credit ledger entry. Ingestion succeeded, and Polar consumption/balance matched 15 credits consumed / 345 remaining before lifecycle tests. |
| Aggregation delay | After accepted ingestion but before meter aggregation, Polar still reported 360 while the website held the charge and exposed 355. Once aggregation reached 5 consumed, website and meter both reported 355. |
| Ingestion outage | One real usage entry was synced against an intentionally unreachable Polar URL. It became failed; spendable credits stayed held. Restoring the real sandbox endpoint sent it successfully. Re-sync did not duplicate the ledger charge. |
| Exhaustion | A separate zero-credit fixture account was rejected without a reservation or process being created. |
| Duration cap | A 999-minute request was capped to a five-minute fixture plan. The real server stopped automatically with `max_runtime_elapsed`, and one 5-credit usage entry was recorded. |
| Callback outage/restart | Four callback files persisted while the configured receiver was unreachable. Restoring it and restarting the orchestrator replayed them, finalized one charge, and emptied the outbox. This used the complimentary fixture, not paid Polar usage. |
| Crash recovery | With one real ranked and one real casual process alive, the orchestrator was killed. Restart removed both old game processes; reconciliation finalized the lost casual session once. The test invoked reconciliation with zero staleness grace rather than waiting the normal ten minutes. It did not create a real Discord ranked match or prove its role/channel cleanup. |
| Period-end cancellation | A real sandbox cancellation webhook set the cancellation flag while retaining active access. Renewal was then restored. |
| Upgrade | After changing only the private acceptance products to fixed pricing, a real upgrade selected VIP from the actual product ID despite stale supporter metadata. The website showed 1,500 credits and a 240-minute limit; Polar also reported 1,500. |
| Scheduled downgrade | Polar scheduled a Supporter downgrade for the next period while current website access remained VIP. The test schedule was subsequently cleared. |
| Revocation | Immediate revocation of the newly created test subscription removed access. A launch was rejected with HTTP 403 and created no session. A fresh VIP checkout was submitted afterward; it remained confirmed without a payment or new subscription at the final provider check. |
| Billing portal entry | `https://sandbox.polar.sh/secondrobotics/portal` was verified as this organization's customer portal sign-in page and configured as the test website's Manage billing destination. Customer authentication inside that portal remains a manual gate. |

## Defects found and fixed during acceptance

1. **Idle bot polling:** the bot asked for a 25-second server wait with a 15-second HTTP deadline. Event requests now allow the whole wait plus overhead; Python 3.10 asyncio timeouts are translated consistently. Regression includes a delayed real localhost HTTP response.
2. **Webhook SDK aliases:** SDK `model_dump()` returned `TYPE`, so signed events were acknowledged but skipped. Serialization now uses wire aliases (`type`); a regression uses the actual SDK event model. Three stored real subscription events were recovered in the disposable test database.
3. **SQLite callback/response races:** stop-response recording, launch-response recording, and callback ownership lookup could upgrade a retained read lock while another writer was active. Stop uses a guarded SQL update; launch locks the user before reading; callback ownership is resolved before its write transaction. Three concurrent file-backed SQLite regressions pass, along with the complete Linux suite.
4. **Private discovery:** `SERVER_PUBLIC_DISCOVERY=false` forces `Register=Off` even when callers request public registration. This is enabled on the test orchestrator and documented for the initial beta.
5. **Return credential handling:** Polar appends a customer-session credential to the checkout success URL. The website discards it from the URL and redacts it from Django access logs. Reverse-proxy access logs must also avoid recording that parameter at eventual cutover.

## Findings that still block launch clearance

### Billing lifecycle and product configuration

The original sandbox Supporter/VIP products use **custom/name-your-price** prices. Polar rejects changing a subscription **to** a custom-price product. Fixed-price copies support the tested upgrade and scheduled downgrade. Nick approved **fixed $5/$12 launch pricing**. Configure production products accordingly; do not retain custom-price targets if normal plan switching is promised. Original products were not modified; only the private acceptance products use fixed prices.

A deliberately shortened billing period advanced to a new period, and the meter's consumed units reset. However, its old 360-credit benefit did **not** replenish within the observed test window; balance remained zero before the later separate VIP upgrade granted 1,500. Do not treat the successful upgrade grant as proof of monthly renewal replenishment. Resolve and retest actual renewal grants, no rollover, and no paid overage before launch. The organization's `reset` proration mode is disabled; tests used the supported `invoice` mode instead of changing organization settings.

A real past-due/failed-renewal payment lifecycle has not been exercised. Revocation, period-end cancellation, and mocked failure behavior are covered, but they do not replace this check.

### Discord benefit and real players

The existing sandbox products include a role benefit pointing at the **main guild**. Acceptance products omit that benefit to avoid changing main-guild roles. If the launch promises a Discord role, install/configure Polar's role integration for the isolated guild and test grant/revocation there. Otherwise remove that promise from actual launch plan copy.

Still required with the game client/test players: join/password verification, actual player/chat/score/OPR updates, a complete ranked queue-to-ELO match, inactivity behavior, Discord match resource cleanup, and IP scoping with actual player data. Nick deferred player participation until automated checks were complete.

### Production prerequisites

- Rehearse migrations on a **fresh production backup**. Only the older local copy and a fresh empty database have been rehearsed so far.
- Verify the production host can run the official binary and sustain planned concurrency. The current test host required private newer libc and temporary swap.
- Configure production product/meter/benefit IDs, webhook secret, portal URL, service tokens, and recurring workers separately. Sandbox IDs must not be reused in production.
- Review all three PRs together and obtain separate merge/cutover authorization. Website main pushes trigger automatic deployment.

## Isolated test environment and preservation

- SSH alias: `digitalocean`.
- Root: `/home/nick/.local/share/second-robotics-test/`; release directory: `releases/20261029/`.
- Website listens on `127.0.0.1:8000`; localhost-only SSH forwarding exposes it at `http://localhost:8000/`.
- Orchestrator listens on `127.0.0.1:3300`. Existing unrelated services on port 3000 were left intact.
- Guild: `663201408581107712`; bot application: `724063847958184046`.
- Runtimes: Python 3.12.16 / Python 3.10.22 / Node 22.23.4.
- The droplet is Ubuntu 20.04, glibc 2.31. Official xRC requires newer libc symbols. Ubuntu Jammy libc6 2.35-0ubuntu3.15 was verified using the signed archive index and SHA256 hashes and extracted privately. Only the test binary's interpreter/RPATH were changed; its original is preserved as `xRC Simulator.x86_64.original`. System libc was not replaced.
- Temporary root-owned mode-600 512 MiB swap file: `acceptance.swap`; it is not configured across reboot. Test startup timeout is 120 seconds. These accommodations do not establish production capacity.
- Private service configuration remains mode 600. Logs, callback outbox, and score archives must be preserved across test restarts. Pending callback files contain connection credentials.
- Official Polar CLI is authenticated to sandbox **SecondRobotics**, not the separate **SecondRoboticsSandbox** organization. It forwards signed events to the private website through the SSH tunnel. Private local artifacts/forwarder logs are under `/private/tmp/second-e2e-prep/`.
- The interrupted turn closed the original SSH tunnel; it was restored as a separate process. Forwarding and the CLI listener must remain running for future events.
- An older sandbox VIP subscription under the original email was left intact. Only the disposable Django profile email was changed to a unique acceptance alias to avoid that pre-existing customer conflict. Do not delete the older subscription as cleanup for this run.

| Tier | Private acceptance product |
| --- | --- |
| Supporter | `4a900d30-03fb-45cb-a0c4-9053f964d966` |
| VIP Supporter | `794d2bb8-5f3b-4868-975a-fb7c181d8a70` |

The copied catalog's stale saved-presets promise was cleaned using the existing migration, and role promises were removed from these credit-only test plans. Preserve customized launch prices/allowances when applying the actual migration.

## State left for the next acceptance step

- Final website code is running on the droplet after the 45-test Linux pass; all code PR checks are green. No game sessions were intentionally left running.
- The post-revocation VIP checkout remained in `confirmed`, with a blank Stripe 3-D Secure challenge and no payment/subscription at the last check. Reloading it did not resolve the pending provider state. Browser control disconnected during the final UI verification. Do not submit repeated duplicate checkouts or report restoration as successful.
- To keep client acceptance usable while that checkout is pending, the disposable account has a clearly labelled **Temporary client acceptance** complimentary entitlement for two days: 1,500 credits, 240-minute maximum, priority -100. A normal active Polar plan has higher priority and automatically wins. This fixture does not constitute paid-billing or renewal evidence; its usage is not sent to Polar.
- Next owner inputs, in order: authorize/configure the isolated Polar Discord-role integration if roles remain promised; join the test game server and arrange enough people for a complete ranked match; provide a fresh production database backup through a private file path for rehearsal. These can proceed alongside resolving the remaining renewal/checkout provider issues.

Discord setup is now partially automated: two zero-permission premium roles have been created in the test guild. The CLI confirms the remaining blocker is merchant-side Discord server authorization. Exact pages and IDs are in [the Discord test setup guide](premium-discord-test-setup.md).

### Discord integration follow-up

Merchant-side authorization is complete. Both isolated role benefits are attached with `kick_member=false`, credit benefits are preserved, and Polar's role hierarchy is corrected. The real VIP grant is pending **customer Discord account connection**, not server setup. Exact benefit/grant/role IDs and the portal step are in the Discord test setup guide. The restoration checkout now has an active VIP subscription in Polar (`8889315a-38ce-40ee-aa7b-b7c2cd09cde2`), superseding the earlier confirmed/pending observation.
