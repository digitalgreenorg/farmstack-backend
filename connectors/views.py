import logging
import os
import shutil

import pandas as pd
from django.db import transaction
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from connectors.models import Connectors, ConnectorsMap
from connectors.serializers import (
    ConnectorsCreateSerializer,
    ConnectorsListSerializer,
    ConnectorsMapCreateSerializer,
    ConnectorsMapSerializer,
    ConnectorsSerializer,
)
from core import settings
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
        # setattr(request.data, "_mutable", True)
        data = request.data
        temp_path = f"{os.path.join(settings.MEDIA_URL,settings.TEMP_CONNECTOR_URL)}{data.get('name')}.xlsx"
        dest_path = f"{settings.CONNECTOR_FILES_URL}{data.get('name')}.xlsx"
        if os.path.exists(temp_path):
            shutil.move(temp_path, dest_path)
        serializer = ConnectorsCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        Connectors.objects.filter(id=serializer.data.get("id")).update(integrated_file=dest_path)
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
        connectors_data = ConnectorsListSerializer(page, many=True)
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
        connector_serializer = ConnectorsCreateSerializer(instance, data=request.data, partial=True)
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

    @action(detail=False, methods=["post"])
    def integration(self, request, *args, **kwargs):
        data = request.data
        maps = request.data.get("maps")
        if not maps:
            return Response({f"Minimum 2 datasets should select for integration"}, status=500)
        integrate = maps[0]
        try:
            left_dataset_file_path = integrate.get("left_dataset_file_path")
            right_dataset_file_path = integrate.get("right_dataset_file_path")
            condition = integrate.get("condition")

            if left_dataset_file_path.endswith(".xlsx") or left_dataset_file_path.endswith(".xls"):
                df1 = pd.read_excel(os.path.join(settings.MEDIA_ROOT, left_dataset_file_path), usecols=condition.get("left_selected"))
            else:
                df1 = pd.read_csv(os.path.join(settings.MEDIA_ROOT, left_dataset_file_path), usecols=condition.get("left_selected"))
            if right_dataset_file_path.endswith(".xlsx") or right_dataset_file_path.endswith(".xls"):
                df2 = pd.read_excel(os.path.join(settings.MEDIA_ROOT, right_dataset_file_path), usecols=condition.get("right_selected"))
            else:
                df2 = pd.read_csv(os.path.join(settings.MEDIA_ROOT, right_dataset_file_path), usecols=condition.get("right_selected"))
            # Join the dataframes
            result = pd.merge(
                df1,
                df2,
                how=condition.get("how", "left"),
                left_on=condition.get("left_on"),
                right_on=condition.get("right_on"),
            )
            for i in range(1, len(maps)):
                integrate = data[i]
                right_dataset_file_path = integrate.get("right_dataset_file_path")
                condition = integrate.get("condition")
                if right_dataset_file_path.endswith(".xlsx") or right_dataset_file_path.endswith(".xls"):
                    df2 = pd.read_excel(
                        os.path.join(settings.MEDIA_ROOT, right_dataset_file_path), usecols=condition.get("right_selected")
                    )
                else:
                    df2 = pd.read_csv(
                        os.path.join(settings.MEDIA_ROOT, right_dataset_file_path), usecols=condition.get("right_selected")
                    )
                # Join the dataframes
                result = pd.merge(
                    result,
                    df2,
                    how=condition.get("how", "left"),
                    left_on=condition.get("left_on"),
                    right_on=condition.get("right_on"),
                )

            name = data.get("name", "connectors")
            file_path = f"{settings.TEMP_CONNECTOR_URL}{name}.xlsx"
            result.to_excel(file_path)
            return Response({"integrated_file": file_path, "data":result.to_json(orient="records")}, status=status.HTTP_200_OK)
        except Exception as e:
            logging.error(str(e), exc_info=True)
            return Response({f"error while integration {integrate} ": str(e)}, status=500)
