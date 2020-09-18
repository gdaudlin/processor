import os
import sys
import json
import time
import logging
import requests
import pandas as pd
import datetime as dt
import reporting.utils as utl

config_path = utl.config_path


class TikApi(object):
    base_url = 'https://ads.tiktok.com'
    ad_url = '/open_api/v1.1/ad/get/'
    ad_report_url = '/open_api/v1.1/audience/ad/get/'
    dimensions = ['COUNTRY', 'DAY', 'ID']
    metrics = ['click_cnt', 'conversion_cost', 'conversion_rate', 'convert_cnt',
               'ctr', 'show_cnt', 'stat_cost', 'time_attr_convert_cnt']

    def __init__(self):
        self.config = None
        self.config_file = None
        self.access_token = None
        self.advertiser_id = None
        self.campaign_id = None
        self.ad_id_list = []
        self.config_list = None
        self.headers = None
        self.version = '2'
        self.df = pd.DataFrame()
        self.r = None

    def input_config(self, config):
        if str(config) == 'nan':
            logging.warning('Config file name not in vendor matrix.  '
                            'Aborting.')
            sys.exit(0)
        logging.info('Loading Tik config file: {}'.format(config))
        self.config_file = os.path.join(config_path, config)
        self.load_config()
        self.check_config()

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except IOError:
            logging.error('{} not found.  Aborting.'.format(self.config_file))
            sys.exit(0)
        self.access_token = self.config['access_token']
        self.config_list = [self.config, self.access_token]
        if 'advertiser_id' in self.config:
            self.advertiser_id = self.config['advertiser_id']
        if 'campaign_id' in self.config:
            self.campaign_id = self.config['campaign_id']

    def check_config(self):
        for item in self.config_list:
            if item == '':
                logging.warning('{} not in Tik config file.'
                                'Aborting.'.format(item))
                sys.exit(0)

    def set_headers(self):
        self.headers = {'Access-Token': self.access_token}

    def make_request(self, url, method, headers=None, json_body=None, data=None,
                     params=None, attempt=1):
        if not json_body:
            json_body = {}
        if not headers:
            headers = {}
        if not data:
            data = {}
        if not params:
            params = {}
        if method == 'POST':
            request_method = requests.post
        else:
            request_method = requests.get
        try:
            r = request_method(url, headers=headers, json=json_body, data=data,
                               params=params)
        except requests.exceptions.ConnectionError as e:
            attempt += 1
            if attempt > 100:
                logging.warning('Could not connection with error: {}'.format(e))
                r = None
            else:
                logging.warning('Connection error, pausing for 60s '
                                'and retrying: {}'.format(e))
                time.sleep(60)
                r = self.make_request(url, method, headers, json_body, attempt)
        return r

    @staticmethod
    def date_check(sd, ed):
        if sd > ed or sd == ed:
            logging.warning('Start date greater than or equal to end date.  '
                            'Start date was set to end date.')
            sd = ed - dt.timedelta(days=1)
        sd = dt.datetime.strftime(sd, '%Y-%m-%d')
        ed = dt.datetime.strftime(ed, '%Y-%m-%d')
        return sd, ed

    def get_data_default_check(self, sd, ed):
        if sd is None:
            sd = dt.datetime.today() - dt.timedelta(days=2)
        if ed is None:
            ed = dt.datetime.today() + dt.timedelta(days=1)
        if dt.datetime.today().date() == ed.date():
            ed += dt.timedelta(days=1)
        sd, ed = self.date_check(sd, ed)
        return sd, ed

    def get_ad_ids(self):
        self.set_headers()
        url = self.base_url + self.ad_url
        params = {'advertiser_id': self.advertiser_id, 'page_size': 1000}
        ad_ids = []
        for x in range(1, 100):
            params['page'] = x
            r = self.make_request(url, method='GET', headers=self.headers,
                                  params=params)
            ad_list = r.json()['data']['list']
            self.ad_id_list.extend(ad_list)
            ad_ids.extend([x['ad_id'] for x in ad_list])
            if x >= r.json()['data']['page_info']['total_page']:
                break
        ad_ids = [ad_ids[x:x + 100] for x in range(0, len(ad_ids), 100)]
        return ad_ids

    def request_and_get_data(self, sd, ed, ad_ids):
        url = self.base_url + self.ad_report_url
        params = {'advertiser_id': self.advertiser_id, 'start_date': sd,
                  'end_date': ed, 'dimensions': json.dumps(self.dimensions),
                  'fields': json.dumps(self.metrics)}
        for idx, ad_id_list in enumerate(ad_ids):
            logging.info('Getting data from {} to {}.  Data pull {} of {}'
                         ''.format(sd, ed, idx + 1, len(ad_id_list)))
            params['ad_ids'] = json.dumps(ad_id_list)
            r = self.make_request(url=url, method='GET', headers=self.headers,
                                  params=params)
            df = pd.DataFrame(
                list(pd.DataFrame(r.json()['data']['list'])['dimensions']))
            df = df.join(pd.DataFrame(
                list(pd.DataFrame(r.json()['data']['list'])['metrics'])))
            self.df = self.df.append(df, ignore_index=True)
        self.df = self.df.merge(pd.DataFrame(self.ad_id_list), on='ad_id',
                                how='left')
        logging.info('Data successfully pulled.  Returning df.')
        return self.df

    def get_data(self, sd=None, ed=None, fields=None):
        sd, ed = self.get_data_default_check(sd, ed)
        ad_ids = self.get_ad_ids()
        self.df = self.request_and_get_data(sd, ed, ad_ids)
        return self.df