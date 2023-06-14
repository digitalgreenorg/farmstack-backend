from rest_framework.response import Response

from participant.constants import FilterAPIConstants
from participant.models import SupportTicketV2, STATUS, CATEGORY


class SupportTicketInternalServices:
    @classmethod
    def search_tickets(cls, user_id:str, search_text: str,others:bool,map_id:str):
        queryset = SupportTicketV2.objects.filter().select_related(
            "user_map__organization", "user_map__user", "user_map__user__role", "user_map"
        ).order_by("-updated_at")
        filter = {"user_map__user__on_boarded_by_id": user_id} if others else {"user_map_id": map_id}
        queryset = queryset.filter(ticket_title__icontains=search_text,**filter)
        return queryset
