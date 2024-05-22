import os

from dotenv import load_dotenv

from api import DKBApi

load_dotenv()


def main(username: str, password: str) -> None:
    dkb_api = DKBApi(dkb_user=username, dkb_password=password)
    dkb_api.login()


if __name__ == '__main__':
    main(username=os.environ.get("DKB_USERNAME"), password=os.environ.get("DKB_PASSWORD"))
