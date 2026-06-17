# TODO - Production-ready Auth (Django + React)

## Backend (Django)
- [ ] Update `UserCreateSerializer` so `organization_id` is optional.
- [ ] Implement org join vs auto-create logic during signup.
- [ ] Fix password reset uid/token encoding + decoding for UUID PKs.
- [ ] Harden `SocialTokenExchangeView` so it relies on authenticated Django session.
- [ ] Add `POST /api/v1/auth/logout/` endpoint that blacklists refresh token.
- [ ] Wire logout endpoint into `core/urls.py`.

## Frontend (React)
- [ ] Make Organization ID optional in `Register.tsx` and avoid sending empty value.
- [ ] Update `App.tsx` to attempt `socialTokenExchange()` on load without requiring `?social=1` marker.
- [ ] Update `useAuth.ts` (or equivalent logout handler) to call backend logout.
- [ ] Ensure social login end-to-end stores JWT and redirects correctly.

## OAuth Setup Instructions
- [ ] Document required env vars + allauth/site config + callback/redirect URLs.

## Testing Checklist
- [ ] Register (create new org)
- [ ] Register (join existing org via org id)
- [ ] Login (email/password)
- [ ] Forgot password + reset password
- [ ] Google OAuth -> JWT -> dashboard
- [ ] Microsoft OAuth -> JWT -> dashboard
- [ ] Logout blacklists refresh token

