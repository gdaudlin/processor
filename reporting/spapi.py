import base64
import os
import sys
import json
import logging
import requests
import datetime as dt
import pandas as pd
import reporting.utils as utl
import spotipy
from spotipy import oauth2

config_path = utl.config_path
# replace later, my test client_details
account_id = ''
client_id = 'cfb799e8647a4ad4b5767f6ef17b59ca'
client_secret = '45779f45eefd41328018232e4fe871b0'
redirect_uri = 'http://localhost:8080/callback'
token_url = 'https://accounts.spotify.com/api/token'
api_base_url = 'https://api-partner.spotify.com/ads/v2/'
auth_url = ('https://accounts.spotify.com/authorize/?client_id={}'
            '&response_type=code&redirect_uri={}').format(client_id,
                                                          redirect_uri)
report_url = 'ad_accounts/{}/aggregate_reports'.format(account_id)
full_url = api_base_url + report_url
sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri)


class SpApi(object):
    def __init__(self):
        self.config = None
        self.config_file = None
        self.client_id = 'cfb799e8647a4ad4b5767f6ef17b59ca'
        self.client_secret = '45779f45eefd41328018232e4fe871b0'
        self.access_token = None
        self.refresh_token = None
        self.act_id = None
        self.config_list = None
        self.client = None
        self.df = pd.DataFrame()
        self.r = None

    def get_token(self):
        code = spotipy.oauth2.SpotifyClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret)
        code = code.get_access_token()
        access_token = code['access_token']
        return access_token

    @staticmethod
    def get_header(acc_token):
        return {'Authorization': 'Bearer ' + acc_token}

    def get_report(self, acc_token):
        header = self.get_header(acc_token)
        r = requests.get(full_url, headers=header)
        if r.status_code == 200:
            return r.json()
        else:
            logging.error('Error: {}'.format(r.status_code))
            print(r.text)

    def get_account_ids(self, acc_token):
        headers = self.get_header(acc_token)
        url = 'https://api-partner.spotify.com/ads/v2/ad_accounts'
        r = requests.get(url, headers=headers)
        return r


ac_token = SpApi.get_token(SpApi())
account_ids = SpApi.get_account_ids(SpApi(), ac_token)
data = SpApi.get_report(SpApi(), ac_token)
print(data)
