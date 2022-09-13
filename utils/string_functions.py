"""String functions"""
import re

def get_full_name(first_name, last_name):
    return first_name + " " + last_name if  last_name else first_name

def get_full_address(address):
    if address:
        data = {"address": address.get("address","")+ ", " + address.get("city",""), "pincode": address.get("pincode",""), "country": address.get("country","")}
        return data

def dataset_category_formatted(category):
    data = []
    for key, value in category.items():
        if value == True:
            data.append(re.sub("_", " ", key).title())
    return data
