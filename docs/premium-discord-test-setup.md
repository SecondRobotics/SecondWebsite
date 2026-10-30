# Isolated Polar Discord benefit acceptance

**Status: complete.** Merchant authorization and both customer connections are complete. Real role changes were verified through Discord's member API, not inferred from Polar statuses or manually assigned.

## Final configuration

- Polar organization: SecondRobotics **sandbox**, `c8c9219f-b5eb-42cb-9c75-2d4445de23ad`.
- Test guild: Nick's Test Server, `663201408581107712`.
- Test customer Discord account: `261976608519225345`.
- Polar Sandbox bot: `1285600567409901569`.
- Polar managed role: `1565531587368722462`, positioned above both premium roles.
- Both premium roles have permission bitfield `0`; both benefits use `kick_member=false`.

| Tier | Role ID | Benefit ID | Private sandbox product |
| --- | --- | --- | --- |
| Supporter | `1565530199838294038` | `d1e7f83d-a107-41d1-ab09-5b7a050a1f2e` | `4a900d30-03fb-45cb-a0c4-9053f964d966` |
| VIP Supporter | `1565530201893380126` | `1bfbd1df-3201-4ed0-868f-992dd9ed4295` | `794d2bb8-5f3b-4868-975a-fb7c181d8a70` |

Each product retains its original meter-credit benefit. The VIP product's final benefits are exactly `e16f5f1e-b7fe-4e6b-ade7-e56c338de4cd` (credits) and `1bfbd1df-3201-4ed0-868f-992dd9ed4295` (VIP role). Its temporary Supporter benefit has been removed.

## Verified behavior

1. Customer connected VIP in the sandbox portal; Polar granted the actual VIP Discord role.
2. Removing the VIP benefit from the private product removed the actual role, without removing guild membership.
3. Reattaching the VIP benefit restored the actual role.
4. The Supporter benefit separately required customer Discord connection. It was temporarily exposed on the private VIP purchase for this test.
5. After connection, Polar granted the actual Supporter role while VIP remained.
6. Removing only that temporary benefit removed Supporter and retained VIP. The final account has VIP only.
7. The website and Polar both retained 1,500 credits throughout the final role cleanup.

The active restored VIP subscription is `8889315a-38ce-40ee-aa7b-b7c2cd09cde2`. VIP grant: `c9c0cebc-e752-4c90-8d27-d9086a899d64`; Supporter test grant: `704f5e83-76c9-452a-8558-12d57c9cf8b9`.

The old benefit `887e581d-f3ca-490c-9a84-cff33751d53b` targets main guild `637407041048281098` and was not edited. No original product, main-guild role, production billing resource, merge, or deployment was changed.

## Repeating the setup

The CLI creates benefits and attaches them to products. The initial server connection requires Discord authorization through the [sandbox benefits page](https://sandbox.polar.sh/dashboard/secondrobotics/products/benefits). Customer connections are completed separately for each benefit in the [sandbox portal](https://sandbox.polar.sh/secondrobotics/portal), using the checkout email alias containing `+premium-acceptance-20261029`.

Official setup guide: https://polar.sh/docs/features/benefits/discord-access
