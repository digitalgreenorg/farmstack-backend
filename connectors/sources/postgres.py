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


def connect_with_postgres(config, cookie_data):
    LOGGER.info(f"Connecting to Postgres")
    try:
        tables = []
        with closing(psycopg2.connect(**config)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                table_list = cursor.fetchall()
        # send the tables as a list in response body & set cookies
        tables = [
            table for inner_list in table_list for table in inner_list]
        response = HttpResponse(json.dumps(
            tables), status=status.HTTP_200_OK)
        response = update_cookies(
            "conn_details", cookie_data, response)
        return response
    except psycopg2.Error as err:
        print(err)
        if "password authentication failed for user" in str(err) or "role" in str(err):
            # Incorrect username or password
            return Response(
                {
                    "username": ["Incorrect username or password"],
                    "password": ["Incorrect username or password"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif "database" in str(err):
            # Database does not exist
            return Response({"dbname": ["Database does not exist"]}, status=status.HTTP_400_BAD_REQUEST)
        elif "could not translate host name" in str(err):
            # Database does not exist
            return Response({"host": ["Invalid Host address"]}, status=status.HTTP_400_BAD_REQUEST)

        elif "Operation timed out" in str(err):
            # Server is not available
            return Response({"port": ["Invalid port or DB Server is down"]}, status=status.HTTP_400_BAD_REQUEST)

        # Return an error message if the connection fails
        return Response({"error": [str(err)]}, status=status.HTTP_400_BAD_REQUEST)


def connect_and_get_column_using_postgres(config,table_name):
    """Create a PostgreSQL connection object on valid database credentials"""
    LOGGER.info(f"Connecting to Postgres")
    try:
        # Try to connect to the database using the provided configuration
        connection = mysql.connector.connect(**config)
        mydb = connection
        mycursor = mydb.cursor()
        db_name = config["database"]
        mycursor.execute("use " + db_name + ";")
        mycursor.execute("SHOW COLUMNS FROM " +
                         db_name + "." + table_name + ";")

        # Fetch columns & return as a response
        col_list = mycursor.fetchall()
        cols = [column_details[0] for column_details in col_list]
        response = HttpResponse(json.dumps(
            cols), status=status.HTTP_200_OK)
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
            return Response({"table_name": ["Table does not exist"]}, status=status.HTTP_400_BAD_REQUEST)
        elif err.errno == mysql.connector.errorcode.ER_KEY_COLUMN_DOES_NOT_EXITS:
            return Response({"col": ["Columns does not exist."]}, status=status.HTTP_400_BAD_REQUEST)
        # Return an error message if the connection fails
        return Response({"error": [str(err)]}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        LOGGER.error(e, exc_info=True)
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


def export_database_data_into_xls_using_postgres(
        config,col_names,t_name,serializer,dataset_name,source,file_name,dataset
):
    """Create a PostgreSQL connection object on valid database credentials"""
    LOGGER.info(f"Connecting to Postgres")
    try:
        with closing(psycopg2.connect(**config)) as conn:
            try:

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
                df = pd.read_sql(query_string, conn)
                if df.empty:
                    return Response({"data": [f"No data was found for the filter applied. Please try again."]},
                                    status=status.HTTP_400_BAD_REQUEST)

                df = df.astype(str)
            except pd.errors.DatabaseError as error:
                LOGGER.error(error, exc_info=True)
                return Response({"col": ["Columns does not exist."]}, status=status.HTTP_400_BAD_REQUEST)

        file_path = file_ops.create_directory(
            settings.DATASET_FILES_URL, [dataset_name, source])
        df.to_excel(os.path.join(
            file_path, file_name + ".xls"))
        serializer = create_dataset_v2_for_data_import(
            dataset=dataset,
            source=source,
            dataset_name=dataset_name,
            file_name=file_name
        )
        return JsonResponse(serializer.data, status=status.HTTP_200_OK)

    except psycopg2.Error as error:
        LOGGER.error(error, exc_info=True)
        return Response(str(error), status=status.HTTP_400_BAD_REQUEST)

