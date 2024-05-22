import os
import pickle
import time
from typing import Dict, List

import requests

from api.exceptions import DKBApiError


class DKBApi:
    base_url = 'https://banking.dkb.de'
    api_prefix = '/api'
    mfa_method = 'seal_one'
    session_timeout = -1
    session = None
    account_Dict = None
    mfa_token = None

    def __init__(self, dkb_user: str, dkb_password: str, mfa_device_idx: int = None):
        """
        DKB API client handler.

        Args:
            dkb_user: Your DKB Username.
            dkb_password: Your DKB Password.
            mfa_device_idx: Integer, indicating which mfa device you want to use to authenticate. Interactive selection,
                            if set to None. Should be zero if you have only one active mfa device.
        """
        self.dkb_user = dkb_user
        self.dkb_password = dkb_password
        self.mfa_device_idx = mfa_device_idx

    def _new_session(self) -> requests.Session:
        # Setup header that mimics typical browser request to avoid being blocked or detection as a bot by the server.
        headers = {
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                      'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0'}
        session = requests.session()
        session.headers = headers

        session.get(self.base_url + '/login')

        # the /login get request returns a cookie, containing a CSRF token. This token should be used in every future
        # request because the server validates it to ensure that the request is legitimate and originated from an
        # authenticated user.
        if '__Host-xsrf' in session.cookies:
            headers['x-xsrf-token'] = session.cookies['__Host-xsrf']
            session.headers = headers

        return session

    def _get_token(self) -> Dict:
        """Request 1fa access token."""
        data_dict = {'grant_type': 'banking_user_sca', 'username': self.dkb_user, 'password': self.dkb_password,
                     'sca_type': 'web-login'}
        response = self.session.post(self.base_url + self.api_prefix + '/token', data=data_dict)
        if response.status_code == 200:
            mfa_token = response.json()
            if 'access_token' not in mfa_token:
                raise DKBApiError('No 1fa access token available.')
            else:
                return mfa_token
        else:
            raise DKBApiError(f'Login failed: 1st factor authentication failed. RC: {response.status_code}')

    def _get_mfa_devices(self) -> Dict[str, List[Dict[str, str | Dict[str, str]]]]:
        response = self.session.get(
            self.base_url + self.api_prefix + f'/mfa/mfa/methods?filter%5BmethodType%5D={self.mfa_method}')
        if response.status_code == 200:
            return response.json()
        else:
            raise DKBApiError(f'Requesting available mfa devices failed. RC: {response.status_code}')

    @staticmethod
    def _sort_mfa_devices(mfa_dict: Dict) -> Dict[str, List[Dict[str, str | Dict[str, str]]]]:
        """ sort mfa devices by preferred device and age."""
        device_list = mfa_dict['data']
        device_list.sort(key=lambda x: (-x['attributes']['preferredDevice'], x['attributes']['enrolledAt']))
        return {'data': device_list}

    @staticmethod
    def _select_mfa_device(mfa_dict: Dict[str, List[Dict[str, str | Dict[str, str]]]]) -> int:
        device_idx_list = [idx for idx in range(0, len(mfa_dict['data']))]
        device_selection_completed = False
        while not device_selection_completed:
            print('\nPick an authentication device from the list below:')
            for idx, device_dict in enumerate(mfa_dict['data']):
                print(f"[{idx}] - {device_dict['attributes']['deviceName']}")

            _tmp_device_num = input(':')
            try:
                if int(_tmp_device_num) in device_idx_list:
                    device_num = int(_tmp_device_num)
                    return device_num
                else:
                    print(f'\n{_tmp_device_num} not in list of available devices!')
            except ValueError:
                print(f"Invalid input {_tmp_device_num}. Expect integer.")

    def authenticate_user(self) -> None:
        """Iterate through all authentication steps, including 2fa."""
        self.mfa_token = self._get_token()

        mfa_devices = self._get_mfa_devices()
        mfa_devices = self._sort_mfa_devices(mfa_devices)

        if self.mfa_device_idx is None:
            self.mfa_device_idx = self._select_mfa_device(mfa_devices)

        with open('session_cookies.pkl', 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def login(self):
        """ login into DKB banking area and perform 2-factor authentication."""
        self.session = self._new_session()
        if os.path.isfile('session_cookies.pkl'):
            with open('session_cookies.pkl', 'rb') as f:
                session_cookies = pickle.load(f)
            if int(time.time()) - session_cookies._now < self.session_timeout:
                self.session.cookies.update(session_cookies)
            else:
                self.authenticate_user()
        else:
            self.authenticate_user()
