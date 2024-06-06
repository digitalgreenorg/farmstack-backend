from rest_framework.decorators import action, permission_classes
from accounts.models import User
from ai.retriever.manual_retrival import QuadrantRetrival
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.response import Response
from django.db.models import Prefetch
from datahub.models import Resource, ResourceFile, ResourceSubCategoryMap, SubCategory, Category

class EmbeddingsViewSet(ModelViewSet):
    lookup_field = 'uuid'  # Specify the UUID field as the lookup field
    permission_classes=[]

    @action(detail=False, methods=['get'])
    def embeddings_and_chunks(self, request):
        collection_id = request.GET.get("resource_file")
        # Define the metadata criteria for the chunks you want to retrieve
        metadata_criteria = {
            'resource_file': collection_id  # Adjusted to include only files and images
        }

        # Retrieve chunks based on the metadata
        chunks = QuadrantRetrival().embeddings_and_chunks(collection_id)
        return Response(chunks)

    
    @action(detail=False, methods=["post"])
    def get_content(self, request):
        embeddings = []
        email = request.data.get("email")
        query = request.data.get("query")
        country = request.data.get("country", "").lower()
        state = request.data.get("state", "").lower()
        category = request.data.get("category", "").lower()
        sub_category = request.data.get("sub_category", "")
        district = request.data.get("district", "").lower()
        file_ids=[]
        if sub_category:
            file_ids = list(ResourceFile.objects.filter(
                            resource__resource_cat_map__sub_category_id=sub_category
                            ).values_list('id', flat=True).distinct().all())
            
        chunks = QuadrantRetrival().retrieve_chunks(file_ids, query, country, state,district, category)
        return Response(chunks)
    
    @action(detail=False, methods=["GET"])
    def get_crops(self, request):
        state=request.GET.get("state")
        country=request.GET.get("country")
        result=[]
        if state:
            result = self.get_state_crops(state)

        elif country:
            result = self.get_country_crops(country)

        return Response(result)
    
    def get_country_crops(self, country):
        # resource_sub_category_maps = ResourceSubCategoryMap.objects.filter(
        #     sub_category__name__icontains=country
        # ).select_related('sub_category__category', 'resource')

        # Get the list of resource IDs associated with the state
        resource_ids = Resource.objects.filter(country=country).values_list('id', flat=True).distinct()

        # Fetch all subcategories related to these resources, excluding categories named "States"
        related_sub_category_maps = ResourceSubCategoryMap.objects.filter(
            resource_id__in=resource_ids
        ).select_related('sub_category__category').exclude(sub_category__category__name="States")

        # Prepare a dictionary to collect categories and their subcategories
        category_dict = {}

        for resource_map in related_sub_category_maps:
            category = resource_map.sub_category.category
            sub_category = resource_map.sub_category

            # Initialize category entry if not exists
            if category.id not in category_dict:
                category_dict[category.id] = {
                    'category_name': category.name,
                    'category_id': category.id,
                    'sub_categories': []
                }

            # Add subcategory to the category's sub_categories list
            if not any(sub['sub_category_id'] == sub_category.id for sub in category_dict[category.id]['sub_categories']):
                category_dict[category.id]['sub_categories'].append({
                    'sub_category_name': sub_category.name,
                    'sub_category_id': sub_category.id
                })

        # Convert category_dict to a list
        return list(category_dict.values())
    
    def get_state_crops(self, state):
        resource_sub_category_maps = ResourceSubCategoryMap.objects.filter(
            sub_category__name__icontains=state
        ).select_related('sub_category__category', 'resource')

        # Get the list of resource IDs associated with the state
        resource_ids = resource_sub_category_maps.values_list('resource_id', flat=True).distinct()

        # Fetch all subcategories related to these resources, excluding categories named "States"
        related_sub_category_maps = ResourceSubCategoryMap.objects.filter(
            resource_id__in=resource_ids
        ).select_related('sub_category__category').exclude(sub_category__category__name="States")

        # Prepare a dictionary to collect categories and their subcategories
        category_dict = {}

        for resource_map in related_sub_category_maps:
            category = resource_map.sub_category.category
            sub_category = resource_map.sub_category

            # Initialize category entry if not exists
            if category.id not in category_dict:
                category_dict[category.id] = {
                    'category_name': category.name,
                    'category_id': category.id,
                    'sub_categories': []
                }

            # Add subcategory to the category's sub_categories list
            if not any(sub['sub_category_id'] == sub_category.id for sub in category_dict[category.id]['sub_categories']):
                category_dict[category.id]['sub_categories'].append({
                    'sub_category_name': sub_category.name,
                    'sub_category_id': sub_category.id
                })

        # Convert category_dict to a list
        return list(category_dict.values())