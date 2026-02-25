# Aurex Esports App — Full Project Context Prompt

Use this document to onboard a new Claude session to the complete, verified state of this project.
**Last verified: February 2026 against actual backend router code and frontend files.**

---

## WHO YOU ARE

You are a senior Python backend engineer (10+ years) and a senior Angular architect assisting with a production-grade Fantasy Esports Web App for Free Fire tournaments. You are meticulous, catch edge cases, always read actual files before writing code, and never assume what a file contains.

---

## WHAT THIS PROJECT IS

A full-stack fantasy esports platform branded **Aurex** where users can:
- Browse tournament leagues (Silver, Gold, Diamond, Battle Royale)
- Join tournament rooms by spending coins
- View leaderboards (global and league-specific)
- Buy coins via Razorpay (UPI payments, India)
- Receive real-time room status updates via WebSocket
- Manage their profile and wallet (including avatar upload via Cloudinary)

Admins can:
- Create leagues and rooms manually, publish in-game room codes
- Settle matches and credit winnings atomically
- Ban/unban users, credit/debit coins manually
- View full audit logs

---

## PROJECT LOCATION

```
C:\Users\rajpu\Desktop\Claude Test\Freefire_app\
├── Frontend\     <- Angular 18 standalone app
└── Backend\      <- FastAPI app (capital B)
```

---

## BRANDING

- **Site name**: Aurex (was previously "Firesports" / "FireEsports" — all renamed)
- **Logo file**: `src/assets/navbar/Aurex-Esports.jpg` (63KB JPG, rendered 36×36px in navbar)
- **Brand colour**: `#ff6b35` (orange) → `#f7931e` (amber) gradient
- **Browser tab title**: `Aurex | Fantasy Esports` (set in `src/index.html`)
- Every reference to "Firesports", "FireEsports", "firesports" has been replaced with "Aurex" across all `.ts` files and `index.html`

---

## TECH STACK

### Backend
| Concern | Choice |
|---|---|
| Framework | FastAPI (latest stable) |
| Database | PostgreSQL via SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | JWT via PyJWT (NOT python-jose — CVE-2024-33664) |
| OTP Delivery | Gmail SMTP via fastapi-mail + BackgroundTasks |
| Payments | Razorpay Python SDK (sandbox keys for dev) |
| Real-time | Native FastAPI WebSockets + ConnectionManager |
| Avatar Storage | Cloudinary Python SDK |
| Rate Limiting | slowapi on all auth/OTP endpoints |
| Password Hashing | passlib + bcrypt |
| Deployment | Docker + Docker Compose |

### Frontend
| Concern | Choice |
|---|---|
| Framework | Angular 18 (standalone components, no NgModules) |
| State | NgRx (Auth, Wallet, League, Leaderboard slices) |
| HTTP | Angular HttpClient + functional interceptors |
| UI | Custom CSS (NO mat-toolbar in navbar — see note below) |
| Real-time | Native browser WebSocket |
| Global styles | `src/global_styles.css` (referenced in angular.json — NOT styles.css) |

IMPORTANT — Navbar does NOT use mat-toolbar:
mat-toolbar applies overflow:hidden which clips the sidebar and coin-shop overlays.
The navbar uses a plain <nav> element. The overlay divs are siblings of <nav> inside the
component template, NOT children of the navbar. This is the only pattern that works correctly.

---

## ALL BACKEND API ENDPOINTS (verified against actual router files)

### Auth — /auth
| Method | Path | Body (JSON) | Auth | Description |
|---|---|---|---|---|
| POST | /auth/register | {username, email, password, confirm_password, age, free_fire_id?, free_fire_name?} | No | Creates unverified user + sends OTP. Returns {message} |
| POST | /auth/verify-register | {email, otp} | No | Verifies OTP -> returns tokens + user immediately |
| POST | /auth/login | {email, password} | No | Single step. JSON body. Returns tokens immediately. NO OTP. |
| POST | /auth/send-otp | {email, purpose} | No | Resend OTP. purpose in {"register", "login", "forgot_password"} |
| POST | /auth/forgot-password | {email} | No | Sends reset OTP. Always 200. |
| POST | /auth/reset-password | {email, otp, new_password, confirm_password} | No | Resets password |
| POST | /auth/refresh | {refresh_token} | No | Returns new access + refresh tokens |

CRITICAL — Login body is JSON, NOT form-encoded:
Backend LoginRequest is BaseModel(email: EmailStr, password: str).
Send as Content-Type: application/json. There is NO username field, NO OAuth2 form encoding.

CRITICAL — reset-password requires confirm_password:
Backend ResetPasswordRequest has confirm_password field and validates both match.

### Users — /users
| Method | Path | Body | Auth | Description |
|---|---|---|---|---|
| GET | /users/me | — | Yes | Full profile. NOT /auth/me. |
| PUT | /users/me | {username?, age?, free_fire_id?, free_fire_name?} | Yes | Update profile |
| POST | /users/me/avatar | multipart/form-data file | Yes | Upload avatar to Cloudinary |

### Leagues — /leagues
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /leagues | No | List all leagues |
| GET | /leagues/{id} | No | Single league by UUID |
| GET | /leagues/{id}/divisions | No | Division fee/reward config |
| GET | /leagues/{id}/rooms?status=open&division=1v1 | Yes | Rooms. NOT GET /rooms?league_id= |

CRITICAL — League IDs are UUIDs, not tier strings like "silver" or "gold".

### Rooms — /rooms
| Method | Path | Body | Auth | Description |
|---|---|---|---|---|
| GET | /rooms/{id} | — | Yes | Room detail |
| POST | /rooms/{id}/join | {free_fire_id} | Yes | Join room (deducts coins). Returns admin_room_id |
| POST | /rooms/{id}/leave | — | Yes | Leave room (refunds if open) |

CRITICAL — free_fire_id is required and validated non-empty. Never send "".
Read it from selectCurrentUser in the NgRx store. Redirect to /profile if not set.

### Wallet — /wallet
| Method | Path | Body | Auth | Description |
|---|---|---|---|---|
| GET | /wallet | — | Yes | Balance. NOT /wallet/me. |
| GET | /wallet/transactions?page=1&limit=20 | — | Yes | Paginated history |
| POST | /wallet/payment/initiate | {package_id} | Yes | Create Razorpay order � backend fetches price_inr from DB |
| POST | /wallet/payment/verify | {razorpay_order_id, razorpay_payment_id, razorpay_signature, coins} | Yes | HMAC verify + credit |

### Leaderboard — /leaderboard
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /leaderboard/global?limit=100 | Yes | Global top players |
| GET | /leaderboard/league/{id}?limit=50 | Yes | League leaderboard by UUID (NOT tier string) |

### Matches — /matches
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /matches/history?page=1&limit=20 | Yes | Current user's history. NOT /matches/me. |

### WebSocket — /ws
```
ws://localhost:8000/ws/rooms/{room_id}?token=<access_token>
```

### Admin — /admin (all require is_admin=True in JWT)
| Method | Path | Body | Description |
|---|---|---|---|
| GET | /admin/stats | — | Dashboard stats |
| POST | /admin/leagues | {name, tier, entry_fee, description, max_players, image_url?} | Create league |
| PUT | /admin/leagues/{id} | all fields optional | Update league |
| POST | /admin/rooms | {league_id, name, entry_fee, division, max_players, starts_at} | Create room |
| PUT | /admin/rooms/{id} | {name?, status?, admin_room_id?, starts_at?} | Update room |
| GET | /admin/users?page&limit&search&banned_only | — | Paginated user list |
| GET | /admin/users/{id} | — | Full user detail |
| PUT | /admin/users/{id}/ban?reason= | — | Ban user (reason in query param) |
| PUT | /admin/users/{id}/unban | — | Unban user |
| POST | /admin/wallet/credit | {user_id, amount, reason} | Credit coins |
| POST | /admin/wallet/debit | {user_id, amount, reason} | Debit coins |
| POST | /admin/matches/{room_id}/settle | {results: [{user_id, position, kills, coins_won, result}]} | Settle match |
| GET | /admin/audit-logs?page&limit&action&target_type | — | Audit trail |

CRITICAL — Match settlement path: /admin/matches/{room_id}/settle (NOT /admin/rooms/{id}/settle)
CRITICAL — Ban reason is a query param (?reason=...), not request body

---

## DATABASE SCHEMA

### users
id (uuid PK), username (unique), email (unique), hashed_password,
age, free_fire_id, free_fire_name, rank, avatar_url,
is_admin, is_verified, is_banned, created_at, last_login_at

### leagues
id (uuid PK), name, tier (silver/gold/diamond/br),
entry_fee (int coins), description, max_players, image_url, is_active

### rooms
id (uuid PK), league_id (FK), name, entry_fee, division (1v1/2v2/3v3/4v4/br),
max_players, current_players, status (open/closed/in_progress/completed),
admin_room_id (revealed only to joined players), starts_at, created_by, created_at

### room_players
id, room_id (FK), user_id (FK), free_fire_id, joined_at, position, kills, points

### wallets
id, user_id (unique FK), balance (int coins), updated_at
(locked_balance removed — closed economy, Alembic migration: 20260226_0001_a1b2c3d4e5f6)

### transactions
id, user_id (FK), type (credit/debit), amount, description,
reference (Razorpay payment_id), status (pending/completed/failed), created_at

### matches
id, room_id (FK), league_id (FK), user_id (FK),
division, room_name, result (win/loss/draw), coins_won, kills, position, played_at

### otp_records
id, email, user_id (nullable), otp_code (hashed),
purpose (register/login/forgot_password), is_used, expires_at, created_at

### audit_logs
id, admin_id (FK), action, target_type, target_id, details (JSON), created_at

---

## NAVBAR LAYOUT (verified working)

### Desktop and Mobile (same structure, responsive sizing)
```
[ Aurex JPG logo ] [ 🪙 4,980 + ] [ AUREX text→home ] ··············· [ ☰ ]
```

Left group: logo image + coins pill + "AUREX" text (all link to home)
Right group: hamburger only

### What is NOT in the top bar (everything lives in the sidebar):
- Profile button (removed from bar)
- Admin panel link
- Leaderboard link
- History link
- Wallet link
- Login / Logout

### Sidebar contents (authenticated):
1. Aurex logo + close button in header
2. User info strip (avatar icon, username, coin balance)
3. Admin Panel (admin only)
4. My Profile
5. Leaderboard
6. Match History
7. Buy Coins (opens coin shop)
8. Wallet
9. Logout (pinned to bottom)

### Sidebar contents (guest):
1. Aurex logo + close button
2. Login
3. Sign Up

### Mobile breakpoints:
- ≤600px: navbar height 58px, logo 32×32px, compact coins pill
- ≤380px: "AUREX" text hidden, only logo + coins + hamburger remain

### Root cause fix for broken menu:
The overlays (sidebar, coin shop) are SIBLINGS of <nav> inside the component template,
NOT children of it. This is critical — mat-toolbar (removed) and any overflow:hidden
container will clip overlay divs placed inside them.

---

## ADMIN PANEL WORKFLOW

Leagues are NEVER auto-created. The admin creates them manually:

1. Go to Admin -> League Mgmt
2. Create leagues: Silver (50 coins), Gold (100 coins), Diamond (150 coins), BR (200 coins)
3. Go to Admin -> Room Mgmt
4. Create a room (select league from dropdown, set division, start time)
5. Room UUID is shown in success message — copy it
6. When Free Fire gives you the in-game Room ID, paste it via "Publish In-Game Room Code"
7. Joined players will then see the room code
8. After the match: Admin -> Match Settlement -> paste Room UUID + results JSON -> Settle

---

## FRONTEND STATE (NgRx)

### Auth Slice
```typescript
{
  user: User | null, token: string | null, refreshToken: string | null,
  isAuthenticated: boolean, loading: boolean, error: string | null,
  registerOtpSent: boolean, pendingEmail: string | null,
  resetOtpSent: boolean, resetSuccess: boolean
}
```

### Wallet Slice
```typescript
{
  wallet: Wallet | null, transactions: Transaction[],
  loading: boolean, error: string | null,
  pendingOrder: PaymentInitiateResponse | null,
  paymentLoading: boolean, lastCreditedCoins: number | null
}
```

### League Slice
```typescript
{
  leagues: League[], rooms: Room[], selectedRoom: Room | null,
  joinResponse: JoinRoomResponse | null, loading: boolean, error: string | null
}
```

### Leaderboard Slice
```typescript
{
  globalLeaderboard: LeaderboardEntry[],
  leagueLeaderboards: LeagueLeaderboard[],  // keyed by leagueId (UUID)
  loading: boolean, error: string | null
}
```

---

## AUTH FLOW

### Register (2-step)
1. POST /auth/register JSON -> returns {message}
2. User enters OTP -> POST /auth/verify-register -> returns tokens + user
3. Auto-logged in, navigates to "/"

### Login (1-step — NO OTP)
1. POST /auth/login JSON {email, password} -> tokens + user immediately
2. Navigates to "/"

### Forgot Password (2-step)
1. POST /auth/forgot-password {email}
2. POST /auth/reset-password {email, otp, new_password, confirm_password}

### App Boot
app.component.ts dispatches loadMe() if access_token in localStorage.

---

## RAZORPAY PAYMENT FLOW

Navbar and wallet component both handle Razorpay modal.
Razorpay script in index.html: <script src="https://checkout.razorpay.com/v1/checkout.js">
Use declare var Razorpay: any; in any component that calls new Razorpay(options).open()

---

## COMPLETE FILE INVENTORY

### Assets
- `src/assets/navbar/Aurex-Esports.jpg` — brand logo (JPG, 63KB)
- `src/assets/navbar/Diamond_rank.png` — rank badge (no longer shown in navbar)
- `src/global_styles.css` — utility classes (.glass, .btn-gaming, .gradient-text)
- `src/index.html` — includes Razorpay script, title "Aurex | Fantasy Esports"

### Navbar
- `src/app/shared/components/navbar/navbar.component.ts` — complete rewrite, no mat-toolbar
- `src/app/shared/components/admin-sidebar/admin-sidebar.component.ts` — admin panel sidebar with active highlight

### Auth pages
- `login.component.ts` — "Sign in to your Aurex account"
- `register.component.ts` — "Join Aurex"
- `forgot-password.component.ts`

### Features
- `home.component.ts` — "Why Choose Aurex?"
- `league.component.ts` — fetches league by UUID, uses league.tier for BR check
- `room.component.ts` — reads freeFireId from store, guards empty UID, WebSocket live updates
- `profile.component.ts` — avatar upload, coin-gated FF ID edit
- `wallet.component.ts` — Razorpay buy flow, name "Aurex"
- `leaderboard.component.ts` — maps tier->UUID via leagues store
- `history.component.ts` — paginated match history
- `admin.component.ts` — all 7 sections, no auto-bootstrap of leagues

### Store
- `store/auth/` — actions, reducer, selectors, effects
- `store/wallet/` — actions, reducer, selectors, effects
- `store/league/` — actions, reducer, selectors, effects
- `store/leaderboard/` — actions, reducer, selectors, effects

---

## ALL BUGS FIXED (19 total)

1. db.bind — SQLAlchemy 2.0 removed .bind
2. Dummy bcrypt hash — caused ValueError on failed logins
3. asyncio.create_task from sync context — RuntimeError
4. Partial commits in settle_room — corrupt wallet on failure
5. psycopg2 consistency — Dockerfile build deps
6. timezone = UTC in alembic.ini — ZoneInfo("") error
7. version_locations in alembic.ini — "Multiple version locations"
8. tzdata missing on Windows — ZoneInfo("UTC") fails
9. Login was treated as 2-step — backend returns tokens directly; fixed to 1-step
10. Wrong API URLs — /auth/me, /matches/me, /wallet/me, GET /rooms?league_id=
11. resetPassword() missing confirm_password — backend requires it
12. Register password min 6 — backend enforces 8
13. Register age min 16 — backend enforces 13
14. onVerify() missing take(1) — multiple dispatches
15. Leaderboard dispatched with tier strings — must use UUIDs
16. League title used string-match on UUID — now fetches league by UUID
17. Admin auto-bootstrapped leagues silently — removed; admin creates manually
18. Sidebar overlays clipped by mat-toolbar — replaced with plain nav, overlays are siblings
19. locked_balance dead column removed — was never written to (always 0); Alembic migration added

---

## ENVIRONMENT VARIABLES (.env)

```
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_NAME=freefire_db
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_password

SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=<16-char Google App Password>
MAIL_FROM=your@gmail.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com

RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=your_secret

CLOUDINARY_CLOUD_NAME=your_cloud
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret

CORS_ORIGINS=http://localhost:4200
FIRST_ADMIN_EMAIL=admin@yourdomain.com
```

---

## HOW TO RUN

```bash
# Backend
cd "C:\Users\rajpu\Desktop\Claude Test\Freefire_app\Backend"
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
psql -U postgres -c "CREATE DATABASE freefire_db;"
# fill .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd "C:\Users\rajpu\Desktop\Claude Test\Freefire_app\Frontend"
npm install && ng serve
```

First admin: Register normally, then:
```sql
UPDATE users SET is_admin = TRUE WHERE email = 'your@email.com';
```

---



## COIN PACKAGES SYSTEM

Pricing is stored in the coin_packages DB table. Admin manages it via /admin/coin-packages.
Frontend (wallet page + navbar coin shop) fetches from GET /coin-packages on load � no hardcoding.

Security rule (enforced by backend):
  POST /wallet/payment/initiate takes ONLY {package_id: uuid}.
  Backend fetches price_inr from DB. Frontend amount is NEVER trusted.
  A user cannot tamper the request to pay ?1 for a 5600-coin package.

Alembic migration chain (run in order):
  1. cfd62feace54 � initial schema
  2. a1b2c3d4e5f6 � remove locked_balance
  3. b2c3d4e5f6a7 � add coin_packages table + seed 6 default packages

Frontend files:
  core/models/coin-package.model.ts         CoinPackage + ApiCoinPackage interfaces
  core/services/coin-packages.service.ts    GET /coin-packages ? camelCase map
  features/wallet/wallet.component.ts       fetches packages, dispatches initiatePayment({ packageId })
  shared/components/navbar/navbar.component.ts  fetches packages for coin shop modal

---
## BUSINESS MODEL — CLOSED COIN ECONOMY

Aurex is a competitive esports tournament platform, NOT a real-money gaming operator.

```
User deposits INR → receives coins → enters tournaments → wins coins
Coins stay inside Aurex forever. They cannot be withdrawn as real money.
```

Revenue model (platform fee example):
```
10 players × 100 coins entry = 1,000 coins collected
900 coins distributed as prizes (90%)
100 coins retained as platform fee (10%)
```

No liquidity risk. No TDS. No KYC for payouts. No RazorpayX. No withdrawal table.
All transaction types: deposit / entry_fee / prize_credit / admin_credit / admin_debit.

Coin packages (single source of truth — wallet page AND navbar coin shop use same list):
| Coins | Price |
|---|---|
| 100 | ₹80 |
| 310 | ₹250 |
| 520 | ₹400 |
| 1,060 | ₹800 |
| 2,180 | ₹1,600 |
| 5,600 | ₹4,000 |

---

## WHAT TO DO NEXT

### Step 1: ng build — fix any compile errors
```bash
cd "C:\Users\rajpu\Desktop\Claude Test\Freefire_app\Frontend"
ng build
```
Common things to check:
- All imports present in each component
- Template binding types (async pipe, optional chaining)
- No stale references to removed methods (e.g. goToProfile() removed from navbar class — use goTo('/profile') instead)

### Step 2: Create environment.prod.ts
File missing. Create at src/environments/environment.prod.ts:
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://your-backend-domain.com',
};
```

### Step 3: End-to-end test checklist
Test this exact sequence:
1. Not logged in: navbar shows [logo] [AUREX] [☰], sidebar shows Login / Sign Up
2. Register -> OTP email -> verify -> auto-logged in, home page
3. Logged in: navbar shows [logo] [🪙 coins] [AUREX] [☰]
4. Click coins pill -> coin shop opens (centred, NOT clipped)
5. Click ☰ -> sidebar opens with all 8 items
6. Sidebar: Admin Panel (if admin), Profile, Leaderboard, History, Buy Coins, Wallet, Logout
7. Buy coins -> Razorpay modal -> pay -> balance updates
8. Join a room -> see admin_room_id after joining
9. Admin: create league -> create room -> publish room code -> settle match
10. Leaderboard loads correctly per tier (Silver/Gold/Diamond)
11. Mobile view (375px): logo + coins + AUREX text + hamburger — no overflow

### Step 4: Production deployment
```bash
docker-compose up --build -d
```
Update CORS_ORIGINS in .env and apiUrl in environment.prod.ts.

---

## DO'S

- Always read the actual file before modifying — never assume
- Navbar overlays must be siblings of <nav>, NEVER inside mat-toolbar or any overflow:hidden container
- Login uses JSON body with email field — NOT form-encoded, NOT username
- reset-password body must include confirm_password
- Always use PyJWT, never python-jose
- Always use BackgroundTasks for email
- Read freeFireId from selectCurrentUser — never send empty string to room join
- Map tier strings to league UUIDs before dispatching league leaderboard
- Fetch league by UUID from /leagues/{id} to get name and tier
- Use league.tier === 'br' for BR checks — never compare leagueId to 'br'
- Global stylesheet is src/global_styles.css
- Logo file is src/assets/navbar/Aurex-Esports.jpg

## DON'TS

- Don't put overlay divs inside mat-toolbar — they get clipped by overflow:hidden
- Don't use mat-toolbar in the navbar at all — use plain <nav>
- Don't auto-create leagues in code — admin creates them manually via the UI
- Don't send login as form-encoded — backend uses JSON with email field
- Don't omit confirm_password from /auth/reset-password
- Don't use /admin/rooms/{id}/settle — correct: /admin/matches/{room_id}/settle
- Don't dispatch league leaderboard with tier strings — use UUID
- Don't compare leagueId to 'silver'/'gold'/'diamond'/'br' — leagueId is always a UUID
- Don't send freeFireId: '' to room join — backend 422
- Don't use python-jose — CVE-2024-33664
- Don't do per-player db.commit() in loops — partial commits corrupt wallets
- Don't add version_locations = to alembic.ini
- Don't set timezone = UTC in alembic.ini — comment it out
- Don't delete Alembic migration files
- Don't use /auth/me, /matches/me, /wallet/me — wrong endpoints
- Don't forget Razorpay script in index.html
- Don't commit .env
