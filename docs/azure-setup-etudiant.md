# Guide Azure — compte étudiant depuis zéro

Guide pour le binôme **Jenny Choufack Ngoufo / Neha Mushtaq**.  
À faire sur [https://portal.azure.com](https://portal.azure.com) avec votre abonnement **Azure for Students**.

---

## Avant de commencer

### Activer l’abonnement étudiant

1. Aller sur [https://azure.microsoft.com/free/students](https://azure.microsoft.com/free/students)
2. Se connecter avec votre mail étudiant
3. Vérifier dans le portail : **Abonnements** → un abonnement actif (ex. *Azure for Students*)

### Convention de noms (à adapter une seule fois)

Remplacez `jn` par vos initiales (ex. `jn` = Jenny + Neha) :

| Ressource | Nom suggéré |
|-----------|-------------|
| Resource group | `rg-doc-pipeline-jn` |
| Storage account | `stdocpipelinejn` (3–24 car., minuscules, chiffres seuls) |
| Cosmos DB account | `cosmos-doc-jn` |
| Function App | `func-doc-pipeline-jn` |
| App Service (API) | `api-doc-pipeline-jn` |
| Static Web App | `swa-doc-pipeline-jn` |
| Service Bus namespace | `sb-doc-pipeline-jn` |
| SignalR | `signalr-doc-jn` |
| Azure OpenAI | `openai-doc-jn` |

**Région recommandée** : `France Central` ou `West Europe` (la même partout).

---

## Étape 1 — Resource group

1. Portail → **Créer une ressource**
2. Chercher **Groupes de ressources** → **Créer**
3. Nom : `rg-doc-pipeline-jn`
4. Région : `France Central`
5. **Créer**

---

## Étape 2 — Storage Account (fichiers uploadés)

1. **Créer une ressource** → **Compte de stockage** → **Créer**
2. Paramètres :
   - Abonnement : votre abonnement étudiant
   - Resource group : `rg-doc-pipeline-jn`
   - Nom : `stdocpipelinejn`
   - Région : `France Central`
   - Performance : **Standard**
   - Redondance : **LRS** (le moins cher)
3. **Vérifier + créer**

### Container blob

1. Ouvrir le compte de stockage → **Conteneurs** → **+ Conteneur**
2. Nom : **`doc-storage`** (obligatoire — utilisé par vos Functions)
3. Niveau d’accès public : **Privé**

### CORS blob (obligatoire pour React en local)

Sans cela, l’upload direct avec l’URL SAS échoue depuis `http://localhost:5173` (*blocked by CORS policy*).

1. Compte de stockage `stdocpipelinejn` → menu gauche **Paramètres** → **Resource sharing (CORS)** / **Partage de ressources (CORS)**
2. Onglet **Service Blob**
3. **+ Ajouter** une règle :

| Champ | Valeur |
|-------|--------|
| Origines autorisées | `http://localhost:5173,http://127.0.0.1:5173` |
| Méthodes autorisées | `PUT,GET,OPTIONS,HEAD` |
| En-têtes autorisés | `*` |
| En-têtes exposés | `*` |
| Durée max (secondes) | `3600` |

4. **Enregistrer**

Attendre ~1 minute, puis réessayer l’upload dans React.

### Récupérer la connection string

1. Storage account → **Clés d’accès**
2. Copier **Chaîne de connexion** (key1)

→ Pour `.env` :

```env
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
BLOB_CONTAINER=doc-storage
```

---

## Étape 3 — Cosmos DB (statuts des jobs)

1. **Créer une ressource** → **Azure Cosmos DB** → **Créer**
2. Choisir **Azure Cosmos DB for NoSQL** (API Core SQL)
3. Paramètres :
   - Resource group : `rg-doc-pipeline-jn`
   - Nom du compte : `cosmos-doc-jn`
   - Capacity mode : **Provisioned throughput** ou **Serverless** (serverless = plus simple étudiant)
   - Région : `France Central`
4. **Vérifier + créer** (attendre 2–5 min)

### Base et container

1. Cosmos account → **Explorateur de données** → **Nouvelle base de données**
   - ID : `db-doc`
   - Throughput : 400 RU/s (ou serverless si choisi)
2. Ouvrir `db-doc` → **Nouveau conteneur**
   - ID conteneur : `jobs`
   - Clé de partition : `/pk`
   - Throughput : partagé avec la DB

### Récupérer les clés

1. Cosmos account → **Clés**
2. Copier **URI** et **PRIMARY KEY**

→ Pour `.env` :

```env
COSMOS_ENDPOINT=https://cosmos-doc-jn.documents.azure.com:443/
COSMOS_KEY=<primary-key>
COSMOS_DATABASE=db-doc
COSMOS_CONTAINER=jobs
```

---

## Étape 4 — Function App (pipeline blob / Service Bus / DLQ)

1. **Créer une ressource** → **Function App** → **Créer**
2. Paramètres :
   - Resource group : `rg-doc-pipeline-jn`
   - Nom : `func-doc-pipeline-jn`
   - Pile : **Python**
   - Version : **3.12**
   - Région : `France Central`
   - Plan : **Consumption (Serverless)**
   - Storage : sélectionner `stdocpipelinejn` (créé à l’étape 2)
3. **Vérifier + créer**

### Lier le Storage pour le blob trigger

1. Function App → **Variables d’environnement** (Configuration)
2. **+ Nouvelle paramètre d’application** :

| Nom | Valeur |
|-----|--------|
| `docstorageprof_STORAGE` | *même chaîne que BLOB_CONNECTION_STRING* |
| `COSMOS_ENDPOINT` | URI Cosmos |
| `COSMOS_KEY` | clé Cosmos |
| `COSMOS_DATABASE` | `db-doc` |
| `COSMOS_CONTAINER` | `jobs` |

(Vous ajouterez Service Bus, SignalR et OpenAI aux étapes 7–9.)

3. **Enregistrer** puis **Redémarrer** l’app

### Fichier local pour développer

```bash
cd src/functions/worker
cp local.settings.json.example local.settings.json
# Remplir les valeurs (ne pas commiter local.settings.json)
```

### Azure Functions Core Tools (`func`)

Installation (Mac) :

```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
func --version
```

Avant le premier `func start`, télécharger le bundle d’extensions (une fois, avec Internet) :

```bash
cd src/functions/worker
func bundles download
```

Puis :

```bash
source .venv/bin/activate
func start
```

> Ne pas faire `export local.settings.json` — ce fichier est lu automatiquement par `func start`.

**Erreur `Connection refused (127.0.0.1:10000)`** : `AzureWebJobsStorage` vaut encore `UseDevelopmentStorage=true` (émulateur Azurite non lancé). Mettre la **vraie** connection string Azure Storage (la même que `docstorageprof_STORAGE`), pas `UseDevelopmentStorage=true`.

---

## Étape 5 — App Service pour l’API FastAPI (option cloud)

Pour la soutenance, l’API peut tourner **en local** (`uvicorn`) au début. Pour la mettre en ligne :

1. **Créer une ressource** → **Application Web** → **Créer**
2. Paramètres :
   - Resource group : `rg-doc-pipeline-jn`
   - Nom : `api-doc-pipeline-jn`
   - Publier : **Code**
   - Runtime : **Python 3.12**
   - OS : **Linux**
   - Plan : **Basic B1** (ou Free F1 si disponible — limité)
3. **Créer**

### Variables sur l’App Service

Application Web → **Paramètres** → **Variables d’environnement** :

- `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER`
- `BLOB_CONNECTION_STRING`, `BLOB_CONTAINER`

### CORS (pour React)

Application Web → **CORS** → ajouter l’URL de votre Static Web App (étape 6) et `http://localhost:5173`.

### Déploiement API (simplifié sans Docker)

```bash
cd src/api
pip install -r requirements.txt   # créer requirements.txt si besoin
# Déployer via VS Code extension "Azure App Service" ou zip deploy
```

Mettre à jour `src/web/src/services/api.js` :

```javascript
baseURL: "https://api-doc-pipeline-jn.azurewebsites.net",
```

---

## Étape 6 — Static Web App (React en ligne) — optionnel au début

1. **Créer une ressource** → **Static Web App**
2. Resource group : `rg-doc-pipeline-jn`
3. Nom : `swa-doc-pipeline-jn`
4. Plan : **Free**
5. Source : GitHub → lier votre dépôt, branche `main`, app location `src/web`, output `dist`

En local sans SWA :

```bash
cd src/web
npm install
npm run dev
```

Et dans `api.js` : `baseURL: "http://localhost:8000"` le temps du dev.

---

## Étape 7 — Service Bus (NOUVEAU — mini-projet)

1. **Créer une ressource** → **Service Bus** → **Créer**
2. Paramètres :
   - Resource group : `rg-doc-pipeline-jn`
   - Namespace : `sb-doc-pipeline-jn`
   - Tarif : **Basic**
   - Région : `France Central`
3. **Créer**

### Queue

1. Ouvrir le namespace → **Files d’attente** → **+ File d’attente**
2. Nom : `document-processing`
3. Ouvrir la queue → **Paramètres partagés** :
   - **Nombre maximal de livraisons** : `3`

La **DLQ** est automatique : messages en échec → sous-queue `$deadletterqueue`.

### Connection string

Namespace → **Stratégies d’accès partagé** → `RootManageSharedAccessKey` → copier **Primary Connection String**

→ Function App → variable :

```text
SERVICE_BUS_CONNECTION_STRING=Endpoint=sb://...
SERVICE_BUS_QUEUE_NAME=document-processing
```

---

## Étape 8 — SignalR (NOUVEAU — notifications)

1. **Créer une ressource** → **SignalR Service**
2. Resource group : `rg-doc-pipeline-jn`
3. Nom : `signalr-doc-jn`
4. Tarif : **Free_F1** (si dispo) ou **Standard_S1**
5. Mode de service : **Serverless** (important pour Azure Functions)
6. **Créer**

### Connection string

SignalR → **Paramètres** → **Clés** → **Chaîne de connexion primaire**

→ Function App :

```text
SIGNALR_CONNECTION_STRING=Endpoint=https://...
```

---

## Étape 9 — Tagging IA avec OpenAI API (choix du projet)

**Aucune ressource Azure OpenAI / Foundry / Grok à créer.**  
Le tagging utilise l’API publique OpenAI depuis les Azure Functions.

### 1. Créer la clé API

1. [https://platform.openai.com](https://platform.openai.com) → compte (mail + vérification ; carte ou crédits selon offre).
2. [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) → **Create secret key**.
3. Copier la clé `sk-...` (visible une seule fois). **Ne jamais la commiter.**

### 2. Configurer les Functions

Copier le modèle :

```bash
cd src/functions/worker
cp local.settings.json.example local.settings.json
```

Remplir dans `local.settings.json` (section `Values`) :

```json
"OPENAI_API_KEY": "sk-...",
"OPENAI_MODEL": "gpt-4o-mini"
```

Sur la **Function App** (portail) → **Variables d’environnement** : les mêmes noms.

### 3. Comportement dans le code

Le module `shared/tagging.py` :

- appelle `https://api.openai.com/v1/chat/completions` avec le prompt du sujet ;
- en cas d’échec (clé absente, quota, erreur réseau) → **tags par règles** sur le nom de fichier (`cv`, `pdf`, `azure`, etc.).

### 4. Coût et sécurité

- Modèle `gpt-4o-mini` : quelques centimes pour une démo (peu d’appels).
- Limiter les tests en boucle.
- Régénérer la clé sur OpenAI si elle a été exposée.

### 5. Tester le tagging en local (optionnel)

```bash
cd src/functions/worker
source .venv/bin/activate   # créer le venv si besoin, comme pour l’API
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python -c "from shared.tagging import generate_tags; print(generate_tags('cv_amine_azure.pdf'))"
```

---

## Étape 10 — Fichier `.env` local (API)

```bash
cd src/api
cp ../../.env.example .env
```

Remplir avec toutes les valeurs des étapes 2–3. Exemple complet :

```env
COSMOS_ENDPOINT=https://cosmos-doc-jn.documents.azure.com:443/
COSMOS_KEY=...
COSMOS_DATABASE=db-doc
COSMOS_CONTAINER=jobs

BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
BLOB_CONTAINER=doc-storage
```

Tester :

```bash
# macOS (Homebrew) : utiliser un venv — pip3 global est bloqué (PEP 668)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

> Ne pas utiliser `pip3 install` sans venv sur Mac : erreur `externally-managed-environment`.

- `GET http://localhost:8000/health` → `{"status":"ok"}`
- Créer un job via React ou Postman → vérifier l’item dans Cosmos **Explorateur de données**

---

## Étape 11 — Vérifier le blob trigger

1. Créer un job via l’API (statut `CREATED`)
2. Uploader un fichier avec l’URL SAS (React)
3. Portail → Storage → `doc-storage` → vous devez voir `input/<uuid>/<fichier>`
4. Function App → **Surveillance** → **Flux de journaux** : le trigger doit loguer le blob

Chemin attendu par le code : container `doc-storage`, préfixe `input/`.

---

## Checklist finale

| # | Ressource | Créé | Connection string / clé notée |
|---|-----------|------|-------------------------------|
| 1 | Resource group | ☐ | — |
| 2 | Storage + container `doc-storage` | ☐ | ☐ |
| 3 | Cosmos `db-doc` / `jobs` | ☐ | ☐ |
| 4 | Function App Python 3.12 | ☐ | ☐ |
| 5 | App Service API (optionnel) | ☐ | ☐ |
| 6 | Static Web App (optionnel) | ☐ | ☐ |
| 7 | Service Bus + queue | ☐ | ☐ |
| 8 | SignalR Serverless | ☐ | ☐ |
| 9 | Azure OpenAI ou OpenAI API | ☐ | ☐ |
| 10 | `.env` local API testé | ☐ | — |
| 11 | Upload blob → logs Function | ☐ | — |

---

## Ordre recommandé (2 jours)

| Jour | Actions |
|------|---------|
| **Jour 1 matin** | Étapes 1–4 + `.env` + test API + upload blob |
| **Jour 1 après-midi** | Étapes 7–9 (Service Bus, SignalR, OpenAI) + variables Function |
| **Jour 2** | Coder les 3 Functions + React SignalR + tests DLQ |
| **Veille soutenance** | Déploiement + démo complète |

---

## Coûts étudiants (ordre de grandeur)

- Storage, Cosmos serverless, Functions Consumption, Service Bus Basic, SignalR Free : **faible** si vous supprimez le resource group après le projet
- App Service B1 + OpenAI : **le plus coûteux** → API en local possible pour économiser

**Après le projet** : supprimer `rg-doc-pipeline-jn` pour arrêter la facturation.

---

## Problèmes fréquents

### `RequestDisallowedByAzure` / `InvalidTemplateDeployment` (Static Web App)

Message typique : *« policy maintains a set of best available regions »*.

**Cause** : l’abonnement **Azure for Students** n’autorise pas toutes les régions pour certains services (souvent Static Web App).

**Solutions** :

1. **Ignorer Static Web App pour l’instant** (recommandé) — le sujet ne l’exige pas pour le pipeline IA / Service Bus. En local :
   ```bash
   cd src/web && npm install && npm run dev
   ```
   Dans `src/web/src/services/api.js` : `baseURL: "http://localhost:8000"`.

2. **Recréer la SWA dans une autre région** : à la création, essayer dans l’ordre :
   - `West Europe`
   - `North Europe`
   - `East US`
   - `West US 2`  
   (éviter une région non listée si le portail la grise.)

3. **Voir les régions autorisées** : Portail → **Abonnements** → votre abonnement → **Ressources** → créer une ressource simple (ex. Storage) et noter quelles régions sont **sélectionnables** — utiliser la même pour la SWA.

4. **Aucune région ne fonctionne** (fréquent sur Azure for Students) : **abandonner Static Web App**. Ce service est souvent **indisponible** sur les abonnements étudiants, même en changeant de région (Austria East, West Europe, etc.). Ce n’est pas bloquant pour le mini-projet.

5. **Alternatives pour héberger React** (optionnel, après la soutenance) :
   - `npm run dev` en local pendant la démo
   - **GitHub Pages** / Vercel / Netlify (gratuit)
   - **Storage static website** : activer « site web statique » sur le compte Storage existant

4bis. Contacter le support Azure étudiant uniquement si vous avez absolument besoin d’une SWA Azure (rare pour ce TP).

| Problème | Solution |
|----------|----------|
| Blob trigger ne part pas | Vérifier `docstorageprof_STORAGE` et container `doc-storage` |
| Cosmos 404 | Partition key `/pk`, valeur `"JOB"` dans les documents |
| OpenAI refusé | Utiliser clé OpenAI externe + fallback règles dans le code |
| React n’appelle pas l’API | CORS sur App Service + bon `baseURL` dans `api.js` |
| Upload blob : *CORS policy* depuis localhost | CORS sur le **compte Storage** (service Blob), pas seulement l’API — voir étape 2 |
| `func start` : *Unable to download extension bundle* | Wi‑Fi actif puis `func bundles download` dans `src/functions/worker` |
| Nom storage déjà pris | Changer le suffixe (`stdocpipelinejn2`) |

---

## Aide

- Enseignant : vincent.leclerc@ynov.com
- Conventions projet : [conventions.md](./conventions.md)
