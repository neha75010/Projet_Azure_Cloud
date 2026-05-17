# Projet Azure Cloud — Pipeline document asynchrone

Mini-projet : upload blob → Service Bus → traitement IA → notifications SignalR.

## Structure

- `src/api` — FastAPI (création job, Cosmos, SAS blob)
- `src/web` — React (upload)
- `src/functions/worker` — Azure Functions (pipeline à compléter)
- `docs/conventions.md` — conventions blob, statuts, messages JSON
- `AUTHORS.TXT` — membres du groupe (rendu SVN)

## Démarrage API en local

### 1. Comptes et accès Azure

Vous devez utiliser les ressources Azure déjà fournies en cours (pas de nouveau compte obligatoire si l’enseignant vous a donné un accès) :

1. Ouvrir [https://portal.azure.com](https://portal.azure.com)
2. Se connecter avec le compte **Microsoft / Ynov** utilisé pour le module cloud
3. Sélectionner la **subscription** et le **resource group** du projet

Si vous n’avez pas accès au portail, demander à l’enseignant (Vincent Leclerc) les droits sur le resource group ou les chaînes de connexion Cosmos / Storage.

### 2. Récupérer les secrets (portail Azure)

| Variable | Où la trouver |
|----------|----------------|
| `COSMOS_ENDPOINT` | Cosmos DB → votre compte → **URI** |
| `COSMOS_KEY` | Cosmos DB → **Keys** → Primary Key |
| `BLOB_CONNECTION_STRING` | Storage account → **Access keys** → Connection string |
| `BLOB_CONTAINER` | Storage account → **Containers** (ex. `doc-storage`) |

### 3. Configurer l’API

```bash
cd src/api
cp ../../.env.example .env
# Éditer .env avec les valeurs du portail
pip install fastapi uvicorn azure-cosmos pydantic-settings python-dotenv azure-storage-blob
python -m uvicorn app.main:app --reload
```

Tester : `GET http://localhost:8000/health` puis `POST http://localhost:8000/jobs` avec `{"fileName":"test.pdf"}`.

### 4. Frontend (inchangé)

```bash
cd src/web
npm install
npm run dev
```

## Modèle Cosmos (étape 1)

Chaque job contient : `status`, `blobName`, `tags`, `size`, `uploadedAt`, `processedAt`, `errorMessage`, `errorAt`.

Statut initial à la création : `CREATED`.

## Compte étudiant depuis zéro

Guide pas à pas (portail Azure, noms, clés, checklist) :

**[docs/azure-setup-etudiant.md](docs/azure-setup-etudiant.md)**

## Prochaines étapes

- Créer Service Bus + queue dans Azure
- Compléter les Azure Functions (voir `docs/conventions.md`)
