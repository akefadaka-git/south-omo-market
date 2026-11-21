# Android production signing and release preparation

**State:** PREPARED, NOT CONFIGURED. No production keystore exists in this repository or CI. No release was built or published.

## Key ownership and generation

The production upload key must be generated and retained by the owner on a trusted computer with a JDK. Run the repository helper from the project root:

    bash mobile/scripts/generate_upload_keystore.sh

The helper defaults to `$HOME/.config/south-omo-market/upload-keystore.jks`, uses a restrictive umask, refuses to overwrite an existing key and lets `keytool` prompt interactively for the keystore/key passwords. It prints the public certificate SHA-256 fingerprint, not the passwords.

Keep the JKS file outside the repository and outside synced/public folders. Maintain at least two encrypted offline recovery copies under owner-controlled custody. Keep passwords in a password manager separate from the key file. Never commit, email, upload to chat, or paste the keystore or passwords into an issue/PR.

The root `.gitignore` excludes `*.jks`, `*.keystore` and `key.properties` as an additional safeguard; this is not a substitute for keeping the key outside the checkout.

## CI secret configuration

Only after the production API and data-residency blocker are cleared, configure these GitHub repository secrets:

- `ANDROID_KEYSTORE_BASE64`: base64 encoding of the owner-held JKS file.
- `ANDROID_KEYSTORE_PASSWORD`: keystore password.
- `ANDROID_KEY_ALIAS`: upload-key alias.
- `ANDROID_KEY_PASSWORD`: private-key password.

Configure these non-secret repository variables:

- `API_BASE_URL`: production HTTPS API base ending in `/api/v1`.
- `PRODUCTION_RELEASE_ENABLED`: set to `true` only when the owner authorizes a production signing build.

Before enabling the variable, configure the GitHub `production-signing` environment with required reviewers/approval rules and ensure only trusted maintainers can change release secrets, variables and tags.

## Gated release workflow

`.github/workflows/android-production-release.yml` is manual only. Its job runs only when:
1. The selected ref is a semantic-version tag such as `v1.0.0`.
2. That tag points to a commit reachable from `main`.
3. `PRODUCTION_RELEASE_ENABLED=true`.
4. All four signing secrets and a valid HTTPS `API_BASE_URL` are present.

The workflow generates the Android scaffold, materializes the keystore under the ephemeral runner's temporary directory, configures Gradle signing, builds an Android App Bundle, verifies the signature and uploads a short-retention artifact. It does not publish to Google Play, deploy the API, create a release, or modify marketplace data.

The helper `mobile/scripts/configure_android_release_signing.py` refuses to run if the keystore is missing or inside the checkout. It injects signing configuration into the generated Flutter Gradle project; it does not create or export private keys.

## Existing CI signing is not production signing

The regular CI workflow creates a random, short-lived test keystore and signs test APK artifacts after building. That certificate is intentionally ephemeral and cannot be used for future updates. Do not distribute CI APKs as production releases.

## Release acceptance checklist

- [ ] A4 verification complete on the exact release commit.
- [ ] A5 release/signing approval recorded separately.
- [ ] Production API and database/object storage meet Ethiopian data-residency and legal requirements.
- [ ] Production HTTPS API is available and passes readiness/security smoke tests.
- [ ] Owner-held key generated, fingerprint recorded, and two encrypted offline backups verified.
- [ ] GitHub signing secrets added without exposing values in logs.
- [ ] Required reviewer protection configured on `production-signing`.
- [ ] Version/tag points to a reviewed commit reachable from `main`.
- [ ] App Bundle signature and certificate fingerprint verified.
- [ ] Physical Android install/update/rollback acceptance completed.
- [ ] Release notes, privacy notice, terms, support contact and incident process approved.
- [ ] Play Store or other distribution submission separately authorized.

## Current blockers

- No owner keystore, signing secrets, production API URL or protected GitHub environment is configured.
- No Ethiopia-located production data platform is selected.
- No signed production AAB or physical-device acceptance exists.
- This workflow is release preparation only. It does not authorize merge, deployment or commercial release.
