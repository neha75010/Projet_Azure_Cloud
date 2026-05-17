# Conventions du projet (étape 0)

## Identifiants

- `jobId` dans l'API FastAPI et React = `documentId` dans Service Bus, SignalR et le sujet du mini-projet.

## Chemin blob (option A — conservée)

```
input/{jobId}/{fileName}
```

Exemple : `input/550e8400-e29b-41d4-a716-446655440000/cv_amine.pdf`

Parsing côté Function :

- `documentId` = premier segment après `input/`
- `fileName` = reste du chemin

## Machine à états

```
CREATED → UPLOADED → QUEUED → PROCESSING → PROCESSED
                              ↘ ERROR
```

| Statut      | Composant              |
|-------------|------------------------|
| CREATED     | FastAPI `POST /jobs`   |
| UPLOADED    | Function Blob Trigger  |
| QUEUED      | Function Blob Trigger  |
| PROCESSING  | Function Service Bus   |
| PROCESSED   | Function Service Bus   |
| ERROR       | Function DLQ / traitement |

## Message Service Bus

```json
{
  "documentId": "<uuid>",
  "fileName": "cv_amine.pdf",
  "blobName": "input/<uuid>/cv_amine.pdf",
  "size": 248392,
  "uploadedAt": "2026-05-16T10:45:00Z"
}
```

## Notification SignalR

```json
{
  "documentId": "<uuid>",
  "status": "UPLOADED",
  "message": "Fichier reçu"
}
```

Pour `PROCESSED`, ajouter `"tags": ["cv", "rh"]`.

## Ressources Azure à provisionner (étapes suivantes)

- Storage Account + container blob
- Cosmos DB (`db-doc` / `jobs`)
- Function App (Python)
- Service Bus (queue `document-processing` + DLQ)
- SignalR Service
- OpenAI API (`OPENAI_API_KEY` sur la Function App) — pas d’Azure OpenAI / Foundry sur ce projet
