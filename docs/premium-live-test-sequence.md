# Remaining live acceptance sequence

Use the isolated 20261029 release on `ssh digitalocean`, test guild
`663201408581107712`, and bot `724063847958184046`. No production deployment
or merge is authorized. Completed evidence remains in
[the acceptance report](premium-acceptance-2026-10-29.md).

| Order | Operator action | Required evidence |
| --- | --- | --- |
| 1 — passed | Agent scheduled a short fixed-price sandbox billing period and observed provider orders, credits, signed webhooks, and website entitlement. | Paid `subscription_cycle` order `60cd3321-9a77-4818-890b-1245fc3bcfa2`; exactly 1,500 credits after the fifteen-minute billing delay, without rollover; website and provider agree. |
| 2 — passed | A real sandbox decline card caused a failed renewal; restoring the successful default card automatically retried the same order. | Past due denied launches without creating sessions/usage, removed VIP without removing guild membership, then recovered active access, exactly 1,500 credits, and the VIP role. A real post-fix 0.637-second session charged five credits once; provider and website ended at 1,495. |
| 3 | Owner confirms player networks and Discord accounts. Agent opens only the required test game access, checks profiles in the disposable database, and starts a casual server. | Both real clients reach the advertised address. Wrong password fails; correct password succeeds. Public discovery remains off. |
| 4 | Players join opposing alliances, send an identifiable test chat message, and play a scored game. Agent inspects API/events/logs and stops the server. | Player presence, chat, score and OPR agree with the clients; scopes protect actual player IP data; stop closes the process and debits once. |
| 5 | Both players use `/queuestandard`, selecting **Rebuilt 1v1**, in [the test queue channel](https://discord.com/channels/663201408581107712/1565227916432900126). | Bot creates private match resources, supplies a working server/password, and assigns the correct players. No production account creation or leaderboard writes. |
| 6 | Players play and submit actual red/blue scores with `/submit` in the match channel; continue until the bot reports the series complete. | Staging match rows and ELO history match submitted scores; channels/roles and game process are cleaned up after the series. Respect the command's two-minute cooldown. |
| 7 | Agent coordinates a fresh test match for idle timeout, then a separate restart/network-disruption check. Players follow the requested join/leave steps. | Idle/restart cleanup removes stale Discord resources and game processes; a transient network failure does not erase a live match; a new match can start afterward. |
| 8 — passed | Agent used the supplied `ssh namecheap` alias to take a consistent read-only SQLite snapshot and migrate a disposable local copy on October 30. | All modeled columns present; zero foreign-key violations; existing data preserved exactly across 22 application tables; original snapshot unchanged. Production was not migrated. |
| 9 | Agent reconciles evidence, fixes findings, runs relevant checks, and updates the three draft PRs. | Every required gate has recorded evidence or a specific unresolved blocker. Merge and production cutover remain a separate owner decision. |

## Inputs still needed

- Both players are confirmed on the current network, which matches the prepared
  game firewall rules. Confirm when they are ready with xRC v21.2 and Discord.
- The second player's Discord ID if they are not the existing `easierthanpai`
  test-guild member. Any profile seeded for ranked acceptance is a test fixture;
  it does not count as an additional OAuth login test.
- Production SSH access and the fresh-backup rehearsal are complete. The live
  application's Python 3.9 → 3.12 switch remains a cutover prerequisite; it has
  not been performed.
- Polar billing acceptance is complete. The successful `4242` card is restored
  as default, the subscription is active, and both balances are 1,495 after the
  verified five-credit usage debit. Keep credentials and codes out of chat.

Temporary UFW rules now permit game TCP/UDP ports 11115–11117 from the current
SSH client address only, in addition to the existing SSH and Nginx rules. The
private `acceptance-firewall.json` cleanup record is under the test root. A second
player on a different network needs a separate source rule. A real Rebuilt 1v1
preflight reached running on port 11115, listened on both TCP and UDP, kept public
discovery off, and accepted a stop request. Actual client reachability remains to
be tested.
Use the current matching xRC client revision; the installed test server is v21.2b.
Connection ports and passwords come from the actual session, not this document.
