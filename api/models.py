# fine-tuning-app-backend/api/models.py

from django.db import models
import os

# Fonction pour définir le chemin d'upload des modèles
def model_upload_path(instance, filename):
    # Le fichier sera uploadé dans MEDIA_ROOT/models/<filename>
    # Simplifié pour l'instant, pourrait être affiné avec ID plus tard
    return os.path.join('models', filename)

# Fonction pour définir le chemin d'upload des datasets
def dataset_upload_path(instance, filename):
    # Le fichier sera uploadé dans MEDIA_ROOT/datasets/<filename>
    return os.path.join('datasets', filename)

class ModelTypeChoices(models.TextChoices):
    LLM = 'LLM', 'Grand Modèle de Langage (LLM)'
    IMAGE_GENERATION = 'IMG_GEN', 'Génération d\'images'
    VOICE_GENERATION = 'VOICE_GEN', 'Génération Vocale'
    VISION = 'VISION', 'Vision par Ordinateur (GenAI)' # Ex: analyse/génération conditionnée par image
    OTHER = 'OTHER', 'Autre'

class AIModel(models.Model):
    """Représente un modèle d'intelligence artificielle uploadé ou importé."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    architecture = models.CharField(max_length=100, blank=True, null=True) # Ex: BERT, ResNet50
    upload_path = models.FileField(upload_to=model_upload_path, max_length=500, blank=True, null=True)
    model_type = models.CharField(
        max_length=10,
        choices=ModelTypeChoices.choices,
        default=ModelTypeChoices.OTHER,
        help_text="Catégorie du modèle d'IA Générative"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Dataset(models.Model):
    """Représente un jeu de données uploadé pour le fine-tuning."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file_format = models.CharField(max_length=10, blank=True, null=True) # Ex: 'csv', 'jsonl'
    upload_path = models.FileField(upload_to=dataset_upload_path, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# --- Ajouts pour Itération 2 --- 

class FineTuningJobStatus(models.TextChoices):
    PENDING = 'PENDING', 'En attente'
    RUNNING = 'RUNNING', 'En cours'
    SUCCESS = 'SUCCESS', 'Terminé avec succès'
    FAILED = 'FAILED', 'Échec'

class FineTuningJob(models.Model):
    """Représente une tâche de fine-tuning lancée par un utilisateur."""
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE, related_name='fine_tuning_jobs')
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='fine_tuning_jobs')
    
    # Stocke les hyperparamètres utilisés pour ce job
    hyperparameters = models.JSONField(default=dict, help_text="Ex: {'lr': 0.001, 'epochs': 3, 'batch_size': 8}")
    
    status = models.CharField(
        max_length=10,
        choices=FineTuningJobStatus.choices,
        default=FineTuningJobStatus.PENDING,
    )
    
    # ID de la tâche Celery associée, pour pouvoir suivre son état
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Chemin vers le modèle résultant du fine-tuning (si succès)
    # Stocké comme chemin relatif à MEDIA_ROOT
    output_model_path = models.CharField(max_length=500, blank=True, null=True)
    
    # Informations de suivi
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True) # Pour stocker les erreurs

    def __str__(self):
        return f"Job {self.id} ({self.model.name} / {self.dataset.name}) - {self.status}"

# --- Fin Ajouts pour Itération 2 --- 
