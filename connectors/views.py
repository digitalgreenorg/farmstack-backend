from django.shortcuts import render
from connectors.models import Connectors, ConnectorsMap
from connectors.serializers import (ConnectorsSerializer, ConnectorsMapSerializer,
 ConnectorsCreateSerializer, ConnectorsMapCreateSerializer)
from rest_framework.viewsets import GenericViewSet, ViewSet
from core.utils import (
    CustomPagination,
)
from rest_framework.response import Response
from rest_framework import pagination, status

# Create your views here.


class ConnectorsViewSet(GenericViewSet):
    """Viewset for Product model"""

    queryset = Connectors.objects.all()
    pagination_class = CustomPagination

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = ConnectorsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        connectors_data = serializer.data
        print(connectors_data)

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
        connectors_map = Connectors.objects.all()
        serializer = ConnectorsSerializer(instance=connectors_map, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        connector_serializer = ConnectorsSerializer(
            instance, data=request.data, partial=True
        )
        connector_serializer.is_valid(raise_exception=True)
        connector_map_serializer = ConnectorsMapSerializer(
        instance, data=request.data, partial=True
        )
        connector_map_serializer.is_valid(raise_exception=True)
        connector_serializer.save()
        connector_map_serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        connector = self.get_object()
        connector.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

