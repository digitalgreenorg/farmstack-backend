from django.core.exceptions import ValidationError


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
