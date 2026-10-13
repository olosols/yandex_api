import os

from dotenv import load_dotenv
from geocoder import geocode_address, transformation_response
from pathlib import Path
import pandas as pd
import requests

def main() -> None:
    load_dotenv()

    directory  = Path(__file__).resolve().parent.parent
    input_path = directory / "data" / "input" / "addresses.csv"
    output_path = directory / "data" / "output"/ "geocoded.csv"

    df= pd.read_csv(input_path,sep=";")
    required_columns = {"object_id", "address"}
    missing_columns = required_columns - set(df.columns)


    if missing_columns:
        raise ValueError(f"В CSV отсутствуют: {missing_columns}")
    api_key = os.getenv("YANDEX_GEOCODER")
    if not api_key or not api_key.strip():
        raise ValueError("Ключ не задан")

    results = []
    errors = []

    # Проверяем наличие
    for row in df.itertuples(index=False):
        if pd.isna(row.address):
            continue
        address = str(row.address).strip() # для удаления пробелов и пропуск строк из пробелов
        if not address:
            continue

        try:
            data_response = geocode_address(address=address, api_key=api_key)
        except requests.exceptions.RequestException as error:
            status_code = (
                error.response.status_code
                if error.response is not None
                else None
            )
            errors.append({
                "object_id": row.object_id,
                "source_address": address,
                "error_type": type(error).__name__,
                "status_code": status_code,
            })
            print(f"Объект {row.object_id}: ошибка {type(error).__name__}, HTTP {status_code}")
            continue
        transform_result = transformation_response(data_response)
        if transform_result is None:
            continue
        transform_result["object_id"] = row.object_id
        transform_result["source_address"] = address
        results.append(transform_result)

    print(f"Успешно: {len(results)}, ошибок API: {len(errors)}")
    print(pd.DataFrame(errors))
    if not results:
        raise ValueError('Нет результатов геокодирования')

    result_df = pd.DataFrame(results)
    print(result_df.head())
    print(result_df["precision"].value_counts(dropna=False))
    print(result_df["kind"].value_counts(dropna=False))

    # Поиск проблемной записи
    resersch_columns = ["object_id",
                    "source_address",
                    "formatted_address",
                    "precision",
                    "kind",
                    "longitude",
                    "latitude"]
    resersch = result_df.loc[result_df["precision"] != "exact",resersch_columns,]
    print(resersch.to_string(index=False))
    result_df["quality_status"] = "rejected"

    review_mask = (result_df["kind"].eq("house")
            & result_df["precision"].isin(["number", "near", "range"])
            & result_df["country_code"].eq("RU")
            & result_df["locality"].eq("Тюмень"))
    result_df.loc[review_mask, "quality_status"] = "review"

    accepted_mask = (
        result_df["kind"].eq("house")
        & result_df["precision"].eq("exact")
        & result_df["country_code"].eq("RU")
        & result_df["locality"].eq("Тюмень")
    )
    result_df.loc[accepted_mask, "quality_status"] = "accepted"
    print(result_df["quality_status"].value_counts())

    output_path.parent.mkdir(parents=True, exist_ok=True) # чтобы сздать папку после клонирования гит
    result_df.to_csv(output_path, sep=";", index=False, encoding="utf-8")

if __name__ == "__main__":
    main()