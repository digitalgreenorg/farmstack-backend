"""String functions"""

def get_full_name(first_name, last_name):
    return first_name + " " + last_name if  last_name else first_name

def get_full_address(address):
    if address:
        data = {"address": address["address"]+", "+ address["city"], "pincode": address["pincode"], "country": address["country"]}
        return data

