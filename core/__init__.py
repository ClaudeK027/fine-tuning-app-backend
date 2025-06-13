# fine-tuning-app-backend/core/__init__.py

# Ceci garantira que l'app est toujours importée quand Django démarre
# afin que les tâches partagées (@shared_task) utilisent cette app.
from .celery import app as celery_app

__all__ = ('celery_app',)
