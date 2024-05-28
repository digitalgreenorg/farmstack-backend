from rest_framework.decorators import action, permission_classes
from accounts.models import User
from ai.retriever.manual_retrival import QuadrantRetrival
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.response import Response

from datahub.models import ResourceFile

class EmbeddingsViewSet(ModelViewSet):
    lookup_field = 'uuid'  # Specify the UUID field as the lookup field

    @action(detail=False, methods=['get'])
    def embeddings_and_chunks(self, request):
        collection_id = request.GET.get("resource_file")
        page_number = request.GET.get("page")
        if page_number and page_number !="":
            page_num = int(page_number)
        else:
            page_num =1
        # Define the metadata criteria for the chunks you want to retrieve
        # metadata_criteria = {
        #     'resource_file': collection_id  # Adjusted to include only files and images
        # }

        # Retrieve chunks based on the metadata
        chunks = QuadrantRetrival().embeddings_and_chunks(collection_id, page_num)
        return Response(chunks)

    
    @action(detail=False, methods=["post"])
    def get_content(self, request):
        embeddings = []
        email = request.data.get("email")
        query = request.data.get("query")
        state = request.data.get("state")
        sub_category = request.data.get("sub_category")
        user_obj = User.objects.filter(email=email)
        user = user_obj.first()
        data = (
                ResourceFile.objects.select_related(
                    "resource",
                    "resource__user_map",
                    "resource__user_map__user"
                )
            )
        if not user:
            return Response([])
        elif user.on_boarded_by:
            data = (
                data.filter(
                    Q(resource__user_map__user__on_boarded_by=user.on_boarded_by)
                    | Q(resource__user_map__user_id=user.on_boarded_by)
                    )
            )
        elif user.role_id == 6:
            data = (
                data.filter(
                    Q(resource__user_map__user__on_boarded_by=user.id)
                    | Q(resource__user_map__user_id=user.id)
                    )
            )
        else:
            data = (
                data.filter(resource__user_map__user__on_boarded_by=None).exclude(resource__user_map__user__role_id=6)
            )
        resource_file_ids = list(data.values_list("id", flat=True).all())
        chunks = QuadrantRetrival().retrieve_chunks(resource_file_ids, query, state, sub_category)
        return Response(chunks)