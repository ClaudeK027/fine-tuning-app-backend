# fine-tuning-app-backend/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Modifiez l'import des vues pour inclure FineTuningJobViewSet
from .views import HealthCheckView, AIModelViewSet, DatasetViewSet, FineTuningJobViewSet

# Crée un routeur
router = DefaultRouter()

# Enregistre les ViewSets existants
router.register(r"models", AIModelViewSet, basename="model")
router.register(r"datasets", DatasetViewSet, basename="dataset")

# --- Ajout pour Itération 2 --- 
# Enregistre le nouveau ViewSet pour les jobs
router.register(r"fine-tuning-jobs", FineTuningJobViewSet, basename="finetuningjob")
# --- Fin Ajout pour Itération 2 --- 

urlpatterns = [
    # Inclut les URLs générées par le routeur (/api/models/, /api/datasets/, /api/fine-tuning-jobs/)
    path("", include(router.urls)),
    
    # Garde l'URL du healthcheck si besoin (en dehors du routeur)
    path("healthcheck/", HealthCheckView.as_view(), name="healthcheck"),
]
