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

## Monitoring record — 2026-07-26 through 2026-07-30

The watchdog ran every 2 hours across this window. **Every sweep returned zero
signals**: no `facebookmail.com` mail, no TikTok notification mail, no
"new lead / lead form / instant form" subjects, and no GUÍA/GUIDE mentions from
any social sender. The Zapier Facebook Lead Ads and TikTok Lead Generation
connections were re-checked several times and remained unlinked throughout.

**Read this as an instrumentation result, not a demand result.** Every capture
path listed in the status table above is still off, so a lead could have arrived
via a Meta Instant Form or a TikTok comment and left no trace the watchdog could
see. Zero observed ≠ zero happened.

## Texas nonresident license — 2026-07-31 checkpoint

`marketing/tiktok/texas-license-timing-2026-aep.md` sets the decision rule:
activate Texas only if TikTok demand data justifies it by 2026-07-31, otherwise
hold and keep the 2026-08-01 → 08-15 application window as the fallback.

**Recommendation: do not buy Texas on this checkpoint.** The decision rule asks
for evidence of Texas demand, and no engagement data was captured at all — which
fails the rule on evidence, without proving demand is absent. Buying a
nonresident license plus carrier appointments and certifications on an unmeasured
hunch is the expensive error here; waiting is cheap and reversible, since the
doc's own timeline keeps Texas viable for AEP through mid-August.

**To reopen the decision before the window closes (2026-08-15):** turn on the
TikTok/Meta notification paths above, then give the watchdog ~10 days of real
comment data. If Texas mentions show up in that window, the Aug 1–15 application
slot is still open and the original timeline holds.
