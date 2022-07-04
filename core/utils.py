import logging
import urllib
from urllib import parse

import sendgrid
from django.conf import settings
from django.db import models
from python_http_client import exceptions
from rest_framework import pagination, status
from rest_framework.pagination import PageNumberPagination
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
                "Failed to send email Subject: %s with ERROR: %s",
                subject,
                error.body,
                exc_info=True,
            )
            return error
        except urllib.error.URLError as error:  # type: ignore
            logger.error(
                "Failed to send email Subject: %s with ERROR: %s",
                subject,
                error,
                exc_info=True,
            )
            return Response({"Error": "Failed to send email "}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  # type: ignore

        return Response({"Message": "Email successfully sent!"}, status=status.HTTP_200_OK)


def replace_query_param(url, key, val, req):
    """
    Given a URL and a key/val pair, set or replace an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(str(url))
    netloc = req.META.get("HTTP_HOST")
    scheme = "http" if "localhost" in netloc else "https"  # type: ignore
    path = path if "localhost" in netloc else "/be" + path  # type: ignore
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[str(key)] = [str(val)]
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


def remove_query_param(url, key, req):
    """
    Given a URL and a key/val pair, remove an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(str(url))
    netloc = req.META.get("HTTP_HOST")
    scheme = "http" if "localhost" in netloc else "https"
    path = path if "localhost" in netloc else "/be" + path
    # netloc = "datahubtest.farmstack.co"
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict.pop(key, None)
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "per_page"
    max_page_size = 5

    def get_next_link(self):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri()
        req = self.request
        page_number = self.page.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number, req)

    def get_previous_link(self):
        req = self.request
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param, req)
        return replace_query_param(url, self.page_query_param, page_number, req)


class DefaultPagination(pagination.PageNumberPagination):
    """
    Configure Pagination
    """

    page_size = 5
