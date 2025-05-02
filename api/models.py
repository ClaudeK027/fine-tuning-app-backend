from django.db import models
import os

# Fonction pour définir le chemin d'upload des modèles
def model_upload_path(instance, filename):
    # Le fichier sera uploadé dans MEDIA_ROOT/models/<model_id>/<filename>
    # Note: instance.id n'est pas disponible lors de la première sauvegarde,
    # il faudrait une logique plus complexe ou un nommage différent si besoin.
    # Pour l'instant, utilisons un nom simple.
    return os.path.join('models', filename)

# Fonction pour définir le chemin d'upload des datasets
def dataset_upload_path(instance, filename):
    # Le fichier sera uploadé dans MEDIA_ROOT/datasets/<filename>
    return os.path.join('datasets', filename)

class ModelTypeChoices(models.TextChoices):
    LLM = 'LLM', 'Grand Modèle de Langage (LLM)'
    IMAGE_GENERATION = 'IMG_GEN', 'Génération d\images'
    VOICE_GENERATION = 'VOICE_GEN', 'Génération Vocale'
    VISION = 'VISION', 'Vision par Ordinateur (GenAI)' # Ex: analyse/génération conditionnée par image
    OTHER = 'OTHER', 'Autre'

class AIModel(models.Model):
    """Représente un modèle d'intelligence artificielle uploadé ou importé."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    architecture = models.CharField(max_length=100, blank=True, null=True) # Ex: BERT, ResNet50
    # Utilise la fonction pour déterminer le chemin d'upload
    upload_path = models.FileField(upload_to=model_upload_path, max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    # Utilise la fonction pour déterminer le chemin d'upload
    upload_path = models.FileField(upload_to=dataset_upload_path, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

