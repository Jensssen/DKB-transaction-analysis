import os
import re
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

from api import DKBApi
import json

import pandas as pd

from api import GoogleSheetsApi
from model.transaction import Transaction
from utils import flatten_dict, df_to_sheet_range, categorize_transaction, group_df_by_year, group_df_by_month


def string_processing(string: str) -> str:
    string = re.sub(r'\s+', ' ', string)
    string = string.lower()
    return string


def extract_data_from_dict(attribute_dict: Dict[str, str]) -> List[Transaction]:
    transaction_list = []

    line_count = 0
    for transaction in attribute_dict["data"]:
        if transaction["attributes"]["status"] == "booked":
            transaction_amount = transaction["attributes"]["amount"]["value"]
            transaction_title = string_processing(transaction["attributes"]["creditor"]["name"])
            transaction_date = transaction["attributes"]["bookingDate"]
            try:
                transaction_comment = string_processing(transaction["attributes"]["description"])
            except KeyError:
                transaction_comment = "-"
            print(transaction_date, transaction_title, transaction_amount)
            transaction_list.append(
                Transaction("DKB", transaction_amount, transaction_title, transaction_date, transaction_comment))
            print(f'Processed {line_count} lines.')
    return transaction_list


def main(username: str, password: str) -> None:
    dkb_api = DKBApi(dkb_user=username, dkb_password=password, mfa_device_idx=0)
    dkb_api.login()

    account_info = dkb_api.get_accounts()
    transactions = dkb_api.get_transactions(account_info["data"][0]["id"])
    timestamp = datetime.now().strftime("%d:%m:%Y_%H_%M_%S")

    with open(f"transactions_{timestamp}.json", 'w') as json_file:
        json.dump(transactions, json_file, indent=4)

    with open(f"transactions_{timestamp}.json") as f:
        transaction_data = json.load(f)["data"]

    google_sheet_api = GoogleSheetsApi()

    model_instances = [Transaction(**item) for item in transaction_data]
    data_dicts = [flatten_dict(instance.dict()) for instance in model_instances]
    df = pd.DataFrame(data_dicts)

    df.to_csv(f"transactions_17:06:2024_12_15_41.json", index=False)

    df = pd.read_csv(f"transactions_17:06:2024_12_15_41.json")

    df = df.loc[::-1].reset_index(drop=True)
    header = [column_name.split("_")[-1] for column_name in df.columns.tolist()]
    df_list = df.values.tolist()

    # Insert reformatted header into df
    df_list.insert(0, header)

    sheet_range = df_to_sheet_range(df_list)
    sheet_id = google_sheet_api.create("Final_sheet")

    # Add all raw transactions to sheet
    google_sheet_api.rename_sheet(sheet_id, "RAW_DATA")
    google_sheet_api.add_data(sheet_id, f"RAW_DATA!{sheet_range}", "USER_ENTERED", df_list)

    # Categories all transactions
    df = categorize_transaction(df)
    header = df.columns.tolist()
    header = [column_name.split("_")[-1] for column_name in header]

    # Group all categorised transactions by year
    dfs_by_year = group_df_by_year(df.copy())

    # Write categorised data into separate year tabs
    for year, data in dfs_by_year.items():
        sum_row_start = 2

        # Separate transactions by month
        df_by_month = group_df_by_month(data.copy())
        extended_df = pd.DataFrame(columns=data.columns)
        for idx, (month, month_data) in enumerate(df_by_month.items()):
            sum_row_end = sum_row_start + len(month_data) - 1

            extended_df = pd.concat([extended_df, month_data], ignore_index=True)
            columns = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S",
                       "T",
                       "U", "V", "W", "X", "Y", "Z"]

            extended_df.loc[len(extended_df)] = pd.Series(
                [' '] * len(df_list[0]) + [f"=SUM({col}{sum_row_start}:{col}{sum_row_end})" for col in
                                           columns[len(df_list[0]):len(month_data.columns)]], index=month_data.columns)
            extended_df.loc[len(extended_df)] = pd.Series(['------------------'] * len(month_data.columns),
                                                          index=month_data.columns)
            sum_row_start = sum_row_end + 3

        google_sheet_api.add_new_sheet(sheet_id, year)
        data = extended_df.values.tolist()
        data.insert(0, header)
        sheet_range = df_to_sheet_range(data)
        google_sheet_api.add_data(sheet_id, f"{year}!{sheet_range}", "USER_ENTERED", data)


if __name__ == '__main__':
    main(username=os.environ.get("DKB_USERNAME"), password=os.environ.get("DKB_PASSWORD"))
