from core.constants import Constants
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_size(value):
    """
    Validator function to check the file size limit.
    """
    filesize = value.size
    print("file_size", filesize)
    if filesize > Constants.MAX_FILE_SIZE:
        raise ValidationError("You cannot upload file more than 2Mb")
    else:
        return value


def validate_image_type(file):
    """
    Validator function to check check for image types
    """
    # file_type = file.content_type.split("/")[1]
    file_extension = str(file).split(".")[-1]
    # if file_type not in settings.IMAGE_TYPES_ALLOWED and file_extension not in settings.IMAGE_TYPES_ALLOWED:
    if file_extension not in settings.IMAGE_TYPES_ALLOWED:
        raise ValidationError("Image type not supported. Image type allowed: png, jpg, jpeg")
    return file_extension


def validate_document_type(file):
    """
    Validator function to check check for document types
    """
    # file_type = file.content_type.split("/")[1]
    file_extension = str(file).split(".")[-1]
    # if file_type not in settings.FILE_TYPES_ALLOWED and file_extension not in settings.FILE_TYPES_ALLOWED:
    if file_extension not in settings.FILE_TYPES_ALLOWED:
        raise ValidationError("Document type not supported. Document type allowed: pdf, doc, docx")
    return file
