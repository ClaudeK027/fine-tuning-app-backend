# Utiliser une image Python officielle
FROM python:3.11-slim

# Définir des variables d'environnement pour éviter que Python n'écrive des fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances Python
# Copier d'abord requirements.txt pour profiter du cache Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . /app/

# Exposer le port sur lequel Django va tourner
EXPOSE 8000
