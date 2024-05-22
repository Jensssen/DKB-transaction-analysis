import json
import os
import pickle
import time
from typing import Dict, List, Tuple

import requests

from api.exceptions import DKBApiError


class DKBApi:
    base_url = 'https://banking.dkb.de'
    api_prefix = '/api'
    mfa_method = 'seal_one'
    session_timeout = 600
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
            if 'access_token' not in mfa_token or 'mfa_id' not in mfa_token:
                raise DKBApiError('No 1fa access token available.')
            else:
                return mfa_token
        else:
            raise DKBApiError(f'1st factor authentication request failed with response code: {response.status_code}')

    def _get_mfa_devices(self) -> Dict[str, List[Dict[str, str | Dict[str, str | int]]]]:
        response = self.session.get(
            self.base_url + self.api_prefix + f'/mfa/mfa/methods?filter%5BmethodType%5D={self.mfa_method}')
        if response.status_code == 200:
            return response.json()
        else:
            raise DKBApiError(f'Requesting available mfa devices failed with response code: {response.status_code}')

    @staticmethod
    def _sort_mfa_devices(mfa_dict: Dict) -> Dict[str, List[Dict[str, str | Dict[str, str | int]]]]:
        """ sort mfa devices by preferred device and age."""
        device_list = mfa_dict['data']
        device_list.sort(key=lambda x: (-x['attributes']['preferredDevice'], x['attributes']['enrolledAt']))
        return {'data': device_list}

    @staticmethod
    def _select_mfa_device(mfa_dict: Dict[str, List[Dict[str, str | Dict[str, str | int]]]]) -> int:
        device_idx_list = [idx for idx in range(0, len(mfa_dict['data']))]
        device_selection_completed = False
        while not device_selection_completed:
            print('\nPick an authentication device from the list below:')
            for idx, device_dict in enumerate(mfa_dict['data']):
                print(f"[{idx}] - {device_dict['attributes']['deviceName']}")

            _tmp_device_idx = input(':')
            try:
                if int(_tmp_device_idx) in device_idx_list:
                    return int(_tmp_device_idx)
                else:
                    print(f'\n{_tmp_device_idx} not in list of available devices!')
            except ValueError:
                print(f"Invalid input {_tmp_device_idx}. Expect integer.")

    def _get_mfa_challenge_id(self, mfa_dict: Dict[str, str | Dict[str, str | int]]) -> Tuple[str, str]:
        """Get challenge Dict with information on the 2nd factor"""
        try:
            try:
                device_name = mfa_dict['attributes']['deviceName']
            except KeyError:
                print('Device Name in selected mfa device not found.')
                device_name = "Unknown Device"

            self.session.headers['Content-Type'] = 'application/vnd.api+json'
            self.session.headers["Accept"] = 'application/vnd.api+json'

            data_dict = {'data': {'type': 'mfa-challenge', 'attributes': {'mfaId': self.mfa_token['mfa_id'],
                                                                          'methodId': mfa_dict['id'],
                                                                          'methodType': self.mfa_method}}}
            response = self.session.post(self.base_url + self.api_prefix + '/mfa/mfa/challenges',
                                         data=json.dumps(data_dict))

            if response.status_code in (200, 201):
                challenge_dict = response.json()
                if 'data' in challenge_dict and 'id' in challenge_dict['data'] and 'type' in challenge_dict['data']:
                    if challenge_dict['data']['type'] == 'mfa-challenge':
                        # we remove the headers we added earlier
                        self.session.headers.pop('Content-Type')
                        self.session.headers.pop('Accept')
                        return challenge_dict['data']['id'], device_name
                    else:
                        raise DKBApiError(
                            f"Challenge type should be mfa-challenge but is {challenge_dict['data']['type']}")
                else:
                    raise DKBApiError(f'MFA challenge response format has missing keys: {challenge_dict}')
            else:
                raise DKBApiError(f'MFA challenge request failed with response code: {response.status_code}')

        except KeyError:
            raise 'The selected mfa device has an unexpected data structure.'

    @staticmethod
    def _check_processing_status(polling_dict: Dict[str, Dict[str, str | Dict[str, str]]]) -> bool:
        if (polling_dict['data']['attributes']['verificationStatus']) == 'processed':
            return True
        elif (polling_dict['data']['attributes']['verificationStatus']) == 'canceled':
            raise DKBApiError('2 factor authentication got canceled by user or timeout')
        return False

    def _complete_2fa(self, challenge_id: str, device_name: str) -> bool:
        """
        Loop for 50 seconds and check the 2fa status of the user every 5 seconds. If the status changes to \"processed\"
        the 2fa was successfully.
        """
        print(f'Check your banking app on "{device_name}" and confirm login...')
        cnt = 0
        mfa_completed = False
        while cnt <= 10:
            response = self.session.get(self.base_url + self.api_prefix + f"/mfa/mfa/challenges/{challenge_id}")
            cnt += 1
            if response.status_code == 200:
                mfa_auth_status = response.json()
                if 'data' in mfa_auth_status and 'attributes' in mfa_auth_status['data'] and 'verificationStatus' in \
                        mfa_auth_status['data']['attributes']:
                    mfa_completed = self._check_processing_status(mfa_auth_status)
                    if mfa_completed:
                        break
                else:
                    raise DKBApiError(f'MFA challenge status response format has missing keys: {mfa_auth_status}')
            else:
                raise DKBApiError(f'MFA challenge status request failed with response code: {response.status_code}')
            time.sleep(5)
        return mfa_completed

    def _update_token(self):
        """Update token information with 2fa information."""
        data_dict = {'grant_type': 'banking_user_mfa', 'mfa_id': self.mfa_token['mfa_id'],
                     'access_token': self.mfa_token['access_token']}
        response = self.session.post(self.base_url + self.api_prefix + '/token', data=data_dict)
        if response.status_code == 200:
            self.token_dict = response.json()
        else:
            raise DKBApiError(f'Token update failed with status code: {response.status_code}')

    def authenticate_user(self) -> None:
        """Iterate through all authentication steps, including 2fa."""
        self.mfa_token = self._get_token()

        mfa_devices = self._get_mfa_devices()
        mfa_devices = self._sort_mfa_devices(mfa_devices)

        if self.mfa_device_idx is None:
            self.mfa_device_idx = self._select_mfa_device(mfa_devices)

        mfa_challenge_id, device_name = self._get_mfa_challenge_id(mfa_devices["data"][self.mfa_device_idx])

        mfa_completed = self._complete_2fa(mfa_challenge_id, device_name)

        # update token Dictionary
        if mfa_completed:
            self._update_token()
        else:
            raise DKBApiError('Login failed: mfa did not complete')

        if self.token_dict['token_factor_type'] != '2fa':
            raise DKBApiError('Login failed: 2nd factor authentication did not complete')

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

    def get_accounts(self) -> Dict[str, List[Dict[str, str]]]:
        response = self.session.get(self.base_url + self.api_prefix + '/accounts/accounts')
        if response.status_code == 200:
            return response.json()
        else:
            raise DKBApiError(f'Requesting accounts failed with response code {response.status_code}')
