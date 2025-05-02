# Utiliser une image Python officielle
FROM python:3.11-slim

# Définir des variables d'environnement pour éviter que Python n'écrive des fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système si nécessaire (ici, juste pour info, pas requis pour l'instant)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Installer les dépendances Python
# Copier d'abord requirements.txt pour profiter du cache Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . /app/

# Exposer le port sur lequel Django va tourner
EXPOSE 8000

# Commande par défaut pour lancer l'application (sera ajustée pour la prod plus tard)
# Pour le développement, on utilise le serveur de développement Django
# Assurez-vous que manage.py est exécutable si nécessaire: RUN chmod +x manage.py
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
