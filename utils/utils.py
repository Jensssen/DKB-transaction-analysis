from typing import Dict
from utils.categories import categories
import pandas as pd


def flatten_dict(dd: Dict, separator: str = '_', prefix: str = '') -> Dict:
    """Flattens a nested dictionary and returns it."""
    return {prefix + separator + k if prefix else k: v
            for kk, vv in dd.items()
            for k, v in flatten_dict(vv, separator, kk).items()
            } if isinstance(dd, dict) else {prefix: dd}


def df_to_sheet_range(data):
    alphabet_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
                     "U", "V", "W", "X", "Y", "Z"]
    return f"A1:{alphabet_list[len(data[0]) - 1]}{len(data)}"


def group_df_by_year(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    df['id'] = pd.to_datetime(df['id'])
    df['year'] = df['id'].dt.year
    df['id'] = df['id'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')

    grouped = df.groupby('year')
    return {str(year): group.drop(columns='year') for year, group in grouped}


def group_df_by_month(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    df['id'] = pd.to_datetime(df['id'])
    df['month'] = df['id'].dt.month
    df['id'] = df['id'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    grouped = df.groupby('month')
    return {str(month): group.drop(columns='month') for month, group in grouped}


def categorize_transaction(df):
    if "Sonstiges" not in categories:
        categories["Sonstiges"] = None
    for category, rule in categories.items():
        df[category] = "0"
    for index, row in df.iterrows():
        category_found = False
        for category, rule in categories.items():
            if rule is not None:
                for attribute, check_list in rule.items():
                    description = row[attribute].lower()
                    for value in check_list:
                        if value in description:
                            df.at[index, category] = row["attributes_amount_value"]
                            category_found = True
                            break
            if category_found:
                break
        if not category_found:
            df.at[index, "Sonstiges"] = row["attributes_amount_value"]
    return df

