from participant.models import SupportTicketV2, STATUS, CATEGORY


class SupportTicketInternalServices:
    @classmethod
    def filter_support_ticket_service(cls,user_map_id:str,status:STATUS,category:CATEGORY,start_date:str,end_date:str):
        tickets = SupportTicketV2.objects.filter(
            user_map_id=user_map_id
        ).order_by("created_at")

        if status:
            tickets = tickets.filter(status=status)

        if category:
            tickets = tickets.filter(category=category)

        if start_date and end_date:
            print("comes here")
            tickets = tickets.filter(created_at__range=(start_date, end_date))

        return tickets


