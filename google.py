from urllib import request, parse

import config
import json


def get_params_from_google():
    try:
        response = request.urlopen(config.GOOGLE_SHEET)
        json_data = json.loads(response.read().decode('utf-8'))
        return json_data
    except Exception:
        raise


def post_record_to_google(post_data):
    try:
        response = request.urlopen(config.GOOGLE_SHEET, parse.urlencode(post_data).encode())
        json_data = json.loads(response.read().decode('utf-8'))
        return json_data
    except Exception:
        raise
