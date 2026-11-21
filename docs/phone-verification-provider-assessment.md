# Seller phone ownership provider assessment

**Assessment date:** 2026-11-21  
**Decision:** NO PROVIDER INTEGRATED. Real OTP remains blocked until an owner-approved, genuinely no-cost live-delivery arrangement is available.

## Candidate: SMSHub (Ethiopia)

Official documentation at https://smshub.et/docs states:

- Live SMS delivery to Ethio Telecom and Safaricom Ethiopian mobile numbers.
- A Verify API with `POST /api/verify/send` and `POST /api/verify/check`; codes are generated and checked by the provider.
- 10 free credits are added once after identity/KYC approval.
- Ethio Telecom uses 1 credit per single-segment SMS; Safaricom uses 2 credits.
- Sending and API access are locked until KYC approval.
- KYC requires a government identity document; the provider lists Fayda, passport, residence permit and other accepted documents.
- After the initial free credits, the service is prepaid. The API returns insufficient-credit errors; the provider does not describe a continuing unlimited free tier.

Sources:
- API docs: https://smshub.et/docs
- Pricing and free-credit terms: https://smshub.et/
- Terms of Use: https://smshub.et/terms

## Decision rationale

SMSHub is a real-delivery technical candidate and its first 10 credits require no payment after KYC. However, the offer is limited, identity documents must be submitted to the provider, and further usage is prepaid. It is not a sustainable no-cost production service. The owner has not authorized submission of personal identity documents or provision of an API key.

No account has been created, no Fayda/ID/passport document has been shared, no API key has been obtained, and no SMS has been sent. Do not ask for a top-up or automatically trigger any payment.

## Required conditions before any future integration

1. Owner independently reviews the provider's current terms, privacy notice, KYC requirements and data-processing/subprocessor locations.
2. Owner decides whether the provider's identity verification and limited free-credit offer are acceptable.
3. A dedicated provider account is used only for this marketplace; no payment method or automatic top-up is configured.
4. Backend integration is server-only, with API key in a secret store, request rate limits, balance guard, provider timeout, delivery state, audit record and fail-closed behavior.
5. The application stops sending when the free-credit allowance is exhausted; it must never initiate a purchase or ask for a top-up.
6. Ethiopian counsel assesses whether sending phone numbers to the SMS provider is a cross-border personal-data transfer and confirms a lawful arrangement under Proclamation No. 1321/2024 before real users are verified.
7. Seller UI must never display a verified badge unless a successful one-time provider check is persisted against the same account phone number.

## Alternatives assessed

- Africa's Talking sandbox: useful for development, but a sandbox/simulator does not prove live delivery to a real handset; not suitable for phone ownership acceptance.
- SMSHub test endpoint: validates request format without contacting a carrier or consuming credits; not a real OTP test.

## Current implementation status

- Phone verification API, mobile verification UI and provider client: NOT IMPLEMENTED.
- Phone ownership state: NOT VERIFIED.
- OTP simulation: PROHIBITED.
- Production readiness: BLOCKED until a suitable real provider and lawful data-transfer arrangement are approved.
