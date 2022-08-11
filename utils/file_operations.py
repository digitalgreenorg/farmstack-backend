from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import logging, os, shutil, cssutils
from python_http_client import exceptions

LOGGER = logging.getLogger(__name__)

# class FileSave:


def file_save(source_file, file_name, destination):
    """Save files"""
    try:
        fs = FileSystemStorage(destination)
        # overrides if file exists
        if fs.exists(file_name):
            fs.delete(file_name)
            fs.save(destination + file_name, source_file)
            return "replaced"
        else:
            fs.save(destination + file_name, source_file)
            return "saved"
    except Exception as e:
        LOGGER.error(e)


def file_path(destination):
    try:
        for root, dirs, files in os.walk(destination):
            file_paths = {os.path.splitext(os.path.basename(file))[0]: root + file for file in files}
            # file_paths = {file: root + file for file in files}
            # print(file_paths)
            return file_paths
    except Exception as e:
        LOGGER.error(e)


def files_move(source, destination):
    """Move files or dirs"""
    try:
        for root, dirs, files in os.walk(source):
            for file in files:
                # shutil.move(root + file, destination)
                print("file source", root+file)
                shutil.copy(root + file, destination)
                os.remove(root + file)
                print("file moved", destination+file)
    except Exception as e:
        LOGGER.error(e)


def remove_files(file_key, destination):
    """Remove files"""
    try:
        fs = FileSystemStorage(destination)
        for root, dirs, files in os.walk(destination):
            for file in files:
                if file.split(".")[0] == file_key:
                    fs.delete(root + file)
    except Exception as e:
        LOGGER.error(e)


def get_file_name(file, output_file):
    """Splits the file extension"""
    try:
        file_type = str(file).split(".")[1]
        file_name = output_file + "." + file_type
        # print(file_name)
        return file_name
    except Exception as e:
        LOGGER.error(e)


def get_css_attributes(css_path, css_attribute):
    """Get CSS files"""
    try:
        with open(css_path) as css:
            sheet = cssutils.css.CSSStyleSheet()
            sheet.cssText = css.read()
            css_attribute_value = sheet.cssRules[0].style[css_attribute]
            # print(css_attribute_value)
        return css_attribute_value
    except Exception as e:
        LOGGER.error(e)
