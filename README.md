# Team <nom> — Kit: Bank Transactions ("Meridian Pay")

## 1. Architecture

```
generator (Python, fourni)
        │  écrit
        ▼
kits/bank-transactions/logs/{transactions.log, auth.log, atm.csv}
        │  lus par Logstash (file input)
        ▼
Logstash  ── parse (kv / json / csv) ── type ── enrichit (geoip) ── route
        │                                                    │
        ▼ (lignes valides)                                   ▼ (lignes malformées)
Elasticsearch                                        Elasticsearch
  bank-transactions-txn-*                               bank-transactions-deadletter-*
  bank-transactions-auth-*
  bank-transactions-atm-*
        │
        ▼
Kibana — dashboard (8 questions) + règle d'alerte → bank-transactions-alerts-*
```

*(remplace ce schéma ASCII par une vraie image si tu veux, ex. excalidraw/draw.io exportée en PNG dans `docs/architecture.png`)*

## 2. Comment lancer le projet (2 commandes max)

```bash
docker compose up -d
./scripts/seed.sh 5000        # applique les mappings + génère 5000 événements déterministes
```

Vérifier que tout est monté :
```bash
curl -s http://localhost:9200/_cat/indices/bank-transactions-*?v
```

Kibana : http://localhost:5601

Pour rejouer une anomalie en direct pendant la démo (mode continu, ~20 ev/s) :
```bash
python3 kits/bank-transactions/generator/generate.py
```
(laisser tourner ~1000 événements pour retraverser la fenêtre d'anomalie, `Ctrl-C` pour arrêter)

## 3. Choix & compromis

> À compléter au fur et à mesure de votre travail — c'est la section où se cachent
> le plus de points. Quelques pistes déjà tranchées dans ce squelette, à
> documenter/justifier avec vos propres mots :

- **`kv` plutôt que `grok`** pour `transactions.log` : le format `clé=valeur`
  s'y prête nativement, plus lisible et plus robuste aux réordonnancements de
  champs qu'un grok pattern positionnel.
- **Détection de dead-letter explicite** plutôt que de se fier uniquement aux
  tags `_grokparsefailure`/`_jsonparsefailure` : `kv` ne "plante" jamais, il
  faut donc vérifier nous-mêmes la présence des champs obligatoires.
- **`dynamic: strict`** sur les index métier : toute dérive de schéma fait
  échouer l'indexation plutôt que de la laisser passer silencieusement.
- **Sécurité X-Pack désactivée** : simplifie la reproduction sur une machine
  de cours ; à mentionner comme trade-off assumé (pas de prod réelle).
- **`sincedb_path => /dev/null`** : permet de rejouer les fichiers à chaque
  redémarrage de Logstash, pratique pour la démo déterministe ; en
  "vraie" prod on utiliserait un sincedb persistant.
- Seuil d'alerte : 20 déclins CNP en 5 min (imposé par l'énoncé) — noter la
  fenêtre Kibana Alerting choisie (`check every` vs `look back window`) et
  pourquoi.

## 4. Réponses aux 8 questions (mapping question → panel du dashboard)

| # | Question | Panel Kibana | Index / champs clés |
|---|----------|--------------|----------------------|
| 1 | Volume & valeur par devise dans le temps | ... | `bank-transactions-txn-*` : `amount`, `currency`, `@timestamp` |
| 2 | Taux d'approbation dans le temps | ... | `status` |
| 3 | Top 10 marchands par valeur | ... | `merchant`, `amount` |
| 4 | Top motifs de refus | ... | `reason` |
| 5 | Card-present vs CNP par pays | ... | `card_present`, `country_code` |
| 6 | Villes ATM / taux d'erreur | ... | `bank-transactions-atm-*` : `city`, `result` |
| 7 | Signature de l'attaque fraude | ... | `txn` + `auth` (geoip) croisés |
| 8 | Part de lignes dead-letter | ... | ratio `deadletter` / total |

*(remplace `...` par le nom réel du panel une fois le dashboard construit)*

## 5. Alerte

- **Type** : Kibana Alerting — règle "Elasticsearch query" (threshold).
- **Condition** : nombre de documents `bank-transactions-txn-*` où
  `status: declined AND card_present: false` > 20 sur une fenêtre glissante
  de 5 minutes.
- **Action** : connecteur "Index" → écrit dans `bank-transactions-alerts-*`.
- **Preuve de déclenchement** : capture d'écran dans `docs/alert-firing.png`
  + démonstration live à la soutenance (relancer le générateur en continu
  jusqu'à retraverser la fenêtre d'anomalie ~55–70% du batch).

## 6. Structure du dépôt

```
team-<nom>/
├── docker-compose.yml
├── README.md
├── kits/bank-transactions/{generator/generate.py, logs/, README.md}
├── logstash/pipeline/bank-transactions.conf
├── logstash/config/logstash.yml
├── elasticsearch/mappings/*.json     # index templates
├── kibana/dashboard.ndjson           # à exporter une fois le dashboard fini
└── scripts/seed.sh                   # LA commande de seed
```

## 7. Checklist avant rendu

- [ ] `docker compose up -d` + `scripts/seed.sh` sur une machine vierge → tout fonctionne
- [ ] `(docs indexés) + (docs dead-letter) = N` vérifié pour un batch donné
- [ ] mappings explicites confirmés via `GET <index>/_mapping`
- [ ] dashboard `.ndjson` s'importe proprement et répond aux 8 questions
- [ ] alerte démontrée (capture + live)
- [ ] section "choix & compromis" rédigée avec nos vraies décisions
