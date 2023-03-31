import datetime
import logging
import os
import urllib
from inspect import formatannotationrelativeto
from urllib import parse

import pandas as pd
import sendgrid
from django.conf import settings
from django.db import models
from python_http_client import exceptions
from rest_framework import pagination, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from sendgrid.helpers.mail import Content, Email, Mail

from core.constants import Constants

LOGGER = logging.getLogger(__name__)

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
            # subject (None, optional): _description_. Defaults to None.
        """
        content = Content("text/html", content)
        mail = Mail(FROM_EMAIL, to_email, subject, content, is_multiple=True)
        try:
            SG.client.mail.send.post(request_body=mail.get())
        # except exceptions.BadRequestsError as error:
        except exceptions.UnauthorizedError as error:
            LOGGER.error(
                "Failed to send email Subject: %s with ERROR: %s",
                subject,
                error.body,
                exc_info=True,
            )
            return Response({"Error": "Failed to send email "}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  # type: ignore
        except urllib.error.URLError as error:  # type: ignore
            LOGGER.error(
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
    scheme = "http" if "localhost" in netloc or "127.0.0.1" in netloc else "https"  # type: ignore
    path = path if "localhost" in netloc or "127.0.0.1" in netloc else "/be" + path  # type: ignore
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
    scheme = "http" if "localhost" in netloc or "127.0.0.1" in netloc else "https"  # type: ignore
    path = path if "localhost" in netloc or "127.0.0.1" in netloc else "/be" + path  # type: ignore
    # netloc = "datahubtest.farmstack.co"
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict.pop(key, None)
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


class CustomPagination(PageNumberPagination):
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


def date_formater(date_range: list):
    """This function accepts from date and to date as list and converts into valid date.

    Args:
        date_range (list): _description_
    """
    try:
        start = date_range[0].split("T")[0]
        end = date_range[1].split("T")[0]
        start = (datetime.datetime.strptime(start, "%Y-%m-%d") + datetime.timedelta(1)).strftime("%Y-%m-%d")
        end = (datetime.datetime.strptime(end, "%Y-%m-%d") + datetime.timedelta(2)).strftime("%Y-%m-%d")
        return [start, end]
    except Exception as error:
        logging.error("Invalid time formate: %s", error)
        return ["", ""]


def one_day_date_formater(date_range: list):
    """This function accepts from date and to date as list and converts into valid date.

    Args:
        date_range (list): _description_
    """
    try:
        start = date_range[0].split("T")[0]
        end = date_range[1].split("T")[0]
        start = (datetime.datetime.strptime(start, "%Y-%m-%d") + datetime.timedelta(1)).strftime("%Y-%m-%d")
        end = (datetime.datetime.strptime(end, "%Y-%m-%d") + datetime.timedelta(1)).strftime("%Y-%m-%d")
        return [start, end]
    except Exception as error:
        logging.error("Invalid time formate: %s", error)
        return ["", ""]


def csv_and_xlsx_file_validatation(file_obj):
    """This function accepts file obj and validates it."""
    try:
        name = file_obj.name
        if name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(file_obj, header=0)
        else:
            df = pd.read_csv(file_obj, encoding="unicode_escape", header=0)
        if len(df) < 5:
            return False
    except Exception as error:
        logging.error("Invalid file ERROR: %s", error)
        return False
    return True


def read_contents_from_csv_or_xlsx_file(file_path):
    """This function reads the file and return the contents as dict"""
    dataframe = pd.DataFrame([])
    try:
        if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            content = pd.read_excel("." + file_path, header=0).head(2) if file_path else dataframe
        else:
            content = pd.read_csv("." + file_path, header=0).head(2) if file_path else dataframe
        content = content.fillna("")
    except Exception as error:
        logging.error("Invalid file ERROR: %s", error)
        return []
    content.columns = content.columns.astype(str)
    return content.to_dict(orient=Constants.RECORDS)
