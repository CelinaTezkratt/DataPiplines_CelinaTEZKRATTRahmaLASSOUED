#!/usr/bin/env bash
# THE one seed command.
# Usage: ./scripts/seed.sh [N]   (N = nombre d'événements, défaut 5000)
set -euo pipefail

ES_URL="http://localhost:9200"
N="${1:-5000}"

# Détecte la bonne commande Python selon l'OS. Sous Windows, "python"/"python3"
# peuvent exister dans le PATH comme alias fantômes du Microsoft Store qui ne
# fonctionnent pas -> on teste une vraie exécution, pas juste command -v.
PY=""
for candidate in py python3 python; do
  if "$candidate" --version &> /dev/null; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "ERREUR: aucun interpréteur Python fonctionnel trouvé (py/python3/python)." >&2
  exit 1
fi
echo "==> Python détecté: ${PY} ($(${PY} --version))"

echo "==> Attente d'Elasticsearch..."
until curl -s "${ES_URL}/_cluster/health" | grep -q '"status":"yellow"\|"status":"green"'; do
  sleep 2
done
echo "==> Elasticsearch prêt."

echo "==> Application des index templates (mappings explicites)..."
for f in elasticsearch/mappings/*.json; do
  name=$(basename "$f" .json)
  echo "    - ${name}"
  curl -s -X PUT "${ES_URL}/_index_template/${name}" \
    -H "Content-Type: application/json" \
    --data-binary @"$f" > /dev/null
done

echo "==> Génération des données (batch=${N}, déterministe)..."
rm -f kits/bank-transactions/logs/*.log kits/bank-transactions/logs/*.csv
${PY} kits/bank-transactions/generator/generate.py --batch "${N}"

echo "==> Lignes générées par source :"
wc -l kits/bank-transactions/logs/transactions.log kits/bank-transactions/logs/auth.log
tail -n +2 kits/bank-transactions/logs/atm.csv | wc -l | xargs echo "atm.csv (hors en-tête):"

echo "==> Terminé. Logstash (déjà démarré via docker compose) va maintenant ingérer ces fichiers."
echo "    Vérifie dans Kibana (http://localhost:5601) ou via:"
echo "    curl -s '${ES_URL}/bank-transactions-*/_count?pretty'"
