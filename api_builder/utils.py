import pandas as pd
import logging
import uuid
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import API

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.headers.get('Authorization', '')

        if not api_key.strip() or api_key.lower() == 'none':
            raise AuthenticationFailed('No API key provided.')

        api_key = api_key.split()[-1]

        try:
            api = API.objects.get(access_key=api_key)
        except API.DoesNotExist:
            raise AuthenticationFailed('API key is invalid.')

        return (api, None)

def generate_api_key():
    return str(uuid.uuid4())

def read_columns_from_csv_or_xlsx_file(file_path):
    """This function reads the file and returns the column names as a list."""
    try:
        if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            content = pd.read_excel(file_path, index_col=None, nrows=21).head(2) if file_path else None
        else:
            content = pd.read_csv(file_path, index_col=False, nrows=21).head(2) if file_path else None

        if content is not None:
            content = content.drop(content.filter(regex='Unnamed').columns, axis=1)
            content = content.fillna("")
            column_names = content.columns.astype(str).tolist()
        else:
            column_names = []

    except Exception as error:
        logging.error("Invalid file ERROR: %s", error)
        column_names = []

    return column_names
