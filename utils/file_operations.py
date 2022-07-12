from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import logging, os, shutil

LOGGER = logging.getLogger(__name__)

# class FileSave:


def file_save(source_file, file_name, destination):
    """Save files"""
    try:
        fs = FileSystemStorage(
            destination,
            # directory_permissions_mode=0o755,
            # file_permissions_mode=0o755,
        )

        # overrides if file exists
        if fs.exists(file_name):
            fs.delete(file_name)
            fs.save(destination + file_name, source_file)
            # print("replaced")
            return "replaced"
        else:
            fs.save(destination + file_name, source_file)
            # print("saved")
            return "saved"
    except Exception as e:
        LOGGER.error(e)


def file_path(destination):
    try:
        for root, dirs, files in os.walk(destination):
            file_paths = {os.path.splitext(os.path.basename(file))[0]: root + file for file in files}
            # file_paths = {file: root + file for file in files}
            print(file_paths)
            return file_paths
    except Exception as e:
        LOGGER.error(e)


def files_move(source, destination):
    """Move files or dirs"""
    try:
        for root, dirs, files in os.walk(source):
            for file in files:
                # shutil.move(root + file, destination)
                shutil.copy(root + file, destination)
                os.remove(root + file)
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
