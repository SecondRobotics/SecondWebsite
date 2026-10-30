# Isolated Polar Discord benefit setup

Most setup is automated. The official Polar CLI can create Discord benefits and attach them to products, but creation currently fails with: `properties.guild_id: This organization has not connected this Discord server. Please connect it again.`

## Required owner authorization

1. Open https://sandbox.polar.sh/dashboard/secondrobotics/products/benefits in the **SecondRobotics sandbox** organization (ID `c8c9219f-b5eb-42cb-9c75-2d4445de23ad`). Do not use the separate SecondRoboticsSandbox organization.
2. Start adding a **Discord** benefit, then choose **Connect your Discord server**.
3. In Discord's authorization screen select **Nick's Test Server**, guild `663201408581107712`.
4. Authorize Polar's own Discord app. Polar's documentation lists Manage Roles, Kick Members, and Create Invite as required permissions. This adds Polar's role integration; the existing ranked test bot cannot substitute for it. No new developer application, client secret, or bot token needs to be created by Nick.
5. Return to Polar after authorization. Tell Codex the server is connected; Codex can create/attach the benefits through the CLI. If a role choice is required to finish the dialog, choose the Supporter role below and leave **kick member** disabled.

Official guide: https://polar.sh/docs/features/benefits/discord-access

## Prepared roles and products

Both roles exist already and have permission bitfield `0`; neither has been assigned to users.

| Tier | Discord role | Role ID | Private sandbox product |
| --- | --- | --- | --- |
| Supporter | Premium Acceptance Supporter | `1565530199838294038` | `4a900d30-03fb-45cb-a0c4-9053f964d966` |
| VIP Supporter | Premium Acceptance VIP | `1565530201893380126` | `794d2bb8-5f3b-4868-975a-fb7c181d8a70` |

After authorization, Codex should verify the role hierarchy, create distinct benefits with `kick_member=false`, and attach each to its matching acceptance product while preserving the existing meter-credit benefit. Customer Discord connection/grant/revocation testing follows after this merchant-side connection.

The old benefit `887e581d-f3ca-490c-9a84-cff33751d53b` targets main guild `637407041048281098`; do not edit or reuse it for this test.
