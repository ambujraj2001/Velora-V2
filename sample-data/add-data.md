No problem. You only need Docker — no local Postgres install needed.

---

## Step 1: Pull and run Postgres with pgvector

Open your terminal and run this one command:

```bash
docker run --name emirates-db \
  -e POSTGRES_DB=emirates \
  -e POSTGRES_USER=emirates \
  -e POSTGRES_PASSWORD=emirates123 \
  -p 5435:5432 \
  -d pgvector/pgvector:pg16
```

Verify it's running:
```bash
docker ps
```

You should see `emirates-db` with status `Up`.

---

## Step 2: Connect in DBeaver

Open DBeaver, then:

1. Click **New Database Connection** (the plug icon top left)
2. Choose **PostgreSQL** → click Next
3. Fill in:

```
Host:      localhost
Port:      5435
Database:  emirates
Username:  emirates
Password:  emirates123
```

4. Click **Test Connection** — it should say Connected
5. Click **Finish**

If DBeaver says it needs to download the Postgres driver, click **Download** and let it finish.

---

## Step 3: Run the SQL file

1. In DBeaver left panel, expand your connection → expand **emirates** database
2. Right-click **emirates** → **SQL Editor** → **Open SQL Script**
3. Open the `emirates_seed.sql` file you downloaded
4. Press **Ctrl + A** to select all, then **Ctrl + Enter** to run

At the bottom you'll see the verification output showing row counts for all 5 tables:

```
aircraft   | 30
passengers | 53
flights    | 51
bookings   | 57
crew       | 55
```

---

## Step 4: Browse the data

In the left panel: **emirates** → **Schemas** → **public** → **Tables** — you'll see all 5 tables. Double-click any table → **Data** tab to see the rows.

---

## Important: connection string for QueryMind

When you connect this DB through your QueryMind app, use:

```
postgresql://emirates:emirates123@localhost:5435/emirates
```

And if QueryMind is also running in Docker, use your machine's IP instead of `localhost` — or use `host.docker.internal`:

```
postgresql://emirates:emirates123@host.docker.internal:5432/emirates
```

DB - Description
```
Emirates airline operational database containing 5 tables. 
aircraft table stores the Emirates fleet including A380, B777 and A350 
aircraft with registration numbers, seat configuration and maintenance 
status. passengers table stores customer profiles with Skywards loyalty 
program data including tier levels (Blue, Silver, Gold, Platinum) and 
accumulated miles. flights table contains route information for Emirates 
flights departing from Dubai (DXB) to destinations including London, 
New York, Sydney, Mumbai, Paris, Singapore, Los Angeles and Tokyo with 
scheduling, gate and fare data. bookings table links passengers to flights 
with cabin class (Economy, Business, First), seat numbers, fares paid, 
meal preferences and booking status. crew table stores pilot and cabin 
crew records including captains, first officers, pursers and cabin crew 
with flight hours, license details and salary information.
```


Here are 10 questions from easy to complex:

---

**1. Easy — simple lookup**
"Show me all passengers who are Platinum tier members"

**2. Easy — filter + count**
"How many flights are currently scheduled vs completed?"

**3. Easy — single table sort**
"Which aircraft have not had maintenance since before 2024?"

**4. Medium — aggregation**
"What is the total revenue collected from all completed bookings broken down by cabin class?"

**5. Medium — join two tables**
"Show me all bookings made by Indian passengers with the flight number and fare paid"

**6. Medium — join + filter**
"Which passengers have booked First Class and what are their Skywards tier levels?"

**7. Medium-Hard — aggregation across joins**
"What is the average fare paid per route (origin to destination) for economy class bookings?"

**8. Hard — multi table join**
"For each completed flight, show the flight number, route, total passengers on board, and total revenue collected"

**9. Hard — ranking + joins**
"Who are the top 5 passengers by total amount spent on bookings and how many flights have they taken?"

**10. Very Hard — multi join + business logic**
"For each captain currently assigned to a scheduled flight, show their name, total flight hours, the route they are flying, the number of passengers booked on that flight, and the total revenue that flight is expected to generate"

---
