# Premium acceptance evidence — 2026-10-29

Status: **in progress; not cleared for merge or launch**. No production deployment or merge has been performed.

## Tested candidates and environment

- Website: `7b46bfc37bcbe04e8ff0c808a9b9dd80b6f35722`.
- Bot: `9927f3e` (acceptance found and fixed idle event polling timeouts).
- Orchestrator: `971a3b1` (adds a host control for private discovery).
- Isolated application files: `ssh digitalocean`, `/home/nick/.local/share/second-robotics-test/releases/20261029/`.
- Test website: loopback port 8000, available locally through the SSH tunnel at `http://localhost:8000/`.
- Test orchestrator: loopback port 3300. Port 3000 belongs to an existing unrelated service and was left intact.
- Discord: guild `663201408581107712`, application `724063847958184046`.
- Fresh SQLite database; only public game-mode and plan configuration copied. Production/customer databases were not copied.
- Python 3.12.16 (website), Python 3.10.22 (bot), Node 22.23.4 (orchestrator).

## Verified

- Fresh migrations and Django system checks pass.
- Discord OAuth redirects persist; real browser login returned successfully and created an authenticated test session.
- Test bot connects and completes startup in the selected guild.
- Linux automated verification: website **39 tests passed**, including the real HTTP contract test; bot **31 tests plus 2 log-parser tests passed**; orchestrator **27 tests passed** before the discovery addition. The updated orchestrator suite **28 tests passed locally**, and its build/test and website-contract CI checks passed.
- The original low-memory cross-service timeout and later OOM were resolved by cleaning up the orphaned test child and adding temporary swap; the complete website rerun passed.
- Real official xRC server v21.2b reached `running` with readiness timestamps for Override (23) and BioBuzz (24). Both then reached `stopped`; their OS processes were verified absent.
- Official Polar CLI authenticated against the **sandbox** SecondRobotics organization (not the separate SecondRoboticsSandbox organization).
- Configured meter: `ae0c267f-dbbf-4e3f-9041-2ac8d43eedac`; filter selects `casual_server_credits`, aggregation sums `credits`.
- Existing meter benefits grant 360 / 1,500 units with rollover disabled. The application token can read customer meters. It lacks product/meter inspection scopes; those inspections used the authorized CLI instead.
- Signed Polar sample `order.created` was forwarded through the official CLI to the real Django webhook handler: **200 OK**. Real `checkout.created` also returned **200 OK**.
- Real website checkout creation succeeds for the isolated Supporter test product; browser checkout is awaiting user completion.

## Acceptance fixes

Bot event requests previously used a 15-second timeout while asking the service to wait 25 seconds. Event polls now allow the complete wait plus response overhead; Python 3.10 asyncio timeouts are translated into the normal service-unavailable error. Regression tests exercise a delayed real localhost HTTP response and Python 3.10 timeout handling. Bot PR CI passed.

Orchestrator `SERVER_PUBLIC_DISCOVERY=false` forces `Register=Off` even if a caller requests registration. Set this during acceptance and the initial beta. Existing installations retain the prior default when unset.

## Test runtime compatibility

The droplet runs Ubuntu 20.04 with glibc 2.31; the current official game binary requires glibc 2.34 symbols. The test harness downloaded Ubuntu Jammy libc6 2.35-0ubuntu3.15, verified the signed Ubuntu archive index and SHA256 hashes, and extracted it into the private test runtime. Only the test executable's interpreter/RPATH were changed; its original executable is preserved as `xRC Simulator.x86_64.original`. System libc and unrelated services were not changed.

A temporary 512 MiB swap file at `/home/nick/.local/share/second-robotics-test/acceptance.swap` is active, with root ownership and mode 600. It is not configured to survive reboot. Test startup timeout is 120 seconds. The host is shared and memory constrained; these accommodations do not establish production capacity. Confirm the production host can run the chosen official binary and sustain the planned concurrency before cutover.

## Billing isolation

Existing sandbox products include a Discord role benefit pointing at the main guild. To avoid changing that guild during acceptance, separate private sandbox products were created with only the matching meter-credit benefits:

| Tier | Test product ID |
| --- | --- |
| Supporter | `4a900d30-03fb-45cb-a0c4-9053f964d966` |
| VIP Supporter | `794d2bb8-5f3b-4868-975a-fb7c181d8a70` |

Only the test database uses these mappings. Main sandbox products and their benefits were not modified. Discord-role acceptance remains outstanding.

The signed-in account already had an older active sandbox VIP subscription under its original email, with no customer external ID. It was left intact. Only the disposable Django account email was changed to a unique acceptance alias for fresh checkout; the real Discord identity is unchanged. A subsequent OAuth login refreshes that test profile email, so finish this run before logging in again.

Secrets remain in private configuration on the host and the CLI's local credential store; never commit or print them. The official local CLI forwards only to `http://localhost:8000/subscriptions/polar/webhook/`, through the SSH tunnel. Its protected log and temporary files live under `/private/tmp/second-e2e-prep/`. Forwarding and the SSH tunnel must remain running for real checkout events to arrive.

## Remaining gates, in order

1. Complete the open **sandbox** Supporter checkout. Verify real subscription webhooks, correct entitlement, 360-credit grant, and no rollover/paid overage configuration.
2. Exercise real casual launches from the website and Discord command. Verify concurrency rejection, duration bounds, stops from both entry points, exactly one five-minute-rounded ledger charge per session, ingestion, and matching meter debit.
3. Exercise live retry/recovery: Polar unavailable at stop, callback outbox replay after website outage, orchestrator restart with live casual/ranked processes, and recovery without double charging.
4. Exercise sandbox lifecycle: upgrade/downgrade, period-end cancellation, renewal reset, past-due/revoked access, and manage-billing link. `POLAR_CUSTOMER_PORTAL_URL` remains to be configured/verified.
5. Configure and verify an isolated Discord role benefit; current test products intentionally omit the main-guild benefit.
6. User deferred real-client/multiplayer participation until automated checks are complete. Still required: client joins, password/player/chat/score verification, complete ranked match, ELO submission, inactivity and resource cleanup, and moderation/IP scoping with actual players.
7. Rehearse migrations on a fresh production backup, review coordinated PRs, and obtain separate merge/cutover authorization.

The catalog import initially reintroduced stale editable plan copy in the test database. The existing saved-presets migration cleanup was reapplied, and main-guild role promises were removed from the credit-only test plans; do not interpret those promises as implemented features. Preserve customized plan prices and allowances.
