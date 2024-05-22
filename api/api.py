class DKBApi:
    base_url = 'https://banking.dkb.de'
    api_prefix = '/api'
    mfa_method = 'seal_one'
    session = None
    account_Dict = None

    def __init__(self, dkb_user: str, dkb_password: str, mfa_device: int = None):
        self.dkb_user = dkb_user
        self.dkb_password = dkb_password
        self.mfa_device = mfa_device
