#!/usr/bin/env bash
# Vérifie: (docs dans les index métier) + (docs dead-letter) == N lignes générées
set -euo pipefail
ES_URL="http://localhost:9200"

PY=""
for candidate in py python3 python; do
  if "$candidate" --version &> /dev/null; then
    PY="$candidate"
    break
  fi
done

count() { curl -s "${ES_URL}/$1/_count" | ${PY} -c "import sys,json;print(json.load(sys.stdin).get('count',0))"; }

TXN=$(count "bank-transactions-txn-*")
AUTH=$(count "bank-transactions-auth-*")
ATM=$(count "bank-transactions-atm-*")
DEAD=$(count "bank-transactions-deadletter-*")

N_TXN=$(wc -l < kits/bank-transactions/logs/transactions.log)
N_AUTH=$(wc -l < kits/bank-transactions/logs/auth.log)
N_ATM=$(tail -n +2 kits/bank-transactions/logs/atm.csv | wc -l)

echo "transactions.log : indexé=${TXN}  lignes_fichier=${N_TXN}"
echo "auth.log         : indexé=${AUTH}  lignes_fichier=${N_AUTH}"
echo "atm.csv           : indexé=${ATM}  lignes_fichier=${N_ATM}"
echo "dead-letter total : ${DEAD}"
echo "---"
echo "Somme indexé (txn+auth+atm) + dead-letter = $((TXN+AUTH+ATM+DEAD))"
echo "Somme lignes générées (hors en-tête csv)   = $((N_TXN+N_AUTH+N_ATM))"
