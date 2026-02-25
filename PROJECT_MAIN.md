# Aurex Esports Platform — Complete Project Journey

**Written:** February 2026  
**Covers:** Every session, decision, bug, architectural pivot, and lesson learned from day one to final deployment-ready state.

---

## TABLE OF CONTENTS

1. [How It Started](#1-how-it-started)
2. [What Was Originally Planned](#2-what-was-originally-planned)
3. [Backend Architecture Plan (Session 1)](#3-backend-architecture-plan-session-1)
4. [First Round of Critical Bugs (Session 2)](#4-first-round-of-critical-bugs-session-2)
5. [Frontend–Backend Integration (Sessions 3–5)](#5-frontendbackend-integration-sessions-35)
6. [The Verification Pass — What the README Got Wrong (Sessions 6–7)](#6-the-verification-pass--what-the-readme-got-wrong-sessions-67)
7. [Frontend Fixes — The Four Remaining Tasks (Session 8)](#7-frontend-fixes--the-four-remaining-tasks-session-8)
8. [Navbar Crisis and the Aurex Rebrand (Session 9)](#8-navbar-crisis-and-the-aurex-rebrand-session-9)
9. [Avatar in Sidebar (Session 10)](#9-avatar-in-sidebar-session-10)
10. [The Withdrawal Strategy Discussion](#10-the-withdrawal-strategy-discussion)
11. [The Closed Economy Audit (Session 11)](#11-the-closed-economy-audit-session-11)
12. [Coin Packages System (Session 12)](#12-coin-packages-system-session-12)
13. [All Bugs Fixed — Complete List](#13-all-bugs-fixed--complete-list)
14. [Architecture Decisions and Why](#14-architecture-decisions-and-why)
15. [What Went Wrong and Why](#15-what-went-wrong-and-why)
16. [Best Practices Established](#16-best-practices-established)
17. [Security Model](#17-security-model)
18. [Final System State](#18-final-system-state)

---

## 1. How It Started

The project began as a learning exercise. The developer (Ayush) had spent several weeks learning FastAPI properly and wanted to build a real, production-grade backend for a Free Fire esports tournament platform.

The frontend already existed — it had been generated from a large GPT prompt requesting an "Angular 18 enterprise-grade esports frontend inspired by Gamesmash-style UI." That frontend was functional in terms of structure but was built with mocked API calls and no real backend behind it.

The goal from day one was:
- Analyze the existing Angular frontend
- Design a FastAPI + PostgreSQL backend that matches what the frontend expects
- Connect them properly
- Build something that could actually run in production

The original platform name was **Firesports** / **FireEsports**. It was renamed to **Aurex** later in the project.

---

## 2. What Was Originally Planned

### What the frontend originally expected

The Angular frontend was built with these assumptions:
- Login would be a 2-step OTP flow (email + password → OTP → tokens)
- A wallet with coin balance displayed in the navbar
- Tournament leagues with rooms inside them
- Room join with Free Fire player ID
- Real-time room status via WebSocket
- Razorpay coin purchases
- A full admin panel at `/admin`
- Leaderboards (global and per-league)
- Match history

### What was planned for the wallet (original)

Early in the project, there was serious discussion about building a real-money withdrawal system:
- `deposit_balance` — coins from purchases
- `winning_balance` — coins from match prizes
- `locked_balance` — coins held during active room participation
- A withdrawal request table
- RazorpayX payout integration
- TDS (Tax Deducted at Source) calculation at 30% on net winnings
- GST handling at 28% on deposits
- KYC requirements for withdrawals
- Liquidity reserve planning

This was the original plan before a strategic pivot (covered in section 10).

### Tech stack decisions made at the start

| Layer | Choice | Reason |
|---|---|---|
| Framework | FastAPI | Developer had learned it properly over several weeks |
| Database | PostgreSQL + SQLAlchemy 2.0 | Production-grade, developer familiar |
| Migrations | Alembic | Proper schema versioning |
| Auth | JWT via PyJWT | Standard, well-documented |
| OTP delivery | Gmail SMTP via fastapi-mail | Simple, free, sufficient |
| Payments | Razorpay | India-specific, UPI support |
| Real-time | Native FastAPI WebSockets | No external dependency needed |
| Avatar storage | Cloudinary | Free tier, simple SDK |
| Rate limiting | slowapi | FastAPI-compatible, minimal config |
| Password hashing | passlib + bcrypt | Industry standard |
| Frontend state | NgRx | Already in place from the frontend |

One critical decision made at the start: **use PyJWT, not python-jose**. python-jose had CVE-2024-33664 published and was also unmaintained. This was verified against live documentation before making the call.

---

## 3. Backend Architecture Plan (Session 1)

**Date:** February 19, 2026  
**Transcript:** `2026-02-19-10-24-24-freefire-backend-build-plan.txt`

The first session was entirely planning — no code written yet. The developer's FastAPI learning materials were read carefully to understand exactly what he already knew, so the plan wouldn't teach things he already understood or use patterns he hadn't learned.

### Database schema designed

Nine tables planned:

```
users           — core user accounts with Free Fire ID, rank, avatar_url
leagues         — permanent tournament tiers (silver/gold/diamond/br)
rooms           — individual match sessions inside leagues
room_players    — join table: which players are in which room
wallets         — one wallet per user (at this point planned with locked/winning split)
transactions    — complete ledger of all coin movements
matches         — historical match results with kills/position/coins_won
otp_records     — OTP codes with expiry and purpose
audit_logs      — admin action trail
```

### Key architectural decisions in session 1

**OTP as background task:** The OTP sending was explicitly designed to use FastAPI's `BackgroundTasks` so the register endpoint responds immediately without waiting for email delivery. This is the correct pattern and was right from the start.

**SELECT FOR UPDATE on wallet operations:** Every coin credit/debit was designed to use `SELECT FOR UPDATE` to lock the wallet row and prevent race conditions. This was designed before a single line of code was written.

**Atomic settlement:** Match settlement was designed as a pre-validation-then-write pattern — validate all players first, then write all results, then commit. This ensures you either settle everyone or no one.

**Two-step register, one-step login:** Register was designed as 2-step (create account → verify OTP → receive tokens). Login was designed as 1-step (credentials → tokens immediately, no OTP). This distinction caused bugs later when the frontend mixed them up.

---

## 4. First Round of Critical Bugs (Session 2)

**Date:** February 19, 2026  
**Transcript:** `2026-02-19-10-41-18-backend-bug-fixes-deployment.txt`

The backend was built and immediately hit a wall of bugs when trying to run it. These were the first batch.

### Bug 1: SQLAlchemy 2.0 `.bind` removal

**What happened:** Code used `db.bind` which was removed in SQLAlchemy 2.0. The backend crashed on startup.

**Fix:** Removed `.bind` references, used the connection directly through the session.

**Lesson:** SQLAlchemy 2.0 was a breaking change from 1.x. The ORM query style changed significantly. Always check which version you're targeting before writing any model code.

### Bug 2: Dummy bcrypt hash

**What happened:** During development, a placeholder `hashed_password = "dummy"` was left in a test path. When a real login was attempted, `bcrypt.verify()` threw a `ValueError` because "dummy" is not a valid bcrypt hash string.

**Fix:** Removed all dummy hash placeholders. Every password is always properly hashed with `passlib`.

**Lesson:** Never leave placeholder values in authentication code paths, even in development.

### Bug 3: asyncio.create_task from sync context

**What happened:** `asyncio.create_task()` was called inside a synchronous FastAPI route function. This threw a `RuntimeError: no running event loop`.

**Fix:** Used FastAPI's `BackgroundTasks` parameter instead. This is the correct FastAPI pattern — background work that needs to happen after a response is returned.

**Lesson:** FastAPI route functions that don't use `async def` run in a thread pool, not the event loop. You cannot call asyncio directly from them.

### Bug 4: Partial commits in settlement

**What happened:** The match settlement endpoint was doing one `db.commit()` per player inside a loop. If player 3 of 10 failed, players 1 and 2 already had their coins credited and those commits could not be rolled back.

**Fix:** Moved to the pre-validation pattern: validate all players in one pass, make all writes, then commit once at the end. If anything fails, the entire transaction rolls back.

**Lesson:** Never commit inside a loop in settlement logic. Database transactions exist for exactly this reason.

### Bug 5: psycopg2 vs psycopg2-binary

**What happened:** requirements.txt had `psycopg2` but the Dockerfile was not set up to compile it (requires libpq-dev, python3-dev). Build failed.

**Fix:** Standardized on `psycopg2-binary` for consistency across local and Docker environments.

### Bugs 6-8: Alembic configuration on Windows

Three separate Alembic bugs, all Windows-specific:

- **`timezone = UTC` in alembic.ini** caused `ZoneInfo("")` error on Windows because it tried to parse an empty string
- **`version_locations =` in alembic.ini** caused "Multiple version locations found" error
- **`tzdata` missing** — `ZoneInfo("UTC")` fails on Windows without the `tzdata` package because Windows doesn't ship IANA timezone data

**Lesson:** Alembic's default configuration has options that work fine on Linux but break on Windows. Always test migrations on the actual target OS during development.

---

## 5. Frontend–Backend Integration (Sessions 3–5)

**Dates:** February 22–23, 2026  
**Transcripts:** Sessions 3 through 7 in the journal

These sessions were about connecting the Angular frontend to the FastAPI backend. This is where the majority of integration bugs were discovered.

### The fundamental integration problem

The frontend was built with mocked API calls. The shapes of the mock responses didn't always match what the real backend returned. Additionally, the frontend used camelCase throughout while FastAPI returns snake_case.

A systematic mapping layer was built in every Angular service:

```typescript
// Every service converts snake_case API responses to camelCase models
private mapApiUser(u: ApiUser): User {
  return {
    id: u.id,
    username: u.username,
    freeFireId: u.free_fire_id,      // snake → camel
    avatarUrl: u.avatar_url,          // snake → camel
    isAdmin: u.is_admin,              // snake → camel
    // etc.
  };
}
```

This pattern was applied to every service: auth, wallet, league, leaderboard, match.

### Bug 9: Login treated as 2-step

**What happened:** The frontend's auth effects were dispatching a "login OTP" action after receiving the login response, waiting for a second OTP step that would never come. The backend's `POST /auth/login` returns tokens immediately.

**Fix:** Login effect rewritten as single-step. Credentials go in → tokens come back → user is stored → navigation happens. No OTP involved.

**Why this happened:** The frontend was originally built expecting everything to be OTP-gated. The backend was designed with login as 1-step for user experience reasons (nobody wants OTP every login).

### Bug 10: Wrong API URL for /users/me

**What happened:** Multiple frontend services were calling `/auth/me` to get the current user's profile. The backend endpoint is `/users/me`.

**Fix:** Updated all calls across all services.

**How many endpoints had wrong URLs:** Ten total. `/auth/me`, `/matches/me`, `/wallet/me` — all prefixed with wrong router names. And `GET /rooms?league_id=` which the backend doesn't support; the correct path is `GET /leagues/{id}/rooms`.

**Lesson:** Mock API calls don't enforce URL correctness. Always verify every endpoint URL against the actual router before shipping integration code.

### The Razorpay integration

The payment flow was integrated correctly from the start:

1. User clicks Buy → frontend dispatches `initiatePayment`
2. Effect calls `POST /wallet/payment/initiate` → backend creates Razorpay order, returns order ID
3. Frontend opens Razorpay modal with the order ID
4. User pays → Razorpay calls the `handler` callback
5. Frontend dispatches `verifyPayment` with the three Razorpay fields
6. Backend verifies HMAC signature → credits coins → returns success
7. Frontend dispatches `reloadWallet` → balance updates

Critical security point established here: **the HMAC verification in step 6 is non-negotiable**. Without it, anyone can send fake payment data and get coins for free.

### The WebSocket integration

WebSocket was integrated as a native browser WebSocket (not Socket.io, not a library). The connection URL is:

```
ws://localhost:8000/ws/rooms/{room_id}?token=<access_token>
```

The token goes in the query parameter because WebSocket browser API doesn't support custom headers. The backend validates the JWT from the query parameter on connection.

---

## 6. The Verification Pass — What the README Got Wrong (Sessions 6–7)

**Dates:** February 24, 2026  
**Transcripts:** `freefire-readme-verification-fixes.txt`, `readme-verification-corrections.txt`

At this point a README had been written documenting the project. A verification pass was done — comparing every claim in the README against the actual code. Eight critical errors were found.

### What the README claimed vs. what the code actually did

| Claim in README | Reality |
|---|---|
| Login sends `username` field | Backend uses `email` field in JSON |
| Login is form-encoded | Backend uses `application/json` |
| reset-password takes `{email, otp, new_password}` | Backend requires `confirm_password` too |
| Admin settlement at `/admin/rooms/{id}/settle` | Actual path: `/admin/matches/{room_id}/settle` |
| Register min password length: 6 | Backend enforces 8 |
| Register min age: 16 | Backend enforces 13 |
| Auth flow described as 1-step register | Register is 2-step (create → OTP → tokens) |
| Ban reason in request body | Reason is a query parameter: `?reason=...` |

**How these errors happened:** Documentation was written from memory of the design plan, not from reading the actual backend code. The plan changed during implementation but the README wasn't updated simultaneously.

**Fix applied:** Every endpoint documented in the README was verified by reading the actual router file. New documentation policy established: never document from memory, always read the source.

### Bug 11: register.component.ts password validator

**What happened:** Frontend register form had `Validators.minLength(6)` for password. Backend enforces minimum 8 characters. Users could submit a 6-character password, pass frontend validation, and get a 422 from the backend.

**Fix:** `Validators.minLength(8)` in the form.

### Bug 12: resetPassword() missing confirm_password

**What happened:** `auth.service.ts` was calling `POST /auth/reset-password` without the `confirm_password` field. Backend's Pydantic schema requires it and validates both fields match.

**Fix:** Updated `resetPassword()` to send `confirm_password: newPassword`. Frontend validates equality before dispatching, so `newPassword` is sent for both fields.

### Bug 13: empty freeFireId in room join

**What happened:** `room.component.ts` was constructing the join payload without checking if `freeFireId` was set. If a user hadn't filled in their Free Fire ID in their profile, an empty string was sent to `POST /rooms/{id}/join`. Backend validates this field as non-empty and returns 422.

**Fix:** Added a guard in the room component — if `freeFireId` is empty/null, navigate to profile page with a message instead of attempting the join.

---

## 7. Frontend Fixes — The Four Remaining Tasks (Session 8)

**Date:** February 25, 2026  
**Transcript:** `task-completion-league-fix.txt`

After the verification pass, four tasks remained in the project documentation as unfinished. All four were completed in this session.

### Task 1: Leaderboard UUID mapping

**Problem:** `leaderboard.component.ts` was dispatching league leaderboard requests using tier strings like `"silver"`, `"gold"`, `"diamond"`. The backend endpoint is `GET /leaderboard/league/{id}` where `{id}` is a UUID, not a tier string.

**Fix:** The component now reads the loaded leagues from the NgRx store, finds the league whose `tier` property matches, and uses that league's UUID for the leaderboard request.

```typescript
// Wrong (what it was):
this.store.dispatch(loadLeagueLeaderboard({ leagueId: 'silver' }));

// Right (what it became):
const league = leagues.find(l => l.tier === 'silver');
this.store.dispatch(loadLeagueLeaderboard({ leagueId: league.id }));
```

### Task 2: League component title logic

**Problem:** `league.component.ts` was checking `if (leagueId === 'br')` to show a Battle Royale-specific heading. `leagueId` is a UUID — this comparison never matched.

**Fix:** Fetch the league by UUID via `GET /leagues/{id}`, then use `league.tier === 'br'` for the conditional.

### Task 3: Admin auto-bootstrap bug

**Problem:** `admin.component.ts` had a `bootstrapDefaultLeagues()` function that automatically called `POST /admin/leagues` to create default leagues whenever the admin panel loaded and found 0 leagues. This was causing leagues to appear on the home page even when the admin had never manually created anything.

Additionally, "Platinum" was used as a tier in the default bootstrap — but the backend only accepts `silver`, `gold`, `diamond`, `br`. So the Platinum creation failed silently while Gold and Diamond were created.

**Fix:** Removed the auto-bootstrap function entirely. Leagues must be created manually by the admin via the League Management section.

**Why this matters:** Auto-seeding production data from a UI event is never correct architecture. Configuration data should be seeded via migrations or explicit admin action, not by side effects of page loads.

### Task 4: onVerify() missing take(1)

**Problem:** The OTP verification observable subscription in the register component was not using `take(1)`. If the stream emitted multiple times, multiple dispatches would fire.

**Fix:** Added `take(1)` to the subscription.

---

## 8. Navbar Crisis and the Aurex Rebrand (Session 9)

**Date:** February 25, 2026  
**Transcript:** `navbar-mobile-fix-aurex-rebrand.txt`

This was the largest single-session change to the frontend.

### The core problem: mat-toolbar clips overlays

The navbar was built using Angular Material's `<mat-toolbar>`. The sidebar (slide-in menu) and coin shop (dropdown panel) were placed as children of `<mat-toolbar>` inside the component template.

**What went wrong:** `mat-toolbar` applies `overflow: hidden` to its host element. Any absolutely or fixed-positioned child element that tries to render outside the toolbar's bounding box is clipped and becomes invisible or unusable. This is why the sidebar appeared broken — it was rendered but immediately clipped.

**The fix:** Remove `mat-toolbar` entirely. Use a plain `<nav>` element. The overlay `<div>`s (sidebar and coin shop) must be **siblings of `<nav>`**, not children of it. This is the only pattern that works correctly.

```html
<!-- WRONG — overlays clipped by mat-toolbar -->
<mat-toolbar>
  <nav>...</nav>
  <div class="sidebar">...</div>  <!-- clipped! -->
</mat-toolbar>

<!-- RIGHT — overlays are siblings of nav -->
<div class="navbar-host">
  <nav>...</nav>
  <div class="sidebar">...</div>   <!-- not clipped -->
  <div class="coin-shop">...</div> <!-- not clipped -->
</div>
```

### The Aurex rebrand

The platform was renamed from Firesports/FireEsports to **Aurex**. Every occurrence of the old name was replaced across all `.ts` files and `index.html`. The browser tab title became "Aurex | Fantasy Esports".

New logo: `src/assets/navbar/Aurex-Esports.jpg` (63KB JPG, rendered 36×36px in navbar).

### New navbar layout

Before (broken):
- Profile button in the top bar
- No consistent hamburger pattern
- Overlays broken on mobile

After (working):
```
[ Aurex JPG logo ] [ 🪙 4,980 + ] [ AUREX text→home ]          [ ☰ ]
```

Everything that was in the top bar moved into the sidebar:
- Profile → sidebar
- Admin Panel → sidebar
- Leaderboard → sidebar
- History → sidebar
- Wallet → sidebar
- Login/Logout → sidebar

### Mobile breakpoints

- ≤600px: navbar height 58px, logo 32×32px, compact coins pill, 2-column coin shop
- ≤380px: "AUREX" text hidden — only logo + coins pill + hamburger remain

---

## 9. Avatar in Sidebar (Session 10)

**Date:** February 25, 2026  
**Transcript:** `avatar-sidebar-readme-delivery.txt`

### The feature

Users can upload an avatar via the Profile page. The image is stored in Cloudinary. The URL is saved in `users.avatar_url`. The sidebar previously showed a generic user icon for everyone.

### The implementation

The sidebar already had access to `currentUser$ | async` from the NgRx auth store. The fix was conditional rendering:

```html
<div class="avatar-circle">
  <img *ngIf="user.avatarUrl" [src]="user.avatarUrl" [alt]="user.username" class="avatar-img" />
  <lucide-icon *ngIf="!user.avatarUrl" name="user" class="icon-md"></lucide-icon>
</div>
```

The `profile.component.ts` already dispatched `updateUserInStore({ user: { ...user, avatarUrl: res.avatar_url } })` after a successful upload. Because the sidebar reads directly from the NgRx store via an Observable, the avatar updates instantly without a page refresh.

### CSS requirement

The container needs `overflow: hidden` and the image needs `border-radius: 50%` + `object-fit: cover` to clip properly to a circle:

```css
.avatar-circle { overflow: hidden; border-radius: 50%; }
.avatar-img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; display: block; }
```

---

## 10. The Withdrawal Strategy Discussion

Before the closed-economy audit session, a separate strategic discussion took place (with GPT) about the business and legal direction of the platform.

### What was proposed

The developer had originally considered building a real-money withdrawal system:
- Split wallet: deposit coins vs. winning coins
- Withdrawal requests table
- TDS deduction at 30% on net winnings
- GST at 28% on deposits
- KYC requirements for payouts
- RazorpayX payout integration
- Liquidity reserve planning

### What the discussion revealed

The conversation exposed several layers of complexity that had not been fully considered:

**Tax complexity:** TDS applies to net winnings, not gross withdrawal amounts. If a user deposited ₹1000 and withdrew ₹900, net winnings = -₹100, so TDS = ₹0. Blindly deducting 30% from the withdrawal amount would be illegal overcharging.

**Liquidity risk:** If 1000 users each accumulate ₹2000 in winning balance, the platform owes ₹20 lakhs. Without proper reserve management, this becomes a platform insolvency risk.

**Legal uncertainty:** PROGA 2025 (Public Gaming Regulation) created regulatory tightening around online money games. Platforms accepting deposits and paying cash returns face high scrutiny. Supreme Court clarity was still pending.

**AML/KYC burden:** Any real-money payout system requires identity verification, which adds significant operational complexity and cost.

### The decision: Closed Coin Economy

After the full analysis, the decision was made to **never build withdrawals**. Aurex is positioned as:

> A competitive esports tournament platform using in-platform credits only — not a real-money gaming operator.

The business model:
```
10 players × 100 coins entry = 1,000 coins collected
900 coins distributed as prizes (90% prize pool)
100 coins retained as platform fee (10% house cut)
Coins never leave the system.
```

Consequences of this decision:
- No TDS calculation required
- No KYC/AML burden
- No liquidity risk
- No RazorpayX needed
- Legal exposure reduced significantly
- Multi-game expansion (BGMI, COD) becomes much simpler

**Strategic note:** The withdrawal system was never actually built. The discussion prevented it from being built. The codebase was already a closed economy by the time this strategic review happened — the review was confirming an already-correct state, not triggering a redesign.

---

## 11. The Closed Economy Audit (Session 11)

**Date:** February 25, 2026

After the strategic discussion, a full audit was done to verify what the strategy document said needed removing actually existed in the codebase or not.

### Audit findings

| Strategy says to remove | Actually exists? |
|---|---|
| Withdrawal endpoints | Never existed |
| winning_balance column | Never existed |
| deposit_balance column | Never existed |
| RazorpayX payout integration | Never existed |
| TDS calculation logic | Never existed |
| Withdrawal request table | Never existed |
| KYC for payouts | Never existed |
| Payout background tasks | Never existed |
| Split wallet display | Never existed |

**Conclusion:** The withdrawal system described in the strategy conversation was a proposed design that was never implemented. The codebase was already a closed economy.

### What DID need changing

Three real issues were found:

**1. locked_balance — dead column**

`locked_balance` existed in the `wallets` table and was referenced in availability checks:
```python
available = wallet.balance - wallet.locked_balance
```

But `locked_balance` was **never written to** anywhere in the codebase. It was always 0. The check was functionally `balance - 0`. It gave a false sense of concurrency safety while doing nothing.

Decision: Remove it. Write an Alembic migration. Simplify the check to:
```python
if wallet.balance < amount:
    raise InsufficientCoinsException(...)
```

**2. Coin package inconsistency**

The wallet page had hardcoded packages: `50/₹49`, `120/₹99`, `300/₹199`.
The navbar coin shop had different hardcoded packages: `100/₹80`, `310/₹250`, `520/₹400`, etc.
Two different price lists in the same app.

Decision: Remove all hardcoding. Create a `coin_packages` database table. Serve packages via `GET /coin-packages`. Frontend fetches from API.

**3. Missing "closed economy" disclaimer**

The strategy required this user-facing text:
> "Coins are for in-platform tournament participation only and cannot be withdrawn as real money."

This text did not exist anywhere in the UI.

Decision: Add it to the wallet page as a visible notice.

---

## 12. Coin Packages System (Session 12)

**Date:** February 25, 2026

### What was built

**Backend:**
- `models/coin_package.py` — `CoinPackage` SQLAlchemy model with: `id`, `coins`, `price_inr`, `is_active`, `is_popular`, `sort_order`, `created_at`
- `schemas/coin_package.py` — `CoinPackageOut` (public), `CoinPackageAdminOut`, `CoinPackageCreateRequest`, `CoinPackageUpdateRequest`
- `routers/coin_packages.py` — `GET /coin-packages` (public, no auth)
- `routers/admin.py` — CRUD endpoints under `/admin/coin-packages`
- Alembic migration `20260226_0002_b2c3d4e5f6a7` — creates table, seeds 6 default packages

**Frontend:**
- `core/models/coin-package.model.ts` — `CoinPackage` and `ApiCoinPackage` interfaces
- `core/services/coin-packages.service.ts` — `getPackages()` → maps snake_case to camelCase
- `wallet.component.ts` — fetches packages on init, uses `packageId` to dispatch
- `navbar.component.ts` — fetches packages on init for coin shop modal

### The critical security rule

`POST /wallet/payment/initiate` was changed to accept only `{package_id: uuid}` instead of `{amount_inr, coins}`.

**Why this matters:** If the frontend sent the amount, a user could intercept the HTTP request and change `amount_inr` from 4000 to 1 while keeping `coins: 5600`. They'd get 5600 coins for ₹1.

With the new design:
1. Frontend sends only `{package_id: "some-uuid"}`
2. Backend looks up the package in the DB
3. Backend uses `package.price_inr` and `package.coins` — never trusts frontend values
4. Razorpay order is created with the DB price

**This is tamper-proof by design.** The frontend has no way to influence the price.

### The TypeScript bug found during this session

`activePkg` in `navbar.component.ts` was declared as `string` (`activePkg = ''`) but was being reset to `0` (a number) in two places:

```typescript
// Bug
this.activePkg = 0;  // type error — activePkg is string

// Fix
this.activePkg = '';  // correct
```

This would have caused `ng build` to fail with a TypeScript error.

---

## 13. All Bugs Fixed — Complete List

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 1 | `db.bind` removed in SQLAlchemy 2.0 | API change | Removed `.bind` references |
| 2 | Dummy bcrypt hash crashed login | Placeholder left in code | Removed all dummy values |
| 3 | asyncio.create_task from sync context | Event loop not available in thread pool | Switched to BackgroundTasks |
| 4 | Partial commits in settlement | db.commit() inside loop | Pre-validate all, write all, commit once |
| 5 | psycopg2 build failure in Docker | Missing native deps | Used psycopg2-binary |
| 6 | `timezone = UTC` in alembic.ini | ZoneInfo("") parse error on Windows | Commented out timezone setting |
| 7 | `version_locations =` in alembic.ini | Alembic misinterprets blank value | Removed the line |
| 8 | ZoneInfo("UTC") on Windows | tzdata not installed | Added tzdata to requirements.txt |
| 9 | Login treated as 2-step OTP flow | Frontend assumed same flow as register | Rewrote login effect as single-step |
| 10 | Wrong API URLs (10 endpoints) | Documentation written from memory | Verified every URL against actual routers |
| 11 | reset-password missing confirm_password | Schema requirement not known | Added confirm_password field |
| 12 | Register password min 6 | Frontend validator didn't match backend | Changed to minLength(8) |
| 13 | Register age min 16 | Frontend validator didn't match backend | Changed to min(13) |
| 14 | onVerify() missing take(1) | Observable subscription not terminated | Added take(1) |
| 15 | Leaderboard used tier strings | Backend expects UUIDs | Map tier→UUID via leagues store |
| 16 | League title compared leagueId === 'br' | leagueId is always a UUID | Fetch league by UUID, use league.tier |
| 17 | Admin auto-bootstrapped leagues | Side effect on page load | Removed bootstrapDefaultLeagues() |
| 18 | Sidebar/overlays clipped by mat-toolbar | mat-toolbar applies overflow:hidden | Removed mat-toolbar, overlays are siblings |
| 19 | locked_balance never written to (always 0) | Column declared but unused | Removed with Alembic migration |
| 20 | activePkg: string reset to 0 (number) | TypeScript type mismatch | Changed reset value to '' |

---

## 14. Architecture Decisions and Why

### Why PyJWT instead of python-jose

python-jose had a published CVE (CVE-2024-33664) and was effectively unmaintained at the time of development. PyJWT is the actively maintained standard library. Checked against live documentation before making this call.

### Why Razorpay not Stripe

The user base is India. UPI is the dominant payment method. Razorpay supports UPI natively. Stripe requires significant setup for India and doesn't have the same level of UPI integration.

### Why native WebSocket not Socket.io

No external dependency needed. FastAPI's `WebSocket` class is sufficient for the room status update use case. Socket.io adds complexity (connection protocol, room abstractions, event system) that isn't needed here.

### Why Cloudinary for avatars

Free tier is sufficient. The SDK is simple. The URL returned is a CDN-served image that works immediately. No S3 bucket configuration, no presigned URLs, no CDN setup.

### Why locked_balance was removed

It was never used. A column that is always 0 and is referenced in checks is worse than no column at all — it creates the illusion of safety without providing it. If a locking model is needed in the future (match cancellation, refund holds, delayed settlement), it should be implemented properly, not left as dead code.

### Why coin packages moved to the database

**Admin control without deployment:** Pricing can change without a frontend rebuild. The admin can add, remove, or reprice packages from the admin panel.

**Price tamper protection:** Backend owns the price. Frontend sends only a package UUID. The frontend cannot influence what Razorpay charges.

**Single source of truth:** Wallet page and navbar coin shop were using different hardcoded price lists. One DB table eliminates the inconsistency permanently.

### Why soft-delete for coin packages

Packages are never hard-deleted (`is_active = False` instead). A package UUID may appear in transaction history as a reference. Hard-deleting it would orphan those references and potentially break audit queries. Soft-delete keeps data integrity intact.

---

## 15. What Went Wrong and Why

### 1. Documentation written from memory, not from code

This was the most pervasive problem in the project. Multiple times, a README or plan document was written based on recollection of the design, not by reading the actual files. This produced documentation with wrong API URLs, wrong field names, wrong validation rules, and wrong auth flows.

**The correct discipline:** Before documenting any endpoint, open the router file and read it. Before documenting any frontend behavior, open the component and read it.

### 2. Frontend built in isolation from backend

The Angular frontend was generated from a prompt with mocked API calls. The mock responses didn't enforce URL correctness, field name accuracy, or flow correctness. When the real backend was connected, 10 URL mismatches and several field mismatches were discovered.

**The correct discipline:** Integration testing should happen as early as possible. Mock services should use the exact same URLs and field names as the real backend.

### 3. Auto-bootstrap as a side effect of page load

The admin component was auto-creating default leagues whenever the league list was empty. This caused data to appear in production without explicit admin action, created leagues with an invalid tier name ("Platinum"), and was just generally the wrong pattern.

**The correct discipline:** Data seeding belongs in Alembic migrations or explicit admin actions, never in UI event handlers.

### 4. mat-toolbar's overflow behavior was unexpected

Using Angular Material's `<mat-toolbar>` for the navbar seemed like the obvious choice. The overflow clipping behavior was not documented prominently and wasn't obvious until the sidebar started disappearing.

**The correct discipline:** When using a UI framework component for layout, verify what CSS properties it applies globally. `overflow: hidden` is a common source of clipping bugs with overlays.

### 5. Coin packages were hardcoded in two different places with different values

The wallet page and the navbar coin shop were both hardcoding package prices as TypeScript constants. They had completely different values. This would have confused users who saw different prices depending on where they looked.

**The correct discipline:** Any list of data items that might change belongs in a database, not in frontend source code.

### 6. The withdrawal design discussion was valuable even though nothing was built

The withdrawal system was extensively designed and never implemented. This might seem like wasted effort, but the discussion was valuable — it surfaced tax complexity (TDS on net winnings vs. gross), liquidity risk quantification, and legal exposure under PROGA 2025 before any of that complexity was written into the codebase. The conversation was a risk discovery process, not just a design exercise.

---

## 16. Best Practices Established

### Backend

**Always use SELECT FOR UPDATE on wallet operations**
```python
wallet = db.execute(
    select(Wallet).where(Wallet.user_id == user_id).with_for_update()
).scalar_one_or_none()
```
This locks the wallet row and prevents two concurrent requests from both reading the same balance, both passing the check, and both deducting — leaving the wallet negative.

**Never commit inside a settlement loop**
```python
# Wrong
for player in players:
    credit_coins(db, player.user_id, amount)
    db.commit()  # if this succeeds for player 3 but fails for player 4, partial state

# Right
for player in valid_players:
    # make all writes
    pass
db.commit()  # one commit at the end
```

**Always use BackgroundTasks for email**
```python
@router.post("/auth/register")
def register(background_tasks: BackgroundTasks, ...):
    # create user
    background_tasks.add_task(send_otp_email, email=user.email, otp=otp)
    return {"message": "OTP sent"}  # responds immediately
```

**Backend must own the price in payment flows**
```python
# Wrong — frontend sends amount
order = create_order(amount_inr=body.amount_inr, coins=body.coins)

# Right — backend fetches price from DB
package = db.query(CoinPackage).filter(
    CoinPackage.id == body.package_id, CoinPackage.is_active == True
).first()
order = create_order(amount_inr=package.price_inr, coins=package.coins)
```

**Soft-delete never hard-delete for financial reference data**
Any record that might be referenced by a transaction, audit log, or settlement should never be hard-deleted. Set `is_active = False` instead.

**Idempotency for payments**
```python
duplicate = db.query(Transaction).filter(
    Transaction.reference == body.razorpay_payment_id
).first()
if duplicate:
    return {"message": "Payment already processed."}
```
The Razorpay payment ID is unique. Storing it as the transaction reference prevents double-crediting if the verify endpoint is called twice.

### Frontend

**Read files before modifying**
Never assume what a file contains. Every component edit in this project started by reading the current state of the file.

**camelCase in Angular, snake_case from API**
All API response shapes have a corresponding `Api*` interface in snake_case. All internal models use camelCase. Every service has a mapping function. This pattern prevents confusion about which format is used where.

**Overlays must be siblings of nav, not children**
`overflow: hidden` on any container will clip overlays. Keep sidebars and dropdown panels at the same DOM level as the nav bar.

**Import shared constants, don't duplicate them**
`COIN_PACKAGES` was previously duplicated between wallet.component and navbar.component. Now there's one source (the API). Never copy-paste a list — reference the single source.

**Use take(1) on one-shot observable subscriptions**
Any subscription that should fire once (OTP verification, payment initiation) must use `take(1)` to prevent multiple dispatches.

---

## 17. Security Model

### Authentication

- JWT access tokens (30 minutes expiry)
- JWT refresh tokens (7 days expiry)
- Tokens stored in localStorage
- Every request authenticated via `Authorization: Bearer <token>` header injected by the HTTP interceptor
- `is_banned` checked on every authenticated request — banning takes effect immediately without waiting for token expiry

### Payment security

- **HMAC verification:** Every payment verify call checks the Razorpay signature before crediting any coins. No signature match = no coins.
- **Backend-owned pricing:** Frontend sends only a `package_id`. Backend fetches `price_inr` from the DB. Frontend cannot influence the charge amount.
- **Idempotency:** Razorpay payment ID stored as transaction reference. Duplicate payment IDs are rejected.
- **Rate limiting:** Payment initiate and verify endpoints are rate-limited to 10 per minute per user.

### Coin economy security

- **SELECT FOR UPDATE:** All balance operations lock the wallet row. Race conditions prevented.
- **Atomic settlement:** Match settlement validates all players, then writes all results in one transaction. Partial settlements are impossible.
- **No withdrawal path:** Coins cannot leave the system. There are no endpoints that move coins to real money.
- **Admin audit logs:** Every admin action is logged with the admin's user ID, the action type, the target, and a JSON details blob.

---

## 18. Final System State

### What exists and works

**Backend (FastAPI):**
- Full authentication system (register/verify/login/forgot-password/reset/refresh)
- User profiles with Cloudinary avatar upload
- League and room management
- Room join with coin deduction (atomic, race-condition safe)
- Room leave with conditional refund
- WebSocket real-time room updates
- Wallet with full transaction ledger
- Coin package system (DB-managed, admin-controlled)
- Razorpay payment flow (package-based, tamper-proof)
- Global and league-specific leaderboards
- Match history
- Full admin panel (leagues, rooms, users, wallet ops, match settlement, audit logs)
- Rate limiting on auth and payment endpoints

**Frontend (Angular 18):**
- Full auth flows (register/login/forgot-password)
- Navbar with logo, coins pill, brand text, hamburger
- Sidebar with all navigation items
- Avatar display in sidebar (Cloudinary URL or fallback icon)
- Coin shop modal (fetches packages from API, no hardcoded values)
- Wallet page with balance, closed-economy disclaimer, transaction history
- League browsing and room joining
- Real-time room status via WebSocket
- Leaderboards (global and per-league, UUID-mapped)
- Match history
- Profile page with avatar upload
- Admin panel with all management sections
- NgRx state management for auth, wallet, league, leaderboard

### Alembic migration chain

```
cfd62feace54  →  a1b2c3d4e5f6  →  b2c3d4e5f6a7
initial schema   remove             add
(all tables)     locked_balance     coin_packages
```

### To run the project

```bash
# Backend
cd Backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
# create .env with all required values
alembic upgrade head      # runs all 3 migrations, seeds coin packages
uvicorn app.main:app --reload --port 8000

# Frontend
cd Frontend
npm install && ng serve
```

### The one remaining step before production

`environment.prod.ts` does not exist. Create it before any production build:

```typescript
export const environment = {
  production: true,
  apiUrl: 'https://your-backend-domain.com',
};
```

---

*This document represents the complete history of the Aurex Esports Platform from its first planning session on February 19, 2026 to its deployment-ready state on February 26, 2026. Total development time: approximately one week across 12 sessions.*
