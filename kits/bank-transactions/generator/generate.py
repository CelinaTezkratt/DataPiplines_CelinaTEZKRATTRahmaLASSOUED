#!/usr/bin/env python3
"""Meridian Pay log generator (final project kit: bank-transactions).

Usage:
    python3 generate.py --batch 5000    # deterministic batch, then exit
    python3 generate.py                 # continuous (~20 events/s), Ctrl-C to stop

Writes logs/transactions.log, logs/auth.log, logs/atm.csv.
~2% of lines are malformed. Do not edit.
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone

SEED = 20260726
BASE = datetime(2026, 7, 26, 0, 0, 0, tzinfo=timezone.utc)
CURRENCIES = ["EUR", "EUR", "EUR", "USD", "GBP"]
COUNTRIES = ["FR", "FR", "DE", "ES", "IT", "GB", "US", "BE"]
CITIES = ["Lille", "Lyon", "Paris", "Nantes", "Bordeaux", "Marseille"]
REASONS = ["insufficient_funds", "expired_card", "suspected_fraud", "wrong_pin"]
CHANNELS = ["mobile", "web", "branch"]

# The anomaly: a burst of declined card-not-present transactions from one
# country, with matching auth failures from a narrow IP range.
FRAUD_COUNTRY = "US"
ANOMALY_WINDOW = (0.55, 0.70)  # fraction of the batch


def mangle(rng, line):
    cut = rng.randint(5, max(6, len(line) - 10))
    return line[:cut] if rng.random() < 0.7 else line.replace("=", "", 2)[:cut]


def emit(rng, t, frac, txn, auth, atm, counter):
    iso = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    in_fraud = ANOMALY_WINDOW[0] <= frac <= ANOMALY_WINDOW[1]

    fraud_txn = in_fraud and rng.random() < 0.45
    if fraud_txn:
        amount = round(rng.uniform(500, 2500), 2)
        country, present, status = FRAUD_COUNTRY, "false", "declined"
        reason = " reason=suspected_fraud"
        currency = "USD"
    else:
        amount = round(10 ** rng.uniform(0.5, 3.2), 2)
        country = rng.choice(COUNTRIES)
        present = "true" if rng.random() < 0.65 else "false"
        declined = rng.random() < 0.08
        status = "declined" if declined else "approved"
        reason = f" reason={rng.choice(REASONS)}" if declined else ""
        currency = rng.choice(CURRENCIES)
    line = (f"ts={iso} ev=txn id=t-{8100000 + counter} amount={amount} "
            f"currency={currency} country={country} card_present={present} "
            f"merchant=m-{rng.randint(1, 400):04d} status={status}{reason}")
    if rng.random() < 0.02:
        line = mangle(rng, line)
    txn.write(line + "\n")

    if rng.random() < 0.6:
        fraud_auth = in_fraud and rng.random() < 0.5
        doc = {"ts": iso, "event": "auth", "user": f"u-{rng.randint(1, 40000):05d}",
               "channel": "web" if fraud_auth else rng.choice(CHANNELS),
               "result": "failure" if (fraud_auth or rng.random() < 0.05) else "success",
               "ip": (f"181.214.{rng.randint(200, 210)}.{rng.randint(1, 254)}" if fraud_auth
                      else f"{rng.randint(1, 223)}.{rng.randint(0, 255)}."
                           f"{rng.randint(0, 255)}.{rng.randint(1, 254)}")}
        aline = json.dumps(doc)
        if rng.random() < 0.02:
            aline = mangle(rng, aline)
        auth.write(aline + "\n")

    if rng.random() < 0.15:
        op = rng.choice(["withdrawal", "withdrawal", "deposit", "balance"])
        amt = f"{rng.choice([20, 40, 60, 100, 200]):.2f}" if op != "balance" else "0.00"
        result = "ok" if rng.random() < 0.93 else rng.choice(["timeout", "out_of_cash"])
        atm.write(f"{iso},atm-{rng.randint(1, 300):04d},{rng.choice(CITIES)},"
                  f"{op},{amt},{result}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, help="emit N transaction events, then exit")
    args = ap.parse_args()
    rng = random.Random(SEED)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(out, exist_ok=True)

    txn = open(os.path.join(out, "transactions.log"), "a")
    auth = open(os.path.join(out, "auth.log"), "a")
    atm_path = os.path.join(out, "atm.csv")
    new_csv = not os.path.exists(atm_path) or os.path.getsize(atm_path) == 0
    atm = open(atm_path, "a")
    if new_csv:
        atm.write("ts,atm_id,city,op,amount,result\n")
    try:
        if args.batch:
            t = BASE
            for i in range(args.batch):
                t += timedelta(seconds=rng.expovariate(20))
                emit(rng, t, i / args.batch, txn, auth, atm, i)
        else:
            i = 0
            while True:
                emit(rng, datetime.now(timezone.utc), (i % 1000) / 1000,
                     txn, auth, atm, i)
                txn.flush(); auth.flush(); atm.flush()
                time.sleep(0.05)
                i += 1
    except KeyboardInterrupt:
        pass
    finally:
        txn.close(); auth.close(); atm.close()
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
