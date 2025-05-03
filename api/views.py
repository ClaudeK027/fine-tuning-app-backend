# fine-tuning-app-backend/api/views.py

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, parsers
# Modifiez les imports de models et serializers
from .models import AIModel, Dataset, FineTuningJob, FineTuningJobStatus
from .serializers import AIModelSerializer, DatasetSerializer, FineTuningJobSerializer
# Importez la tâche Celery
from .tasks import run_fine_tuning_task

class HealthCheckView(APIView):
    """Vue simple pour vérifier l'état de santé de l'API."""
    permission_classes = [] # Permettre l'accès sans authentification
    def get(self, request, *args, **kwargs):
        """Retourne une réponse simple indiquant que l'API est opérationnelle."""
        return Response({"status": "ok"}, status=status.HTTP_200_OK)

class AIModelViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les modèles AI."""
    queryset = AIModel.objects.all().order_by("-created_at")
    serializer_class = AIModelSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Exemple si auth

class DatasetViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les datasets."""
    queryset = Dataset.objects.all().order_by("-created_at")
    serializer_class = DatasetSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]

# --- Ajouts pour Itération 2 --- 

class FineTuningJobViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les FineTuningJobs."""
    queryset = FineTuningJob.objects.select_related("model", "dataset").all().order_by("-created_at")
    serializer_class = FineTuningJobSerializer
    # permission_classes = [permissions.IsAuthenticated] # Exemple: Seuls les users connectés peuvent gérer les jobs

    # Surcharge de la méthode create pour lancer la tâche Celery
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # Valide les données (model_id, dataset_id, hyperparameters)
        # Le serializer gère la liaison model_id -> model et dataset_id -> dataset grâce à "source"
        serializer.is_valid(raise_exception=True) 
        
        # Sauvegarde l'instance de job avec statut PENDING par défaut
        # et les relations model/dataset correctement établies.
        job = serializer.save() 
        
        # Lancer la tâche Celery en arrière-plan
        # .delay() est un raccourci pour .apply_async()
        try:
            task_result = run_fine_tuning_task.delay(job.id)
            # Optionnel: Sauvegarder immédiatement l'ID de tâche Celery si besoin pour suivi immédiat
            # job.celery_task_id = task_result.id
            # job.save(update_fields=["celery_task_id"])
        except Exception as e:
            # Si le lancement de la tâche échoue (ex: broker indisponible)
            # Marquer le job comme échoué immédiatement
            job.status = FineTuningJobStatus.FAILED
            job.error_message = f"Erreur lors du lancement de la tâche Celery: {e}"
            job.save(update_fields=["status", "error_message"])
            # Renvoyer une erreur au client
            return Response(
                {"detail": f"Erreur lors du lancement de la tâche de fond: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Retourner les données du job créé (avec statut PENDING)
        # serializer.data contient maintenant l'ID du job créé et les autres champs read_only
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # Les actions list (GET /) et retrieve (GET /{id}/) sont fournies par ModelViewSet
    # et utilisent le queryset et serializer_class définis.
    # Le queryset utilise select_related pour optimiser l'accès aux modèles/datasets liés.

# --- Fin Ajouts pour Itération 2 --- 
