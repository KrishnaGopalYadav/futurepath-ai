# Google Auth Implementation Challenges – 1

## FuturePath AI — Implementation, Troubleshooting and Interview Preparation

This document records the complete Google OAuth implementation journey for the FuturePath AI MVP, the problems encountered during GitHub/Docker/OAuth setup, the diagnosis and resolution of each problem, and interview-oriented questions and answers.

## 1. Executive Summary

The first application slice was authentication with two choices: username/password and Google SSO. The key architectural decision was that Google OAuth credentials belong to the FuturePath deployment, not individual users.

The completed flow is:

```text
Login page
   ↓
Password OR Google
   ↓
FuturePath backend
   ↓
Google authentication for SSO
   ↓
OAuth callback
   ↓
Find/Create FuturePath user
   ↓
HttpOnly application session
   ↓
Authenticated FuturePath page
```

Docker Compose provides a reproducible local environment with Next.js on port 3000 and FastAPI on port 8000.

## 2. Step-by-Step Journey and Challenges

### Step 1 — Repository and MVP scope

We started from the FuturePath AI repository and its product and architecture documentation. The first implementation target was authentication because every later career capability depends on a stable user identity.

**Challenges:**
- The repository contained evolving product and architecture documentation plus application code.
- Authentication had to work across frontend, backend, database and session security.

**Lesson:** Build a vertical slice first rather than implementing every future technology immediately.

### Step 2 — GitHub permissions

An attempted push to the upstream repository returned HTTP 403 because the authenticated GitHub account did not have write permission.

```text
git push origin main
remote: Permission ... denied
fatal: ... 403
```

**Resolution:** use collaborator access or a fork. GitHub authentication and repository authorization are different concepts.

### Step 3 — Login MVP

The login page was designed with two entry points:

```text
Username / Password
Continue with Google
```

The purpose was to establish a stable authentication foundation before building career features.

### Step 4 — Application-level Google OAuth

The important conceptual question was whether every new user would need the Google OAuth secrets. They do not.

```text
FuturePath deployment
  ├── GOOGLE_CLIENT_ID
  └── GOOGLE_CLIENT_SECRET
             ↓
       FuturePath backend
             ↓
       Any FuturePath user
             ↓
        Google account
```

The Client ID identifies the application. The Client Secret is confidential server-side configuration. The user only authenticates with their own Google account.

**Challenge:** confusing application credentials with user credentials.

**Correct design:** configure Google OAuth once for the application; users simply click Continue with Google.

### Step 5 — Environment and secrets

Local configuration uses `backend/.env`. The real file must be ignored by Git. The repository contains `.env.example` so required variables are documented without exposing secrets.

Important variables include:

```dotenv
JWT_SECRET=<strong-random-secret>
GOOGLE_CLIENT_ID=<your-google-web-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
COOKIE_SECURE=false
```

Production should inject these values through deployment-level secrets/environment configuration and use `COOKIE_SECURE=true` over HTTPS.

### Step 6 — Secure application session

The initial MVP approach could have exposed a JWT in a URL. That was replaced with an HttpOnly cookie.

```text
OAuth callback
    ↓
Set-Cookie: futurepath_session=...
    ↓
/welcome
```

**Why:** URL tokens can leak through history, logs, copied links, analytics and referrer data. An HttpOnly cookie is not directly readable by normal browser JavaScript.

### Step 7 — Automatic Google user provisioning

After successful Google authentication, the backend verifies the Google email and searches for the FuturePath user.

```text
Verified Google email
       ↓
Existing user? ── yes ──> sign in
       │
       no
       ↓
Create FuturePath user
       ↓
Create application session
```

This solves the original onboarding problem: a new user never needs Google Cloud Console access, a Client ID, Client Secret, `.env`, or Docker.

### Step 8 — Dockerization

The project was split into two services:

```text
frontend → Next.js → localhost:3000
api      → FastAPI → localhost:8000
```

The backend also uses a mounted development data directory for SQLite.

### Step 9 — Docker port collision

The first build succeeded, but startup failed with:

```text
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Root cause:** an older FuturePath API container was already publishing port 8000. An older frontend container was also using 3000.

**Diagnosis:**

```bash
lsof -i :8000
docker ps
```

**Resolution:** stop stale containers and recreate the current Compose stack.

### Step 10 — Backend running but Swagger unavailable

At one point the API logs showed:

```text
Uvicorn running on http://0.0.0.0:8000
```

but `docker port futurepath-ai-api-1` returned nothing and `localhost:8000` refused connections.

**Important distinction:** listening inside a container does not mean the port is published to the host.

The Compose configuration correctly contained:

```yaml
ports:
  - "8000:8000"
```

The running container had to be recreated:

```bash
docker compose down
docker compose up --build -d
```

After that, Swagger became reachable at `http://localhost:8000/docs`.

### Step 11 — Frontend browser troubleshooting

Chrome initially showed `ERR_CONNECTION_REFUSED` even though Docker reported the frontend as running.

We tested independently:

```bash
curl -I http://localhost:3000
```

which returned `HTTP/1.1 200 OK`.

We also checked:

```bash
ping -c 1 localhost
```

which resolved localhost to `127.0.0.1`.

**Lesson:** use curl to distinguish browser issues from server/container issues before modifying application code.

### Step 12 — End-to-end Google OAuth validation

After the backend and frontend were reachable, Google login was tested successfully. The browser returned to FuturePath and displayed the authenticated user.

This validated the full local flow: login → Google → callback → user lookup/creation → secure session → authenticated page.

## 3. Security Checklist

- Never commit `backend/.env`.
- Keep the Google Client Secret server-side.
- Use a strong random JWT signing secret.
- Do not put bearer tokens in query strings.
- Use HttpOnly cookies for application sessions.
- Use Secure cookies in HTTPS production.
- Register exact Google OAuth redirect URIs.
- Use HTTPS in production.
- Use deployment secret management.
- Sanitize logs so passwords, tokens, API keys and resume content are not logged.

## 4. Interview Q&A

### Q1. Explain the Google OAuth implementation.

**A:** The Next.js frontend provides a Google login option. The browser is redirected to Google. The FastAPI backend owns the application's Google Client ID and Client Secret and handles the callback. After successful authentication, the backend finds or creates the FuturePath user and establishes an HttpOnly application session.

### Q2. Why don't users need the Google Client Secret?

**A:** The secret identifies the FuturePath application and is used by the trusted backend during the OAuth exchange. It is not a user credential. Users authenticate with their own Google accounts.

### Q3. What happens for a first-time Google user?

**A:** The backend verifies the Google identity, checks the user table by email, creates a FuturePath user if no account exists, and establishes the application session.

### Q4. Why handle the OAuth callback on the backend?

**A:** The backend is trusted server-side code and can safely use the Client Secret. It also controls identity mapping and application session creation without exposing the secret to the browser.

### Q5. Why is the redirect URI important?

**A:** Google only redirects to registered callback URLs. A mismatch prevents the authorization response from being sent to an untrusted endpoint. Local and production callback URLs therefore need explicit configuration.

### Q6. Why not put the JWT in the URL?

**A:** URLs can appear in browser history, logs, copied links, analytics and referrer data. HttpOnly cookies avoid this URL exposure and reduce direct JavaScript access to the token.

### Q7. OAuth vs application session?

**A:** OAuth authenticates the user through Google and provides trusted identity information. FuturePath then creates its own application session so the user can access protected FuturePath APIs.

### Q8. How were secrets handled?

**A:** Real secrets were stored in `backend/.env`, which is ignored by Git. `.env.example` documents required variables. Production should use deployment-level secret/environment configuration.

### Q9. What caused the Docker port error?

**A:** An older container already owned host port 8000. Docker cannot bind the same host port to two containers. We identified the conflict with `docker ps` and `lsof`, stopped the stale container, and restarted Compose.

### Q10. Why can Uvicorn run while localhost:8000 fails?

**A:** Uvicorn can listen inside the container without a host port mapping. Docker must publish `8000:8000` for the Mac to reach it.

### Q11. How did you debug the frontend browser error?

**A:** `curl` returned HTTP 200 and `ping` showed localhost resolving to 127.0.0.1. That proved Docker and Next.js were functioning and isolated the issue from application code.

### Q12. Why Docker Compose?

**A:** The project has multiple services. Compose provides a reproducible definition of builds, ports, environment, dependencies, volumes and restart behavior.

### Q13. What should change before production?

**A:** Use PostgreSQL instead of development SQLite, migrations, HTTPS, secure cookies, secret management, production OAuth redirect URIs, observability, backups, rate limiting and appropriate deployment architecture.

### Q14. What is the next MVP feature?

**A:** The repository roadmap identifies Release 1 as Career Profile Intelligence. The next implementation should collect and persist the user's career profile, including experience, education, skills and target career direction.

### Q15. Explain the entire system in 60 seconds.

**A:** FuturePath has a Next.js frontend and FastAPI modular monolith. Authentication supports password and Google SSO. For Google SSO, Google authenticates the user while the backend uses FuturePath's application OAuth credentials to process the callback. The backend finds or creates the FuturePath user and sets an HttpOnly session cookie. Docker Compose makes local development reproducible. The next product capability is the career profile, followed by AI-driven career intelligence.

## 5. Quick Revision Sheet

```text
OAuth Client ID/Secret = application credentials
Google account         = user identity
OAuth callback         = backend endpoint
Application session    = FuturePath's authenticated state
HttpOnly cookie        = reduced JS token exposure
Redirect URI            = exact Google callback registration
.env                    = local runtime configuration
Docker mapping          = host:container
8000:8000               = Mac port 8000 → API port 8000
R1                      = Career Profile Intelligence
R2                      = Career Gap & Target Role Intelligence
R3                      = Market + Learning Intelligence
R4                      = Continuous Personal Career Intelligence
```

## 6. Final Mental Model

The most important concept is the separation of application credentials from user identity. FuturePath owns one Google OAuth client configuration. Google owns the user's identity. The backend bridges those systems and creates a FuturePath session. Therefore, unlimited new users can use Google SSO without ever receiving or configuring the application's Google secrets.
