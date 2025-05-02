from rest_framework import serializers
from .models import AIModel, Dataset

class AIModelSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le modèle AIModel."""
    # Rend l'URL du fichier uploadé au lieu du chemin local
    upload_path_url = serializers.SerializerMethodField()

    class Meta:
        model = AIModel
        # Inclut tous les champs du modèle par défaut
        fields = '__all__'
        # Rend certains champs en lecture seule dans l'API (gérés automatiquement)
        read_only_fields = ('created_at', 'updated_at', 'upload_path_url')

    def get_upload_path_url(self, obj):
        # Retourne l'URL complète si un fichier est associé
        if obj.upload_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.upload_path.url)
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

