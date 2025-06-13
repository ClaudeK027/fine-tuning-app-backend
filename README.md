# Fine-Tuning Application - Backend

## 📖 Description

Ce projet constitue le backend de l'application de fine-tuning. Il s'agit d'une API RESTful développée avec Django et Django REST Framework, conçue pour gérer des modèles d'intelligence artificielle, des jeux de données, et lancer des tâches d'affinage (fine-tuning) de manière asynchrone.

Le backend est entièrement conteneurisé avec Docker, ce qui simplifie son déploiement et son exécution dans un environnement de développement ou de production.

---

## ✨ Fonctionnalités

- **Gestion des Modèles AI :** CRUD complet pour les modèles d'IA (ex: GPT-2, BERT).
- **Gestion des Datasets :** CRUD pour les jeux de données, incluant une fonctionnalité d'upload de fichiers CSV.
- **Gestion des Jobs de Fine-Tuning :**
    - Création et suivi des tâches d'affinage.
    - Lancement des entraînements en arrière-plan grâce à **Celery** et **Redis**.
    - Suivi du statut des jobs (En attente, En cours, Terminé, Échoué).
    - Annulation des jobs en cours.
- **API RESTful :** Endpoints clairs et documentés pour interagir avec le frontend.
- **Conteneurisation :** Entièrement fonctionnel via Docker et Docker Compose.

---

## 🛠️ Stack Technique

- **Langage :** Python 3.10+
- **Framework :** Django, Django REST Framework
- **Tâches Asynchrones :** Celery
- **Broker de Messages :** Redis
- **Base de Données :** PostgreSQL (configurable, SQLite par défaut pour le développement)
- **Conteneurisation :** Docker, Docker Compose
- **Bibliothèques IA :** Hugging Face `transformers`, `datasets`, `torch`

---

## 🚀 Installation et Lancement

### Prérequis

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Étapes

1.  **Clonez le dépôt :**
    ```bash
    git clone https://github.com/votre-utilisateur/fine-tuning-app-backend.git
    cd fine-tuning-app-backend
    ```

2.  **Lancez l'application avec Docker Compose :**
    Cette commande va construire les images Docker pour le backend, le worker Celery et Redis, puis démarrer les conteneurs.
    ```bash
    docker-compose up --build -d
    ```

3.  **Appliquez les migrations de la base de données :**
    ```bash
    docker-compose exec backend python manage.py migrate
    ```

4.  **L'API est maintenant accessible** à l'adresse `http://localhost:8000/api/`.

---

## 📡 Endpoints de l'API

Voici un aperçu des principaux endpoints disponibles :

| Méthode | Endpoint                      | Description                               |
|---------|-------------------------------|-------------------------------------------|
| `GET`   | `/api/ai-models/`             | Lister tous les modèles d'IA.             |
| `GET`   | `/api/datasets/`              | Lister tous les datasets.                 |
| `POST`  | `/api/datasets/upload/`       | Uploader un nouveau dataset (fichier CSV).|
| `GET`   | `/api/fine-tuning-jobs/`      | Lister tous les jobs d'affinage.          |
| `POST`  | `/api/fine-tuning-jobs/`      | Créer un nouveau job d'affinage.          |
| `GET`   | `/api/fine-tuning-jobs/{id}/` | Obtenir les détails d'un job spécifique.  |
| `DELETE`| `/api/fine-tuning-jobs/{id}/` | Supprimer un job (et annuler la tâche).   |
| `GET`   | `/api/healthcheck/`           | Vérifier l'état de santé de l'API.        |

---

## 📂 Structure du Projet

```
fine-tuning-app-backend/
├── api/                   # Application Django principale
│   ├── migrations/
│   ├── models.py          # Modèles de données (AIModel, Dataset, FineTuningJob)
│   ├── serializers.py     # Sérialiseurs pour l'API
│   ├── views.py           # Logique des endpoints (ViewSets)
│   └── urls.py            # Routage de l'API
├── fine_tuning_project/   # Configuration du projet Django
│   ├── settings.py
│   └── celery.py          # Configuration de Celery
├── tasks/                 # Tâches Celery
│   └── fine_tuning.py     # Logique de l'entraînement du modèle
├── Dockerfile             # Instructions pour construire l'image du backend
├── docker-compose.yml     # Orchestration des services (backend, worker, redis)
└── requirements.txt       # Dépendances Python
```
