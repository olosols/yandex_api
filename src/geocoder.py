import requests

BASE_URL = "https://geocode-maps.yandex.ru/v1/"

def geocode_address(address: str, api_key: str) -> dict:
    if not address or not address.strip():
        raise ValueError("Адрес пуст")
    if not api_key or not api_key.strip():
        raise ValueError("api ключ отстувует")

    params  = {"apikey": api_key,
               "geocode": address,
               "format": "json",
               "lang": "ru_RU",
               "results": 1,}

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=(5, 15),
    )

    response.raise_for_status()
    return response.json()

def transformation_response(data: dict) -> dict|None:
    collection = data["response"]["GeoObjectCollection"]
    response_metadata = collection["metaDataProperty"]["GeocoderResponseMetaData"]
    request = response_metadata["request"]
    found = int(response_metadata["found"])

    members = collection["featureMember"]
    if not members:
        return None

    # первый геообъект
    geo_object = members[0]["GeoObject"]

    # Метаданные
    geocoder_metadata = geo_object["metaDataProperty"]["GeocoderMetaData"]
    precision = geocoder_metadata["precision"]
    form_address = geocoder_metadata["text"]
    kind = geocoder_metadata["kind"]

    address_data = geocoder_metadata["Address"]
    locality = None

    for component in address_data.get("Components", []):
        if component.get("kind") == "locality":
            locality = component.get("name")
            break
    country_code = address_data["country_code"]
    postal_code = address_data.get("postal_code") # т.к. почт. индекс может отсутсвовать

    # обрабатываем кординаты
    position = geo_object["Point"]["pos"]
    longitude, latitude = map(float, position.split())

    return {
            "request": request,
            "found": found,
            "formatted_address": form_address,
            "precision": precision,
            "kind": kind,
            "country_code": country_code,
            "postal_code": postal_code,
            "locality": locality,
            "longitude": longitude,
            "latitude": latitude,
        }