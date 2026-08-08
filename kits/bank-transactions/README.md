# Kit: Bank Transactions — "Meridian Pay"

You are the new data team of **Meridian Pay**, a card-payment processor. Three
systems log independently: the transaction engine, the customer authentication
service, and the ATM network. Compliance wants visibility *yesterday*.

Nobody documented the log formats. Below is what the systems actually emit —
reverse-engineering them is your job. The generator (`generator/generate.py`)
produces all three sources into `logs/`. Around 2 % of lines are garbage:
**account for every line**.

## Sources (by example — that's all you get)

**1. Transaction engine** — `logs/transactions.log` (one event per line, key=value)

```
ts=2026-07-26T00:00:07Z ev=txn id=t-8100452 amount=59.90 currency=EUR country=FR card_present=true merchant=m-1042 status=approved
ts=2026-07-26T00:01:33Z ev=txn id=t-8100453 amount=980.00 currency=USD country=US card_present=false merchant=m-0077 status=declined reason=insufficient_funds
```

**2. Authentication service** — `logs/auth.log` (JSON lines)

```
{"ts": "2026-07-26T00:00:05Z", "event": "auth", "user": "u-19204", "channel": "mobile", "result": "success", "ip": "83.112.4.19"}
```

**3. ATM network (nightly export)** — `logs/atm.csv`

```
ts,atm_id,city,op,amount,result
2026-07-26T00:02:11Z,atm-0140,Lille,withdrawal,60.00,ok
```

## Generator

```bash
python3 generator/generate.py --batch 5000   # 5000 events then exit (deterministic)
python3 generator/generate.py                # continuous mode (~20 events/s)
```

## The 8 questions your dashboard must answer

1. Transaction volume (count) and value (sum) over time, by currency?
2. What is the approval rate (approved vs declined) over time?
3. Top 10 merchants by transaction value?
4. What are the top decline reasons?
5. Card-present vs card-not-present split, per country?
6. Which cities' ATMs dispense the most cash, and what is the ATM error rate?
7. **At some point, something that looks like a fraud attack happened. When, from which country, and what is its signature?**
8. What share of lines were unparseable (dead-letter) today?

## The alert

Raise an alert when **more than 20 declined card-not-present transactions occur
within 5 minutes**. Action: write to an `alerts` index. You must demonstrate it
firing (the generator's data will give you the opportunity — see question 7).

## Suggested enrichment

`auth.log` carries client IPs — a geoip map of authentication failures next to
question 7's answer tells a compelling story. Amounts must be numbers: finance
people notice when `sum` concatenates strings.
