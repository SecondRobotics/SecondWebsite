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
| Exhaustion | A separate zero-credit fixture account was rejected without a reservation or process being created. Later, the real paid VIP customer had an actual zero Polar meter balance during renewal: launch returned HTTP 403 and the server-session count was unchanged. This proves the tested launch path does not create paid overage at zero balance. |
| Duration cap | A 999-minute request was capped to a five-minute fixture plan. The real server stopped automatically with `max_runtime_elapsed`, and one 5-credit usage entry was recorded. |
| Callback outage/restart | Four callback files persisted while the configured receiver was unreachable. Restoring it and restarting the orchestrator replayed them, finalized one charge, and emptied the outbox. This used the complimentary fixture, not paid Polar usage. |
| Crash recovery | With one real ranked and one real casual process alive, the orchestrator was killed. Restart removed both old game processes; reconciliation finalized the lost casual session once. The test invoked reconciliation with zero staleness grace rather than waiting the normal ten minutes. It did not create a real Discord ranked match or prove its role/channel cleanup. |
| Period-end cancellation | A real sandbox cancellation webhook set the cancellation flag while retaining active access. Renewal was then restored. |
| Upgrade | After changing only the private acceptance products to fixed pricing, a real upgrade selected VIP from the actual product ID despite stale supporter metadata. The website showed 1,500 credits and a 240-minute limit; Polar also reported 1,500. |
| Scheduled downgrade | Polar scheduled a Supporter downgrade for the next period while current website access remained VIP. The test schedule was subsequently cleared. |
| Standalone renewal / no rollover | Fixed-price VIP renewal produced paid `subscription_cycle` order `60cd3321-9a77-4818-890b-1245fc3bcfa2`. After the provider's fifteen-minute order delay, both Polar and the website reported exactly 1,500 credits, consumed units zero, and the new period October 30–November 30. The previous 1,500 credits did not roll over; no webhook failures were present. |
| Revocation | Immediate revocation of the newly created test subscription removed access. A launch was rejected with HTTP 403 and created no session. A fresh VIP checkout was initially delayed, then completed. Real Polar VIP access and its 1,500-credit balance are restored. |
| Billing portal entry | `https://sandbox.polar.sh/secondrobotics/portal` was verified as this organization's customer portal sign-in page and configured as the test website's Manage billing destination. Customer portal sign-in and both Discord benefit connections were completed; actual portal UI billing changes remain separate from the API lifecycle checks. |

## Defects found and fixed during acceptance

1. **Idle bot polling:** the bot asked for a 25-second server wait with a 15-second HTTP deadline. Event requests now allow the whole wait plus overhead; Python 3.10 asyncio timeouts are translated consistently. Regression includes a delayed real localhost HTTP response.
2. **Webhook SDK aliases:** SDK `model_dump()` returned `TYPE`, so signed events were acknowledged but skipped. Serialization now uses wire aliases (`type`); a regression uses the actual SDK event model. Three stored real subscription events were recovered in the disposable test database.
3. **SQLite callback/response races:** stop-response recording, launch-response recording, and callback ownership lookup could upgrade a retained read lock while another writer was active. Stop uses a guarded SQL update; launch locks the user before reading; callback ownership is resolved before its write transaction. Three concurrent file-backed SQLite regressions pass, along with the complete Linux suite.
4. **Private discovery:** `SERVER_PUBLIC_DISCOVERY=false` forces `Register=Off` even when callers request public registration. This is enabled on the test orchestrator and documented for the initial beta.
5. **Return credential handling:** Polar appends a customer-session credential to the checkout success URL. The website discards it from the URL and redacts it from Django access logs. Reverse-proxy access logs must also avoid recording that parameter at eventual cutover.

## Findings that still block launch clearance

### Billing lifecycle and product configuration

The original sandbox Supporter/VIP products use **custom/name-your-price** prices. Polar rejects changing a subscription **to** a custom-price product. Fixed-price copies support the tested upgrade and scheduled downgrade. Nick approved **fixed $5/$12 launch pricing**. Configure production products accordingly; do not retain custom-price targets if normal plan switching is promised. Original products were not modified; only the private acceptance products use fixed prices.

The first deliberately shortened billing period advanced, and the meter's consumed units reset. Its old 360-credit benefit did **not** replenish before the later separate VIP upgrade granted 1,500. That upgrade was not proof of monthly replenishment. The separate follow-up below now proves standalone renewal and no rollover; a real zero-balance launch was also rejected. The organization's `reset` proration mode is disabled; tests used the supported `invoice` mode instead of changing organization settings.

A real past-due/failed-renewal payment lifecycle has not been exercised. Revocation, period-end cancellation, and mocked failure behavior are covered, but they do not replace this check.

Follow-up renewal diagnosis: the sandbox organization reports `subscription_renewals=true` and zero-day benefit-revocation grace. A second test shortened the **fixed-price** restored VIP subscription to `2026-10-30T01:58:55.051431Z`. Its period advanced to November 30, but initially there was no cycle order, and both provider balance and website spendable credits became zero. Polar's current public implementation deliberately defers recurring order creation for fifteen minutes after the cutoff, then cycles credit grants after the renewal order is paid ([order task](https://github.com/polarsource/polar/blob/main/server/polar/order/tasks.py), [paid-order handling](https://github.com/polarsource/polar/blob/main/server/polar/order/service.py)). At `02:14:26Z`, the deployed sandbox was observed to have produced paid recurring order `60cd3321-9a77-4818-890b-1245fc3bcfa2`; both provider and website had exactly 1,500 credits, and no webhooks had failed. Standalone replenishment and no rollover are now proven. The temporary zero-credit renewal interval is real behavior to account for in launch messaging.

The earlier upgrade order `bab5689d-5225-4aff-bc82-2f7342356614` has a $17 pre-tax subtotal with two lines: a $5 non-prorated Supporter cycle starting `14:15:57Z`, and a $12 VIP upgrade starting `14:24:09Z`. Thus the pending Supporter cycle was collected in the upgrade invoice; its absence as a separate cycle order does not demonstrate an uncharged renewal. The upgrade/grant still cannot prove standalone recurring credit replenishment.

The customer portal's Add Payment Method flow initially stalled on a dimmed loading overlay. One reload and retry opened the form successfully. Stripe's documented decline-after-attachment card ending `0341` was attached in sandbox. Polar automatically made the new card the default; a subsequent API check caught this, and the successful `4242` method `07587eda-50df-4821-ac3d-bf4d313f3b19` was restored and verified as default before the pending renewal charge. The failure method `aca3b621-e73d-4619-94a0-e5f3f953a649` remains attached for the subsequent failed-renewal test; attachment alone does not prove a payment failure. See [Stripe's test-card behavior](https://docs.stripe.com/testing#declined-payments).

After successful renewal, selecting the saved failure card showed “Failed to update default payment method / Failed to update customer.” A fresh attachment attempt stalled; refreshing returned the portal to sign-in. The session is now awaiting the owner's emailed verification code in Edge. The failure cause is not established. Final API verification still shows the successful `4242` card as default, subscription active through November 30, and no second shortened period scheduled. Resume failed-renewal setup after reauthentication; do not claim that gate passed.

### Discord benefit and real players

Discord role acceptance is now complete in the isolated guild: actual VIP grant/removal/regrant and Supporter grant/removal passed. Both private products preserve their credit benefits and use `kick_member=false`. The VIP product is restored to VIP-only role benefits. The original main-guild benefit was not edited. See the Discord test setup guide for exact IDs and evidence.

Still required with the game client/test players: join/password verification, actual player/chat/score/OPR updates, a complete ranked queue-to-ELO match, inactivity behavior, Discord match resource cleanup, and IP scoping with actual player data. Nick has confirmed two players can participate. The droplet initially blocked game ports; temporary source-restricted rules are now prepared as described below. A real Rebuilt 1v1 preflight reached running, listened on TCP and UDP port 11115 with public discovery off, and stopped. This is not a completed Discord ranked match or a real-client reachability test.

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

The copied catalog's stale saved-presets promise was cleaned using the existing migration. The acceptance products initially used credits only; their intended Discord benefits have since been configured and verified as described above. Preserve customized launch prices/allowances when applying the actual migration.

## Current state and next gates

- The real Polar VIP subscription `8889315a-38ce-40ee-aa7b-b7c2cd09cde2` passed standalone renewal: both provider and website report **1,500 credits** for October 30–November 30. The temporary complimentary fallback remains deactivated.
- Isolated Discord role acceptance is complete: VIP grant/removal/regrant and Supporter grant/removal were verified directly in Discord. VIP and guild membership were retained during final Supporter removal. Both private products have their intended final benefits, and the temporary extra Supporter benefit was removed from VIP. [Exact configuration and evidence](premium-discord-test-setup.md).
- No production/main-guild resources were changed, and all coordinated PRs remain unmerged.
- Follow the [ordered remaining live-test sequence](premium-live-test-sequence.md), including exact test queue/channel and evidence requirements. Temporary UFW rules now allow TCP/UDP ports 11115–11117 only from the current SSH client address; a private cleanup record is stored at `acceptance-firewall.json` under the test root. A second player on another network requires a separate source rule.
- Remaining billing gate: a failed-renewal/past-due lifecycle and payment recovery. Standalone recurring credit replenishment, no rollover, and rejecting actual zero-balance launches are now proven.
- Next owner participation: join a real test game and arrange players for a complete ranked match; provide a consistent fresh production database backup through a private file path for migration rehearsal.
- Production fixed $5/$12 product configuration, credentials, capacity validation, recurring workers, coordinated review, and separate cutover authorization remain required before launch.
