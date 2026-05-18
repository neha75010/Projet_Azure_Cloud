# Projet Azure Cloud — Pipeline document asynchrone

Mini-projet Ynov : upload blob → Service Bus → traitement IA → Cosmos DB → notifications SignalR (avec DLQ).

**Groupe :** Jenny Choufack Ngoufo / Neha Mushtaq — voir `AUTHORS.TXT`

## Architecture

```text
React (src/web)
  → FastAPI (src/api)          POST /jobs, SAS upload
  → Blob Storage               input/{jobId}/{fileName}
  → Azure Functions (worker)   Blob trigger → Service Bus → traitement IA
  → Cosmos DB (jobs)           statuts CREATED … PROCESSED / ERROR
  → Azure SignalR              jobUpdate temps réel vers React
```

Détails des statuts et messages JSON : [docs/conventions.md](docs/conventions.md)

## Structure du dépôt

| Dossier | Rôle |
|---------|------|
| `src/api` | API FastAPI — création job, SAS, Cosmos |
| `src/web` | Frontend React — upload + suivi SignalR |
| `src/functions/worker` | Azure Functions — pipeline cloud |
| `docs/azure-setup-etudiant.md` | Création des ressources Azure |
| `.gitlab-ci.yml` | CI/CD (API, Functions, frontend Storage) |

## Prérequis

- Node.js **≥ 20.19** (`src/web/.nvmrc`)
- Python **3.11+**
- Compte Azure avec : Storage, Cosmos, Function App, Service Bus, SignalR, clé OpenAI

---

## Variables d'environnement

### API (`src/api/.env` ou `.env` à la racine)

| Variable | Description |
|----------|-------------|
| `COSMOS_ENDPOINT` | URI du compte Cosmos |
| `COSMOS_KEY` | Clé primaire Cosmos |
| `COSMOS_DATABASE` | Base (défaut : `db-doc`) |
| `COSMOS_CONTAINER` | Conteneur (défaut : `jobs`) |
| `BLOB_CONNECTION_STRING` | Chaîne de connexion Storage |
| `BLOB_CONTAINER` | Conteneur blob (ex. `doc-storage`) |

Modèle : copier [`.env.example`](.env.example) vers `src/api/.env` et remplir les valeurs (portail Azure → Cosmos / Storage).

### Frontend (`src/web/.env.development.local`, optionnel)

| Variable | Description |
|----------|-------------|
| `VITE_FUNCTIONS_PROXY_TARGET` | URL de la Function App **sans** `/api` — proxy Vite pour SignalR en local |
| `VITE_API_URL` | URL de l'API (défaut build prod : App Service ; local : non requis) |
| `VITE_FUNCTIONS_BASE_URL` | Même URL Function App — utilisé au build si pas de proxy (site Storage / Netlify) |

Exemple hybride **React local + Functions cloud** :

```env
VITE_FUNCTIONS_PROXY_TARGET=https://func-doc-pipeline-jn-hnd2ethah8gtcpg8.austriaeast-01.azurewebsites.net
```

### Azure Functions (portail → Function App → Paramètres)

| Variable | Description |
|----------|-------------|
| `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER` | Cosmos |
| `BLOB_CONNECTION_STRING`, `docstorageprof_STORAGE`, `AzureWebJobsStorage` | Storage |
| `SERVICE_BUS_CONNECTION_STRING`, `SERVICE_BUS_QUEUE_NAME` | Queue `document-processing` |
| `SIGNALR_CONNECTION_STRING` | SignalR (mode serverless) |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Tagging IA (`gpt-4o-mini`) |

---

## Lancer l'application en local (démo soutenance)

### 1. API FastAPI

```bash
cd src/api
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Créer src/api/.env à partir de .env.example (clés Azure)
python -m uvicorn app.main:app --reload --port 8000
```

Vérification locale : [http://localhost:8000/health](http://localhost:8000/health) → `{"status":"ok"}`

API déployée (App Service) : [https://api-doc-pipeline-jn-a6h4cug9eeh4ajbp.austriaeast-01.azurewebsites.net/health](https://api-doc-pipeline-jn-a6h4cug9eeh4ajbp.austriaeast-01.azurewebsites.net/health)

### 2. Frontend React

```bash
cd src/web
npm install
npm run dev
```

Ouvrir [http://localhost:5173](http://localhost:5173).

L'API est appelée sur `http://localhost:8000` par défaut (`src/web/src/services/api.js`).

### 3. Workers cloud (recommandé)

Les Functions tournent sur **Azure** (pas besoin de `func start` en local si `.env.development.local` pointe vers la Function App déployée).

Vérifier dans le portail que la Function App est **démarrée** et que les App Settings ci-dessus sont renseignées.

### 4. CORS Storage (obligatoire pour l'upload)

Storage account → **Resource sharing (CORS)** :

- Origines autorisées : `http://localhost:5173`
- Méthodes : `GET`, `PUT`, `OPTIONS`
- En-têtes : `*` (ou au minimum `x-ms-blob-type`, `Content-Type`)

---

## Scénario de démo

1. Sélectionner un **PDF normal** → Initier & uploader → suivre les statuts : `CREATED` → `UPLOADED` → `QUEUED` → `PROCESSING` → `PROCESSED` (+ tags).
2. Sélectionner **`crash.pdf`** (nouveau job) → après plusieurs échecs Service Bus → statut **`ERROR`** (DLQ, message dans Cosmos).

Fichier `crash.pdf` : simule un échec de traitement côté worker (voir `src/functions/worker/function_app.py`).

---

## Déploiement 100 % Azure (sans Static Web App)

| Composant | Ressource | URL / cible |
|-----------|-----------|-------------|
| API | App Service `api-doc-pipeline-jn-a6h4cug9eeh4ajbp` | https://api-doc-pipeline-jn-a6h4cug9eeh4ajbp.austriaeast-01.azurewebsites.net |
| Workers | Function App `func-doc-pipeline-jn-hnd2ethah8gtcpg8` | https://func-doc-pipeline-jn-hnd2ethah8gtcpg8.austriaeast-01.azurewebsites.net |
| React | Storage `stdocpipelinejn` → conteneur `$web` | `https://stdocpipelinejn.zXX.web.core.windows.net` (portail → Site web statique) |
| Données | Cosmos `db-doc` / `jobs`, Blob `doc-storage` | — |

### 1. API (déjà en ligne)

Vérifier : `/health` → `{"status":"ok"}`. Déploiement : zip `src/api` → App Service (voir `api.zip`).

### 2. Functions

Portail → Function App → variables d’environnement (Cosmos, Storage, Service Bus, SignalR, OpenAI) → zip `src/functions/worker`.

### 3. React sur Storage

```bash
cd src/web
export VITE_API_URL="https://api-doc-pipeline-jn-a6h4cug9eeh4ajbp.austriaeast-01.azurewebsites.net"
export VITE_FUNCTIONS_BASE_URL="https://func-doc-pipeline-jn-hnd2ethah8gtcpg8.austriaeast-01.azurewebsites.net"
npm run build
```

Storage `stdocpipelinejn` → **Site web statique** activé (index + 404 = `index.html`) → conteneur **`$web`** → téléverser tout `dist/`.

### 4. CORS (obligatoire pour le site `$web`)

- **Storage** → CORS : origine = URL du site statique (+ `http://localhost:5173` en secours).
- **Function App** → CORS : même URL du site statique.

**Static Web App** : souvent bloquée sur Azure for Students — non utilisée ici.

---

## CI/CD GitLab

Pipeline sur branche `main` : build React, déploiement API (App Service), Functions (zip), frontend (Storage `$web`).

Variables à configurer dans GitLab → Settings → CI/CD : voir les commentaires en tête de [`.gitlab-ci.yml`](.gitlab-ci.yml).

---

## Modèle Cosmos (document job)

Champs principaux : `id` (jobId), `status`, `blobName`, `tags`, `size`, `uploadedAt`, `processedAt`, `errorMessage`, `errorAt`.  
Partition key : `/pk` = `"JOB"`.

Statuts : voir [docs/conventions.md](docs/conventions.md).

---

## Documentation complémentaire

- [docs/azure-setup-etudiant.md](docs/azure-setup-etudiant.md) — création ressources Azure
- [mini_projet_azure_pipeline.md](mini_projet_azure_pipeline.md) — sujet et barème
- [docs/conventions.md](docs/conventions.md) — chemins blob, JSON Service Bus / SignalR

## Dépannage rapide

| Problème | Piste |
|----------|--------|
| Upload blob bloqué (CORS) | CORS Storage : origine = URL site `$web` (et `http://localhost:5173` si local) |
| Pas de statuts SignalR | Build avec `VITE_FUNCTIONS_BASE_URL` + CORS Function App (URL site `$web`) |
| API 500 à la création job | Vérifier `src/api/.env` (Cosmos + Storage) |
| Statut reste sur CREATED | Functions cloud arrêtées ou mauvais `BLOB_CONNECTION_STRING` |
| `crash.pdf` ne passe pas en ERROR | Nouveau job (nouveau fichier / nouvel upload), queue DLQ configurée |

**Contact enseignant :** vincent.leclerc@ynov.com
