import os

from dotenv import load_dotenv

from api import DKBApi

load_dotenv()


def main(username: str, password: str) -> None:
    dkb_api = DKBApi(dkb_user=username, dkb_password=password, mfa_device_idx=0)
    dkb_api.login()

    account_info = dkb_api.get_accounts()
    transactions = dkb_api.get_transactions(account_info["data"][0]["id"])


if __name__ == '__main__':
    main(username=os.environ.get("DKB_USERNAME"), password=os.environ.get("DKB_PASSWORD"))
