# Emirates sample database

A realistic airline database for testing Velora chat. Five tables, real joins, good for complex SQL questions.

**Tables:** `aircraft` · `passengers` · `flights` · `bookings` · `crew`

---

## Quick setup (Docker Compose)

From this folder:

```bash
docker compose up -d
docker exec -i emirates-db psql -U emirates -d emirates < emirates_seed.sql
```

Connection string for Velora:

```
postgresql://emirates:emirates123@localhost:5435/emirates
```

Verify:

```bash
docker exec emirates-db psql -U emirates -d emirates -c "
SELECT 'aircraft' AS tbl, COUNT(*) FROM aircraft
UNION ALL SELECT 'passengers', COUNT(*) FROM passengers
UNION ALL SELECT 'flights', COUNT(*) FROM flights
UNION ALL SELECT 'bookings', COUNT(*) FROM bookings
UNION ALL SELECT 'crew', COUNT(*) FROM crew;
"
```

Expected: ~30 / ~53 / ~51 / ~57 / ~55 rows.

---

## Alternative: single docker run

```bash
docker run --name emirates-db \
  -e POSTGRES_DB=emirates \
  -e POSTGRES_USER=emirates \
  -e POSTGRES_PASSWORD=emirates123 \
  -p 5435:5432 \
  -d pgvector/pgvector:pg16
```

Then load SQL:

```bash
docker exec -i emirates-db psql -U emirates -d emirates < emirates_seed.sql
```

---

## Load data with DBeaver

1. **New connection** → PostgreSQL
2. Host `localhost`, Port `5435`, Database `emirates`, User `emirates`, Password `emirates123`
3. **Test connection** → Finish
4. Right-click **emirates** → SQL Editor → Open SQL Script → select `emirates_seed.sql`
5. Select all (`Ctrl+A`) → Execute (`Ctrl+Enter`)

---

## What the data contains

Emirates airline operational database. Fleet (A380, B777, A350), passenger Skywards tiers (Blue → Platinum), DXB routes worldwide, bookings with cabin class and revenue, crew with roles (Captain, Purser, Cabin Crew).

---

## Sample questions (easy → hard)

1. "Show me all passengers who are Platinum tier members"
2. "How many flights are currently scheduled vs completed?"
3. "Which aircraft have not had maintenance since before 2024?"
4. "What is the total revenue from completed bookings by cabin class?"
5. "Show all bookings by Indian passengers with flight number and fare paid"
6. "Which passengers booked First Class and what are their Skywards tiers?"
7. "What is the average economy fare per route (origin → destination)?"
8. "For each completed flight: flight number, route, passenger count, total revenue"
9. "Top 5 passengers by total spend and number of flights taken"
10. "For each captain on a scheduled flight: name, flight hours, route, passengers booked, expected revenue"

---

## Stop / reset

```bash
docker compose down      # stop container
docker compose down -v   # stop + wipe data
```

---

## If Velora runs in Docker

Use your host IP or `host.docker.internal` instead of `localhost`:

```
postgresql://emirates:emirates123@host.docker.internal:5435/emirates
```

Note port **5435** (mapped host port), not 5432.
