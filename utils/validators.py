from django.core.exceptions import ValidationError
from django.conf import settings


def validate_file_size(value):
    """
    Validator function to check the file size limit.
    """
    filesize = value.size
    print("file_size", filesize)
    if filesize > 2097152:
        raise ValidationError("You cannot upload file more than 2Mb")
    else:
        return value


def validate_image_type(file):
    """
    Validator function to check check for image types
    """
    file_type = file.content_type.split("/")[1]
    # print(file_type)
    if file_type not in settings.IMAGE_TYPES_ALLOWED:
        raise ValidationError("Image type not supported")
    return file_type


def validate_document_type(file):
    """
    Validator function to check check for document types
    """
    file_type = file.content_type.split("/")[1]
    # print(file_type)
    if file_type not in settings.FILE_TYPES_ALLOWED:
        raise ValidationError("Document type not supported")
    return file
