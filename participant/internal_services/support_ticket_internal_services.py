from rest_framework.response import Response

from participant.constants import FilterAPIConstants
from participant.models import SupportTicketV2, STATUS, CATEGORY


class SupportTicketInternalServices:
    @classmethod
    def search_tickets(cls, user_id:str, search_text: str,others:bool,map_id:str):
        pass