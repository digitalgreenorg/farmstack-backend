from django.db import transaction
from django.shortcuts import render
from rest_framework import pagination, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from connectors.models import Connectors, ConnectorsMap
from connectors.serializers import (
    ConnectorsCreateSerializer,
    ConnectorsMapCreateSerializer,
    ConnectorsMapSerializer,
    ConnectorsSerializer,
)
from core.constants import Constants
from core.utils import CustomPagination

# Create your views here.


class ConnectorsViewSet(GenericViewSet):
    """Viewset for Product model"""

    queryset = Connectors.objects.all()
    pagination_class = CustomPagination
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = ConnectorsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        connectors_data = serializer.data
        for maps in request.data.get("maps", []):
            maps["connectors"] = connectors_data.get("id")
            serializer = ConnectorsMapCreateSerializer(data=maps)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(connectors_data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        data = Connectors.objects.all()
        page = self.paginate_queryset(data)
        connectors_data = ConnectorsSerializer(page, many=True)
        return self.get_paginated_response(connectors_data.data)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        instance = self.get_object()
        serializer = ConnectorsSerializer(instance=instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @transaction.atomic
    def update(self, request, pk):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        connector_serializer = ConnectorsCreateSerializer(
            instance, data=request.data, partial=True
        )
        connector_serializer.is_valid(raise_exception=True)
        connector_serializer.save()
        for maps in request.data.get(Constants.MAPS, []):
            maps[Constants.CONNECTORS] = pk
            if maps.get(Constants.ID):
                instance = ConnectorsMap.objects.get(id=maps.get(Constants.ID))
                serializer = ConnectorsMapCreateSerializer(instance, data=maps, partial=True)
            else:
               serializer = ConnectorsMapCreateSerializer(data=maps)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(connector_serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        if request.GET.get(Constants.MAPS):
            connector = ConnectorsMap.objects.get(id=pk)
            connector.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            connector = self.get_object()
            connector.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

