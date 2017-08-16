import sys
import os.path
import logging
import pandas as pd
import cleaning as cln
import dictcolumns as dctc

csvpath = 'Dictionaries/'


class Dict(object):
    def __init__(self, filename):
        cln.dir_check(csvpath)
        if str(filename) == 'nan':
            logging.error('No dictionary file provided.  Aborting.')
            sys.exit(0)
        self.filename = filename
        self.dictfile = csvpath + self.filename
        self.data_dict = pd.DataFrame()
        self.read()

    def read(self):
        if not os.path.isfile(self.dictfile):
            logging.info('Creating ' + self.filename)
            if self.filename == dctc.PFN:
                data_dict = pd.DataFrame(columns=dctc.PCOLS, index=None)
            else:
                data_dict = pd.DataFrame(columns=dctc.COLS, index=None)
            data_dict.to_csv(self.dictfile, index=False)
        self.data_dict = pd.read_csv(self.dictfile)
        self.clean()

    def get(self):
        return self.data_dict

    def merge(self, df, colname):
        logging.info('Merging ' + self.filename)
        df = df.merge(self.data_dict, on=colname, how='left')
        return df

    def auto(self, err, autodicord, placement):
        error = err.get()
        if not autodicord == ['nan'] and not error.empty:
            logging.info('Populating ' + self.filename)
            i = 0
            for value in autodicord:
                error[value] = error[placement].str.split('_').str[i]
                i += 1
            error = error.ix[~error[dctc.FPN].isin(self.data_dict[dctc.FPN])]
            self.data_dict = self.data_dict.append(error)
            self.data_dict = self.data_dict[dctc.COLS]
            self.write()
            err.dic = self
            err.reset()
            self.clean()

    def apply_relation(self):
        rc = RelationalConfig()
        rc.read(dctc.filename_rel_config)
        self.data_dict = rc.loop(self.data_dict)
        self.write(self.data_dict)

    def apply_constants(self):
        dcc = DictConstantConfig()
        dcc.read(dctc.filename_con_config)
        self.data_dict = dcc.apply_constants_to_dict(self.data_dict)
        self.write(self.data_dict)

    def write(self, df=None):
        logging.debug('Writing ' + self.filename)
        if df is None:
            df = self.data_dict
        try:
            df.to_csv(self.dictfile, index=False)
        except IOError:
            logging.warn(self.filename + ' could not be opened.  ' +
                         'This dictionary was not saved.')

    def clean(self):
        self.data_dict = cln.data_to_type(self.data_dict, dctc.floatcol,
                                          dctc.datecol, dctc.strcol)


class RelationalConfig(object):
    def __init__(self):
        self.csvpath = 'Config/'
        cln.dir_check('Config/')
        self.df = pd.DataFrame()
        self.rc = None
        self.relational_params = None
        self.key_list = []

    def read(self, configfile):
        filename = self.csvpath + configfile
        try:
            self.df = pd.read_csv(filename)
        except IOError:
            logging.debug('No Relational Dictionary config')
            return None
        self.key_list = self.df[dctc.RK].tolist()
        self.rc = self.df.set_index(dctc.RK).to_dict()
        self.rc[dctc.DEP] = ({key: list(str(value).split('|')) for key, value
                              in self.rc[dctc.DEP].items()})

    def get_relation_params(self, relational_key):
        relational_params = {}
        for param in self.rc:
            value = self.rc[param][relational_key]
            relational_params[param] = value
        return relational_params

    def loop(self, data_dict):
        for key in self.key_list:
            self.relational_params = self.get_relation_params(key)
            dr = DictRelational(**self.relational_params)
            data_dict = dr.apply_to_dict(data_dict)
        return data_dict


class DictRelational(object):
    def __init__(self, **kwargs):
        self.csvpath = 'Dictionaries/Relational/'
        cln.dir_check(self.csvpath)
        self.df = pd.DataFrame()
        self.params = kwargs
        self.filename = self.params[dctc.FN]
        self.full_file_path = self.csvpath + self.filename
        self.key = self.params[dctc.KEY]
        self.dependents = self.params[dctc.DEP]
        self.columns = [self.key] + self.dependents

    def read(self):
        if not os.path.isfile(self.full_file_path):
            logging.info('Creating ' + self.filename)
            df = pd.DataFrame(columns=self.columns, index=None)
            df.to_csv(self.full_file_path, index=False)
        self.df = pd.read_csv(self.full_file_path)

    def add_key_values(self, data_dict):
        keys_list = pd.DataFrame(data_dict[self.key]).drop_duplicates()
        keys_list.dropna(subset=[self.key], inplace=True)
        self.df = self.df.merge(keys_list, how='outer').reset_index(drop=True)
        self.df.dropna(subset=[self.key], inplace=True)
        self.write(self.df)

    def write(self, df):
        logging.debug('Writing ' + self.filename)
        if df is None:
            df = self.df
        try:
            df.to_csv(self.full_file_path, index=False)
        except IOError:
            logging.warn(self.filename + ' could not be opened.  ' +
                         'This dictionary was not saved.')

    def apply_to_dict(self, data_dict):
        if self.key not in data_dict.columns:
            return data_dict
        self.read()
        self.add_key_values(data_dict)
        self.df.dropna()
        data_dict = data_dict.merge(self.df, on=self.key, how='left')
        for col in self.dependents:
            col_x = col + '_x'
            col_y = col + '_y'
            if col_y in data_dict.columns:
                data_dict[col] = data_dict[col_y]
                data_dict = data_dict.drop([col_x, col_y], axis=1)
        self.rename_y_columns(data_dict)
        data_dict = self.reorder_columns(data_dict)
        return data_dict

    @staticmethod
    def rename_y_columns(df):
        for x in df.columns:
            if x[-2:] == '_y':
                df.rename(columns={x: x[:-2]}, inplace=True)

    @staticmethod
    def reorder_columns(data_dict):
        if dctc.PNC in data_dict.columns:
            first_cols = [dctc.FPN, dctc.PNC]
            back_cols = [x for x in data_dict.columns if x not in first_cols]
            cols = first_cols + back_cols
        else:
            cols = [x for x in dctc.COLS if x in data_dict.columns]
        data_dict = data_dict[cols]
        return data_dict


class DictConstantConfig(object):
    def __init__(self):
        self.csvpath = 'Config/'
        cln.dir_check('Config/')
        self.df = pd.DataFrame()
        self.dict_col_names = None
        self.dict_col_values = None
        self.dict_constants = None

    def read(self, configfile):
        filename = self.csvpath + configfile
        try:
            self.df = pd.read_csv(filename)
        except IOError:
            logging.debug('No Constant Dictionary config')
            return None
        self.dict_col_names = self.df[dctc.DICT_COL_NAME].tolist()
        self.dict_constants = self.df.set_index(dctc.DICT_COL_NAME).to_dict()

    def get(self):
        return self.dict_constants

    def apply_constants_to_dict(self, data_dict):
        if self.dict_col_names is None:
            return data_dict
        for col in self.dict_col_names:
            constant_value = self.dict_constants[dctc.DICT_COL_VALUE][col]
            data_dict[col] = constant_value
        return data_dict


def dict_update():
    for filename in os.listdir(csvpath):
        if filename[-4:] != '.csv':
            continue
        if 'plannet' in filename:
            cols = dctc.PCOLS
        else:
            cols = dctc.COLS
        ndic = pd.DataFrame(columns=cols, index=None)
        dic = Dict(filename)
        odic = dic.get()
        df = ndic.append(odic)
        if 'pncFull Placement Name' in df.columns:
            df[dctc.FPN] = df['pncFull Placement Name']
            df = df[cols]
        df = df[cols]
        dic.write(df)
