# fine-tuning-app-backend/api/serializers.py

from rest_framework import serializers
# Modifiez l'import pour inclure FineTuningJob 
from .models import AIModel, Dataset, FineTuningJob, ModelTypeChoices, FineTuningJobStatus # Ajout ModelTypeChoices, FineTuningJobStatus
import os
from django.conf import settings

class AIModelSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le modèle AIModel."""
    upload_path_url = serializers.SerializerMethodField()
    # Afficher la version lisible du choix
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)

    class Meta:
        model = AIModel
        # Inclure model_type_display
        fields = ['id', 'name', 'description', 'architecture', 'path', 'upload_path_url', 'model_type', 'model_type_display', 'created_at', 'updated_at']
        read_only_fields = ('created_at', 'updated_at', 'upload_path_url', 'model_type_display')

    def get_upload_path_url(self, obj):
        # obj.path est le chemin absolu du dossier du modèle sur le serveur.
        # Nous voulons une URL relative à MEDIA_URL.
        if obj.path and hasattr(settings, 'MEDIA_URL') and settings.MEDIA_URL and hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
            try:
                # Rendre le chemin relatif à MEDIA_ROOT
                relative_path = os.path.relpath(obj.path, settings.MEDIA_ROOT)
                # os.path.normpath pour normaliser les séparateurs (ex: \ en /)
                # Remplacer les séparateurs Windows par des slashes pour l'URL
                url_path_part = os.path.normpath(relative_path).replace(os.sep, '/')
                
                # Construire l'URL
                request = self.context.get('request')
                base_url = str(settings.MEDIA_URL)
                # S'assurer qu'il n'y a pas de double slash
                if base_url.endswith('/') and url_path_part.startswith('/'):
                    full_url_path = base_url + url_path_part[1:]
                elif not base_url.endswith('/') and not url_path_part.startswith('/'):
                    full_url_path = base_url + '/' + url_path_part
                else:
                    full_url_path = base_url + url_path_part
                
                if request:
                    return request.build_absolute_uri(full_url_path)
                else:
                    # Fallback si pas de request dans le contexte (moins courant pour les URLs absolues)
                    return full_url_path

            except ValueError:
                # Peut arriver si obj.path n'est pas sous MEDIA_ROOT ou si MEDIA_ROOT/MEDIA_URL ne sont pas définis
                return None
        return None

class DatasetSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le modèle Dataset."""
    upload_path_url = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'upload_path_url')

    def get_upload_path_url(self, obj):
        if obj.upload_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.upload_path.url)
        return None

# --- Ajouts pour Itération 2 --- 

class FineTuningJobSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le modèle FineTuningJob."""
    # Optionnel: Afficher des détails sur le modèle et le dataset plutôt que juste l'ID
    # Utiliser read_only=True car ces champs sont remplis par le modèle, pas fournis à la création
    model_details = AIModelSerializer(source='model', read_only=True)
    dataset_details = DatasetSerializer(source='dataset', read_only=True)
    # Afficher la version lisible du statut
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Champs pour accepter les IDs lors de la création (POST)
    # write_only=True signifie qu'ils ne seront pas inclus dans la réponse GET
    # source='model' lie ce champ au champ 'model' du modèle FineTuningJob
    model_id = serializers.PrimaryKeyRelatedField(
        queryset=AIModel.objects.all(), source='model', write_only=True,
        help_text="ID du modèle AI à utiliser."
    )
    dataset_id = serializers.PrimaryKeyRelatedField(
        queryset=Dataset.objects.all(), source='dataset', write_only=True,
        help_text="ID du dataset à utiliser."
    )

    class Meta:
        model = FineTuningJob
        fields = [
            'id',
            'model', # Garde l'ID du modèle en lecture pour référence
            'dataset', # Garde l'ID du dataset en lecture pour référence
            'model_details', # Détails imbriqués en lecture
            'dataset_details', # Détails imbriqués en lecture
            'model_id', # Pour l'écriture (création)
            'dataset_id', # Pour l'écriture (création)
            'hyperparameters',
            'status',
            'status_display', # Version lisible du statut
            'celery_task_id',
            'output_model_path',
            'created_at',
            'updated_at',
            'error_message',
        ]
        # Champs qui ne peuvent pas être définis directement via l'API (gérés par le système)
        read_only_fields = (
            'id', # L'ID est toujours en lecture seule
            'status', 
            'status_display',
            'celery_task_id', 
            'output_model_path', 
            'created_at', 
            'updated_at', 
            'error_message',
            'model_details', # Les détails sont pour la lecture
            'dataset_details',
            'model', # L'ID du modèle est aussi en lecture seule (défini via model_id)
            'dataset', # L'ID du dataset est aussi en lecture seule (défini via dataset_id)
        )

    # Validation des hyperparamètres (exemple simple)
    def validate_hyperparameters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Les hyperparamètres doivent être un objet JSON.")
        
        # Vérifier les types et valeurs des clés attendues
        lr = value.get('lr')
        epochs = value.get('epochs')
        batch_size = value.get('batch_size')

        errors = {}
        if lr is None:
            errors['lr'] = "Le taux d'apprentissage (lr) est requis."
        elif not isinstance(lr, (int, float)) or lr <= 0:
            errors['lr'] = "Le taux d'apprentissage doit être un nombre positif."
        
        if epochs is None:
            errors['epochs'] = "Le nombre d'époques (epochs) est requis."
        elif not isinstance(epochs, int) or epochs <= 0:
            errors['epochs'] = "Le nombre d'époques doit être un entier positif."

        if batch_size is None:
            errors['batch_size'] = "La taille du batch (batch_size) est requise."
        elif not isinstance(batch_size, int) or batch_size <= 0:
            errors['batch_size'] = "La taille du batch doit être un entier positif."

        if errors:
            raise serializers.ValidationError(errors)
             
        # Retourner seulement les clés validées ou toutes ? Pour l'instant toutes.
        return value

# --- Fin Ajouts pour Itération 2 --- 
