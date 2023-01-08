import re, logging, os

LOGGER = logging.getLogger(__name__)


def get_full_name(first_name, last_name):
    """
    Return full name by concatenating first and last names.

    **Parameters**
    ``first_name`` (str): first name to be concatenated
    ``last_name`` (str): last name to be concatenated with
    """
    return first_name + " " + last_name if  last_name else first_name


def get_full_address(address):
    """
    Return full address as a dictionary.

    **Parameters**
    ``address`` (JSON obj): address
    """
    if address:
        data = {"address": address.get("address","")+ ", " + address.get("city",""), "pincode": address.get("pincode",""), "country": address.get("country","")}
        return data


def dataset_category_formatted(category):
    data = []
    for key, value in category.items():
        if value == True:
            data.append(re.sub("_", " ", key).title())
    return data


def check_special_chars(name: str):
    """
    Check if the string contains special characters.

    **Parameters**
    ``name`` (str): string to be checked
    """
    try:
        special_char = re.compile(r'[@_!#$%^&*()<>?/\\|}{~:]')
        if special_char.search(name):
            return True
        return False

    except Exception as error:
        LOGGER.error(error, exc_info=True)


def format_dir_name(directory: str, name: str):
    """
    Remove the white spaces from the directory to be created.

    **Parameters**
    ``name`` (str): directory name to be formatted with a trailing slash

    **Returns**
    ``destination`` (str): formatted single white space directory name
    """
    name = re.sub(r'\s+', ' ', name)
    destination = os.path.join(directory, name, "", "")
    return destination
