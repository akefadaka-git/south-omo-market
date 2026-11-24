# Administrator provisioning runbook

Administrator privileges are never assigned by public registration and there is no HTTP endpoint for granting or revoking administrator access.

## Preconditions

1. The target person must already have a registered account.
2. An authorized operations owner must independently verify the person's identity and authorization before provisioning.
3. The operator must have trusted shell access to the backend host and its configured database credentials. Do not expose database credentials or run this command from an untrusted workstation.
4. Use a unique, attributable operator identifier. The CLI records this identifier in the audit event; host access logs should independently identify the authenticated shell operator.

## Grant access

From the `backend/` directory on the trusted host:

```bash
python -m app.admin_cli grant --operator "approved-operator-id"
```

The command prompts for the target account's phone number and requires the operator to enter it a second time. The phone number is not placed in shell history or process arguments. The command only grants access to an existing account; it does not create accounts, disclose passwords, or issue tokens.

## Revoke access

```bash
python -m app.admin_cli revoke --operator "approved-operator-id"
```

The command uses the same interactive confirmation. It refuses to revoke the last active administrator. Provisioning changes and their audit records are committed in the same database transaction.

## Audit and operational controls

- Grant/revoke events use `admin.access.granted` and `admin.access.revoked`, with `actor_id=null`, the operator identifier, and `provisioning_method=trusted_cli`. The null actor indicates that this action was performed out-of-band rather than by an API user.
- Moderation decisions record the authenticated administrator as actor and the previous/new listing status plus the optional moderation note.
- The PostgreSQL migration installs a trigger that rejects UPDATE and DELETE against `audit_events`; the API exposes read-only, administrator-protected history.
- Keep database backups and restrict direct database access. Audit history does not replace host authentication logs or an incident-response process.
- Never put real phone numbers, credentials, or customer data in tests, commits, CI, or screenshots.
