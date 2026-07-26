# MedicareManny Lead Vigilance — Runbook

_Last verified: 2026-07-26 (remote Claude Code session)_

Monitors inbound leads for **Meta Page `315272328346658`** (Instant Form lead ads)
and **TikTok `@medicaremanny`**, with Gmail as the signal bus.

## Current status

| Channel | Status | Notes |
|---|---|---|
| Gmail access (remote) | ✅ Working | Google Gmail MCP connector is authorized for `medicaremanny@gmail.com`; searches and labels verified. The remote environment does not use `gog` — the connector replaces it there. |
| `gog` CLI (local Mac) | ⚠️ Needs reauth | Must be reauthorized interactively on the Mac — cannot be done from a remote container. Run `gog auth login` (or `gog auth` to list subcommands) and complete the browser consent for `medicaremanny@gmail.com`. |
| Meta Instant Forms (direct) | ❌ Blocked | Graph API returns `OAuthException` without a valid app token; interactive login is blocked from the remote container. |
| Meta lead email notifications | ❌ Not flowing | Zero `facebookmail.com` emails in the last 90 days. Enable in **Meta Business Suite → Leads Center → notification settings** (email notifications for instant-form leads). |
| TikTok comments (direct) | ❌ Blocked | Comment endpoints return HTTP 403 to unauthenticated clients (profile page itself loads fine). |
| TikTok email notifications | ❌ Not flowing | Only security emails arrive (to `leonmannyl@gmail.com`). Enable in **TikTok app → Settings → Notifications → Email** for comments/messages. |

## Watchdog routine (active)

Routine **`medicaremanny-lead-vigilance`** (`trig_01KU2AT43yNCDEv3HX5qvPQx`) runs
**every 2 hours** and is bound to the remote session that holds the Gmail connector.
Each run:

1. Sweeps Gmail for new `facebookmail.com`, TikTok-notification, and "new lead /
   lead form / instant form" emails from the last 24 h.
2. Dedupes with the Gmail label `LeadVigilance-Processed`.
3. If Zapier "Facebook Lead Ads" / "TikTok Lead Generation" connections exist,
   pulls recent leads directly.
4. On new signals: sends a push notification and creates a Gmail draft alert with
   each lead's name/contact and thread link; otherwise stays silent.

Manage it at claude.ai → Routines (pause/edit/delete).

## One-time actions for Manny (restores the blocked channels)

1. **Reauthorize `gog` on the Mac** — `gog auth login`, pick `medicaremanny@gmail.com`.
2. **Connect Facebook Lead Ads to Zapier** (bypasses the blocked Graph API):
   <https://mcp.zapier.com/api/v1/connect-auth/FacebookLeadsCLIAPI?accountId=14705638>
3. **Connect TikTok Lead Generation to Zapier**:
   <https://mcp.zapier.com/api/v1/connect-auth/TikTokLeadGenerationCLIAPI?accountId=14705638>
4. **Turn Meta lead-email notifications back on** (Business Suite → Leads Center).
5. **Turn TikTok email notifications on** for comments/DMs.

Once 2–3 are connected, the routine picks them up automatically — no prompt change
needed. Items 4–5 make the Gmail sweep light up even without Zapier.
