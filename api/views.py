from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets, parsers, status
from rest_framework.response import Response
from .models import AIModel, Dataset
from .serializers import AIModelSerializer, DatasetSerializer

class HealthCheckView(APIView):
    """Vue simple pour vérifier l'état de santé de l'API."""
    def get(self, request, *args, **kwargs):
        """Retourne une réponse simple indiquant que l'API est opérationnelle."""
        return Response({"status": "ok"}, status=status.HTTP_200_OK)




class AIModelViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les modèles AI."""
    queryset = AIModel.objects.all().order_by("-created_at")
    serializer_class = AIModelSerializer
    # Ajoute le parser pour gérer les uploads de fichiers (multipart/form-data)
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

    # Optionnel : Si vous voulez une logique spécifique lors de la création
    # def perform_create(self, serializer):
    #     # Par exemple, pour associer l'utilisateur courant (si auth est en place)
    #     # serializer.save(owner=self.request.user)
    #     serializer.save()

class DatasetViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les datasets."""
    queryset = Dataset.objects.all().order_by("-created_at")
    serializer_class = DatasetSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

    # Optionnel : Logique spécifique à la création
    # def perform_create(self, serializer):
    #     serializer.save()

