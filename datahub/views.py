from accounts.models import User
from accounts.serializers import UserCreateSerializer
from django.conf import settings
from drf_braces.mixins import MultipleSerializersViewMixin
from rest_framework import pagination, status
from rest_framework.parsers import MultiPartParser, FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ViewSet

from datahub.models import Organization, UserOrganizationMap
from datahub.serializers import OrganizationSerializer, UserOrganizationMapSerializer, PolicyDocumentSerializer

import datetime, logging, os, shutil

LOGGER = logging.getLogger(__name__)


class DefaultPagination(pagination.PageNumberPagination):
    """
    Configure Pagination
    """

    page_size = 5


class TeamMemberViewSet(GenericViewSet):
    """Viewset for Product model"""

    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    pagination_class = DefaultPagination

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        product = self.get_object()
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantViewSet(GenericViewSet):
    """Viewset for Product model"""

    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    pagination_class = DefaultPagination

    def perform_create(self, serializer):
        return serializer.save()

    def create(self, request, *args, **kwargs):
        """POST method: create action to save an object by sending a POST request"""
        # self.retrieve(request, request.data.get("email", ""))
        # filter email from the queryset
        org_queryset = Organization.objects.filter(
            org_email=self.request.data["org_email"]
        ).values()
        if not org_queryset:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            org_queryset = self.perform_create(serializer)
            org_id = org_queryset.id
        else:
            org_id = org_queryset[0].get("id")
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_saved = self.perform_create(serializer)

        user_org_serializer = UserOrganizationMapSerializer(
            data={"user_id": user_saved.id, "organization_id": org_id}
        )
        user_org_serializer.is_valid(raise_exception=True)
        self.perform_create(user_org_serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET method: query all the list of objects from the Product model"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk):
        """GET method: retrieve an object or instance of the Product model"""
        product = self.get_object()
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT method: update or send a PUT request on an object of the Product model"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=None)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """DELETE method: delete an object"""
        product = self.get_object()
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DropDocumentView(APIView):
    """View for uploading organization document files"""
    parser_class = (MultiPartParser, FileUploadParser)

    def post(self, request):
        """Saves the document files in temp location before saving"""
        try:
            # get name, type, size & file obj from key of the form-data
            file_name = list(request.FILES.keys())[0]
            file_type = request.FILES.get(file_name).content_type.split('/')[1]     # file type
            file_size = request.FILES[file_name].size
            file = request.data[file_name]  # file obj
            max_limit = settings.FILE_UPLOAD_MAX_SIZE * 1000000

            if file_size > max_limit:
                return Response({'message: please upload file with size lesser than 2MB'})
            # check for file types (pdf, doc, docx)
            elif file_type not in settings.FILE_TYPES_ALLOWED:
                return Response({'message: Please upload only pdf or doc files'})
            else:
                with open(settings.TEMP_FILE_PATH + file_name + '.' + file_type, 'wb+') as file_upload_path:
                    for chunk in file.chunks():
                        file_upload_path.write(chunk)           # uploading

                    return Response({'message: uploading....'}, status=status.HTTP_201_CREATED) 

        except Exception as e:
            LOGGER.error(e)

        return Response({'message: encountered an error while uploading'}, status=status.HTTP_400_BAD_REQUEST)


class DocumentSaveView(GenericViewSet):
    """View for uploading all the datahub documents and content"""
    serializer_class = PolicyDocumentSerializer

    def create(self, request, *args, **kwargs):
        """Saves the document content and files"""
        try:
            serializer = PolicyDocumentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            for root, dirs, files in os.walk(settings.TEMP_FILE_PATH):
                for file in files:
                    # save the files in the destination directory
                    shutil.copyfile(root+file, os.getcwd() + '/' + settings.CONTENT_URL + file)

            return Response({'message: Document content saved!'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            LOGGER.error(e)

        return Response({'message: not allowed'}, status=status.HTTP_400_BAD_REQUEST)
