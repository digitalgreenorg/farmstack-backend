import json
from contextlib import closing
import mysql.connector
import os
import psycopg2
from django.http import HttpResponse, JsonResponse
from rest_framework import pagination, serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from connectors.utils import update_cookies, create_dataset_v2_for_data_import
from core import settings
from core.constants import Constants, NumericalConstants
import logging
import datetime
from rest_framework.exceptions import ValidationError
import pandas as pd

from datahub.serializers import DatasetFileV2NewSerializer
from utils import file_operations as file_ops

LOGGER = logging.getLogger(__name__)


def connect_with_mysql(request, cookie_data, config):
    LOGGER.info(f"Connecting to MySQL")

    try:
        # Try to connect to the database using the provided configuration
        mydb = mysql.connector.connect(**config)
        mycursor = mydb.cursor()
        db_name = request.data.get("database")
        mycursor.execute("use " + db_name + ";")
        mycursor.execute("show tables;")
        table_list = mycursor.fetchall()
        table_list = [
            element for innerList in table_list for element in innerList]

        # send the tables as a list in response body
        response = HttpResponse(json.dumps(
            table_list), status=status.HTTP_200_OK)
        # set the cookies in response
        response = update_cookies(
            "conn_details", cookie_data, response)
        return response
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            return Response(
                {
                    "username": ["Incorrect username or password"],
                    "password": ["Incorrect username or password"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif err.errno == mysql.connector.errorcode.ER_NO_SUCH_TABLE:
            return Response({"table": ["Table does not exist"]},
                            status=status.HTTP_400_BAD_REQUEST)
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            # Port is incorrect
            return Response({
                "dbname": ["Invalid database name. Connection Failed."]}, status=status.HTTP_400_BAD_REQUEST)
        # Return an error message if the connection fails
        return Response({"host": ["Invalid host . Connection Failed."]}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


def connect_and_get_column_using_mysql(config, table_name):
    """Create a PostgreSQL connection object on valid database credentials"""
    LOGGER.info(f"Connecting to MySQL")
    try:
        col_list = []
        with closing(psycopg2.connect(**config)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor = conn.cursor()
                # Fetch columns & return as a response
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='{0}';".format(
                        table_name
                    )
                )
                col_list = cursor.fetchall()

        if len(col_list) <= 0:
            return Response({"table_name": ["Table does not exist."]}, status=status.HTTP_400_BAD_REQUEST)

        cols = [column_details[0] for column_details in col_list]
        return HttpResponse(json.dumps(cols), status=status.HTTP_200_OK)
    except psycopg2.Error as error:
        LOGGER.error(error, exc_info=True)
        return Response({"table_name": ["Something went wrong please try again later."]},
                        status=status.HTTP_400_BAD_REQUEST)


def export_database_data_into_xls_using_mysql(
        config, col_names, t_name, serializer, dataset_name, source, file_name, dataset
):
    """Create a PostgreSQL connection object on valid database credentials"""
    LOGGER.info(f"Connecting to MYSQL")

    try:
        mydb = mysql.connector.connect(**config)
        mycursor = mydb.cursor()
        db_name = config["database"]
        mycursor.execute("use " + db_name + ";")

        query_string = f"SELECT {col_names} FROM {t_name}"
        sub_queries = []  # List to store individual filter sub-queries
        if serializer.data.get("filter_data"):

            filter_data = json.loads(serializer.data.get("filter_data")[0])
            for query_dict in filter_data:
                query_string = f"SELECT {col_names} FROM {t_name} WHERE "
                column_name = query_dict.get('column_name')
                operation = query_dict.get('operation')
                value = query_dict.get('value')
                sub_query = f"{column_name} {operation} '{value}'"  # Using %s as a placeholder for the value
                sub_queries.append(sub_query)
            query_string += " AND ".join(sub_queries)

        mycursor.execute(query_string)
        result = mycursor.fetchall()

        # save the list of files to a temp directory
        file_path = file_ops.create_directory(
            settings.DATASET_FILES_URL, [dataset_name, source])
        df = pd.read_sql(query_string, mydb)
        if df.empty:
            return Response({"data": [f"No data was found for the filter applied. Please try again."]},
                            status=status.HTTP_400_BAD_REQUEST)
        df = df.astype(str)
        df.to_excel(file_path + "/" + file_name + ".xls")
        serializer = create_dataset_v2_for_data_import(
            dataset=dataset,
            source=source,
            dataset_name=dataset_name,
            file_name=file_name
        )
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        # return HttpResponse(json.dumps(result), status=status.HTTP_200_OK)

    except mysql.connector.Error as err:
        LOGGER.error(err, exc_info=True)
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            return Response(
                {
                    "username": ["Incorrect username or password"],
                    "password": ["Incorrect username or password"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif err.errno == mysql.connector.errorcode.ER_NO_SUCH_TABLE:
            return Response({"table_name": ["Table does not exist"]}, status=status.HTTP_400_BAD_REQUEST)
        # elif err.errno == mysql.connector.errorcode.ER_KEY_COLUMN_DOES_NOT_EXITS:
        elif str(err).__contains__("Unknown column"):
            return Response({"col": ["Columns does not exist."]}, status=status.HTTP_400_BAD_REQUEST)
        # Return an error message if the connection fails
        return Response({"": [str(err)]}, status=status.HTTP_400_BAD_REQUEST)
