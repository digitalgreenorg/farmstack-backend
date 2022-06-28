import logging
import urllib

import sendgrid
from django.conf import settings
from django.db import models
from python_http_client import exceptions
from rest_framework import pagination, status
from rest_framework.response import Response
from sendgrid.helpers.mail import Content, Email, Mail

logger = logging.getLogger(__name__)

SG = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
FROM_EMAIL = Email(settings.EMAIL_HOST_USER)


class Utils:
    """
    This class will support with the generic functions that can be utilized by the whole procject.
    """

    def send_email(self, to_email: list, content=None, subject=None):
        """
        This function gets the To mails list with content and subject
        and sends the mail to respective recipiants. By default content and subject will be empty.

        Args:
            to_email (list): List of emails to send the Invitation.
            content (None, optional): _description_. Defaults to None.
            subject (None, optional): _description_. Defaults to None.
        """
        content = Content("text/html", content)
        mail = Mail(FROM_EMAIL, to_email, subject, content)
        try:
            SG.client.mail.send.post(request_body=mail.get())
        except exceptions.BadRequestsError as error:
            logger.error(
                "Faild to send email Subject: %s with ERROR: %s",
                subject,
                error.body,
                exc_info=True,
            )
            return error
        except urllib.error.URLError as error:  # type: ignore
            logger.error(
                "Faild to send email Subject: %s with ERROR: %s",
                subject,
                error,
                exc_info=True,
            )
            return Response({"Error": "Faild to send email "}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  # type: ignore

        return Response({"Message": "Invation sent to the participants"}, status=status.HTTP_200_OK)


class DefaultPagination(pagination.PageNumberPagination):
    """
    Configure Pagination
    """

    page_size = 5


class TimeStampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
