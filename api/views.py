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
from celery import current_app
import zipfile
import os
import shutil
from django.conf import settings
import logging
import uuid
from zipfile import ZipFile
import shutil

logger = logging.getLogger(__name__)

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
    # La logique de décompression est maintenant gérée par la tâche Celery.
    # Il n'y a plus besoin de surcharger perform_create.

    def perform_create(self, serializer):
        uploaded_file = self.request.data.get('file')

        if uploaded_file:
            # Créer un nom de dossier unique
            unique_folder_name = str(uuid.uuid4())
            model_directory = os.path.join(settings.MEDIA_ROOT, 'models', unique_folder_name)
            os.makedirs(model_directory, exist_ok=True)

            # Chemin temporaire pour le fichier zip
            zip_path = os.path.join(model_directory, uploaded_file.name)
            
            # Sauvegarder le fichier uploadé
            with open(zip_path, 'wb+') as temp_zip:
                for chunk in uploaded_file.chunks():
                    temp_zip.write(chunk)

            # Décompresser le fichier dans un dossier temporaire à l'intérieur de model_directory
            temp_extract_dir = os.path.join(model_directory, 'temp_extract')
            os.makedirs(temp_extract_dir, exist_ok=True)

            try:
                with ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
                
                # Logique d'aplatissement améliorée
                # Chercher le répertoire contenant config.json ou pytorch_model.bin
                source_dir_to_move = None
                for root, dirs, files in os.walk(temp_extract_dir):
                    if 'config.json' in files or 'pytorch_model.bin' in files or 'tf_model.h5' in files:
                        source_dir_to_move = root
                        break
                
                if source_dir_to_move and source_dir_to_move != model_directory:
                    # Déplacer le contenu du sous-dossier trouvé vers model_directory
                    for item in os.listdir(source_dir_to_move):
                        s = os.path.join(source_dir_to_move, item)
                        d = os.path.join(model_directory, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)
                elif not source_dir_to_move:
                    # Si aucun sous-dossier approprié n'est trouvé, 
                    # on suppose que les fichiers sont à la racine de temp_extract_dir
                    # ou que la structure n'est pas reconnue (ce qui pourrait poser problème plus tard)
                    # Pour l'instant, on copie tout de temp_extract_dir
                    for item in os.listdir(temp_extract_dir):
                        s = os.path.join(temp_extract_dir, item)
                        d = os.path.join(model_directory, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)

                # Sauvegarder l'instance avec le chemin vers le dossier final
                serializer.save(path=model_directory)

            finally:
                # Nettoyage
                if os.path.exists(temp_extract_dir):
                    shutil.rmtree(temp_extract_dir)
                if os.path.exists(zip_path):
                    os.remove(zip_path)
        else:
            serializer.save()

    def perform_destroy(self, instance):
        """
        Surcharge la suppression pour effacer aussi le dossier du modèle.
        """
        model_path = instance.path
        
        # Sécurité : Vérifier si le chemin existe et est bien un dossier
        if model_path and os.path.isdir(model_path):
            try:
                shutil.rmtree(model_path)
            except OSError as e:
                # Gérer l'erreur (par ex. logging) si la suppression échoue
                print(f"Error deleting directory {model_path}: {e.strerror}")
        
        # Appeler la méthode de suppression de la classe parente pour effacer l'objet en BDD
        super().perform_destroy(instance)

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
        serializer.is_valid(raise_exception=True)

        # Sauvegarde l'instance de job
        job = serializer.save()

        # Lancer la tâche Celery en arrière-plan avec les PKs
        try:
            # On passe les IDs simples, pas les objets complexes
            task_result = run_fine_tuning_task.delay(
                job.id,
                job.model.id,
                job.dataset.id
            )
            # Sauvegarder l'ID de la tâche Celery pour pouvoir la suivre/l'annuler
            job.celery_task_id = task_result.id
            job.save()
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
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_destroy(self, instance):
        """
        Surcharge la suppression pour annuler la tâche Celery si elle est en cours.
        """
        if instance.status == FineTuningJobStatus.RUNNING and instance.celery_task_id:
            try:
                # Annule la tâche. terminate=True envoie un signal SIGTERM au processus.
                current_app.control.revoke(instance.celery_task_id, terminate=True)
                logger.info(f"Tâche Celery {instance.celery_task_id} pour le job {instance.id} annulée.")
            except Exception as e:
                logger.error(f"Erreur lors de l'annulation de la tâche Celery {instance.celery_task_id}: {e}")
                # On continue la suppression de l'objet même si l'annulation échoue.

        # Appelle la méthode parente pour supprimer l'objet de la BDD.
        super().perform_destroy(instance)

    # Les actions list (GET /) et retrieve (GET /{id}/) sont fournies par ModelViewSet
    # et utilisent le queryset et serializer_class définis.
    # Le queryset utilise select_related pour optimiser l'accès aux modèles/datasets liés.

# --- Fin Ajouts pour Itération 2 --- 
