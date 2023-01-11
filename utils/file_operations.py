from django.core.files.storage import FileSystemStorage
from django.utils import timezone
import logging, os, shutil, cssutils, re

from core.constants import Constants
from .validators import validate_image_type

LOGGER = logging.getLogger(__name__)


def remove_files(file_key: str, destination: str):
    """
    Remove files from the file path or destination directory.

    **Parameters**
    ``file_key`` (str): file name or file name without extension
    ``destination`` (str): directory or file path
    """
    try:
        # destination = rf"{destination}" + "/"
        fs = FileSystemStorage(destination)
        with os.scandir(destination) as file_path:
            for file in file_path:
                # deleting file based on file key, that is passed without extension
                if file.is_file() and file.name.split(".")[:-1][0] == file_key:
                    LOGGER.info(f"Deleting file: {destination+file.name}")
                    fs.delete(destination + file.name)
                # deleting file based on file name
                elif file.is_file() and file.name == file_key:
                    LOGGER.info(f"Deleting file: {destination+file.name}")
                    fs.delete(destination + file.name)
    except Exception as error:
        LOGGER.error(error, exc_info=True)


def move_directory(source: str, destination: str):
    """
    Move files from location to another on the file system.

    **Parameters**
    ``source`` (str): source directory to be moved
    ``destination`` (str): directory or file path where the source needs to be moved
    """
    try:
        if not os.path.exists(source):
            LOGGER.error(f"{source} not found")
            raise FileNotFoundError(f"{source} not found")
        else:
            # shutil.copyfileobj(source+file.name, destination)
            destination = shutil.move(os.path.join(source), os.path.join(destination))
            LOGGER.info(f"Directory moved: directory {source} moved to {destination}")
            return destination
    except Exception as error:
        LOGGER.error(error, exc_info=True)


def create_directory(directory: str, names: list):
    """
    Create a directory or directories at the destination or skip if exists.

    **Parameters**
    ``directory`` (str): directory name
    ``name`` (list): list of nested directory names to create inside directory
    """
    try:
        print(os.path.join(directory, names[0]))
        if names:
            formatted_names = [re.sub(r'\s+', ' ', name) for name in names]
            directory = os.path.join(directory, *formatted_names, "", "")

        if not os.path.exists(directory):
            os.makedirs(directory)
            LOGGER.info(f"Creating directory: {directory}")
        print("DIRE", directory)
        return directory
    except Exception as error:
        LOGGER.error(error, exc_info=True)


def file_save(source_file, file_name: str, directory: str):
    """
    Save or replace files at the preferred destination or file path.

    **Parameters**
    ``source_file`` (file obj): file obj to be saved
    ``file_name`` (str): file name to be saved
    ``destination`` (str): directory or file path where to save the file
    """

    try:
        with open(directory+file_name, "wb+") as dest_file:
            for chunk in source_file.chunks():
                dest_file.write(chunk)

        LOGGER.info(f"File saved: {directory+file_name}")
    except Exception as error:
        LOGGER.error(error, exc_info=True)
    return file_name


def file_path(destination: str):
    """
    Return file paths and its file names without file extensions.

    **Parameters**
    ``destination`` (str): directory or file path

    **Returns**
    ``file_paths`` (dict): dictionary containing file names & file paths

        ``Example``
        {'key': 'path/to/file.ext'}
    """
    try:
        file_paths = {
            os.path.splitext(os.path.basename(file))[0]: destination + file.name
            for file in os.scandir(destination)
        }
        LOGGER.info(f"file paths: {file_paths}")
        return file_paths
    except Exception as error:
        LOGGER.error(error, exc_info=True)


def files_move(source: str, destination: str):
    """
    Move files from location to another on the file system.

    **Parameters**
    ``source`` (str): source directory or file path from where the file needs to be moved
    ``destination`` (str): directory or file path where to where the file needs to be saved
    """
    try:
        with os.scandir(source) as file_path:
            for file in file_path:
                if file.is_file():
                    # shutil.copyfileobj(source+file.name, destination)
                    shutil.move(os.path.join(source, file.name), os.path.join(destination, file.name))
                    LOGGER.info(f"File moved: {source+file.name}")

    except Exception as error:
        LOGGER.error(error, exc_info=True)


def file_rename(file: str, key: str):
    """
    Returns the desired file name for a file.

    **Parameters**
    ``file_name`` (str): file_name to be converted
    ``key`` (str): key for the file name

    **Returns**
    ``file_name`` (str): desired file name
    """
    try:
        validate_image_type(file)
        file_split = str(file).split(".")

        if not key:
            timestamp = str(timezone.now().timestamp())
            file_to_save = file_split[:-1][0] + "-" + timestamp + "." + file_split[-1]
        elif key:
            file_to_save = key + "." + file_split[-1]
        return file_to_save

    except Exception as error:
        LOGGER.error(error, exc_info=True)


def get_css_attributes(css_path: str, css_attribute: str):
    """
    Returns CSS attribute value of the HTML element.

    **Parameters**
    ``css_path`` (str): CSS file path
    ``css_attribute`` (str): CSS property or attribute

    **Returns**
    ``css_attribute_value`` (str): value of CSS attribute or property
    """
    try:
        with open(css_path) as css:
            sheet = cssutils.css.CSSStyleSheet()
            sheet.cssText = css.read()
            css_attribute_value = sheet.cssRules[0].style[css_attribute]
        return css_attribute_value
    except Exception as error:
        LOGGER.error(error, exc_info=True)
