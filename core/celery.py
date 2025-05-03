# fine-tuning-app-backend/core/celery.py

import os
from celery import Celery

# Définir le module de settings Django par défaut pour le programme 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Créer une instance de l'application Celery
# Le premier argument est le nom du module principal (votre projet Django)
app = Celery('core')

# Utiliser une chaîne ici signifie que le worker n'a pas besoin de sérialiser
# l'objet de configuration pour les processus enfants.
# - namespace='CELERY' signifie que toutes les clés de configuration Celery
#   doivent avoir un préfixe `CELERY_`.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Charger automatiquement les modules tasks.py depuis toutes les applications Django enregistrées.
app.autodiscover_tasks()

# Tâche d'exemple (optionnel, pour tester)
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
