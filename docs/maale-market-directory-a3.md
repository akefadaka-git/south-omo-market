# Maale Market Directory and Weekly Schedule — A3

## Owner-provided initial directory

| Market | Weekday |
|---|---|
| Beneta | Thursday |
| Asheker | Tuesday |
| Boshkoro | Saturday |
| Bala | Tuesday |
| Koybe | Monday |
| Bobo | Wednesday |
| Ajo | Saturday |
| Gento | Saturday |

Weekday integers use ISO-style Monday=0 through Sunday=6. Empty days mean no market is recorded in this initial directory; they do not assert that no market exists elsewhere.

## Data model

- `markets`: stable ID, unique code, official supplied name, optional FK to `locations`, active status and timestamps.
- `market_schedule_days`: one row per market/weekday, active flag and creation timestamp.
- Unique `(market_id, weekday)` and a weekday range check enforce the recurring schedule.
- Existing geographic `locations` remain authoritative. Initial market location associations are NULL; no association is inferred from a market name.
- Administrative changes are written to the existing `audit_events` table. Schedule changes record before/after weekday sets.

## API

Public:
- `GET /api/v1/markets`
- `GET /api/v1/markets/schedule`
- `GET /api/v1/markets/by-day/{weekday}`
- `GET /api/v1/markets/{market_id}`

Administrator-only:
- `GET /api/v1/admin/markets`
- `POST /api/v1/admin/markets`
- `PATCH /api/v1/admin/markets/{market_id}`
- `PUT /api/v1/admin/markets/{market_id}/schedule`
- `PATCH /api/v1/admin/markets/{market_id}/status`

The schedule response includes all seven days and timezone `Africa/Addis_Ababa`. Market names are preserved as supplied. No Amharic or Maale translations are asserted for market names.

## Clients

- React administration supports market creation, optional selection of an existing geographic location, recurring day editing, active/inactive status and weekly preview.
- Flutter exposes a weekly calendar from marketplace discovery.
- Mobile schedule cache is read-only and stored separately from listing drafts. Cached data is shown offline with its last-updated timestamp.
- Weekday labels have English and Amharic UI strings. Maale market-name translations remain unset until human review.

## Safety and scope

- Initial seed contains exactly the eight owner-provided records and is repeatable by stable codes and IDs.
- Location IDs are never inferred; administrators may select only an existing active location.
- No payment, wallet, transaction, logistics or GPS features are introduced.
- No production database migration, deployment, merge or commercial activation is authorized by this feature implementation.
