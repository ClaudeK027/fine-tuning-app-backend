from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HealthCheckView, AIModelViewSet, DatasetViewSet

# Crée un routeur
router = DefaultRouter()
# Enregistre les ViewSets avec le routeur
# Le premier argument est le préfixe de l'URL (ex: /api/models/)
# Le deuxième est le ViewSet
# Le troisième est le nom de base pour les noms d'URL générés
router.register(r'models', AIModelViewSet, basename='model')
router.register(r'datasets', DatasetViewSet, basename='dataset')

urlpatterns = [
    # Inclut les URLs générées par le routeur
    path('', include(router.urls)),
    # Garde l'URL du healthcheck si besoin
    path('healthcheck/', HealthCheckView.as_view(), name='healthcheck'),
]
