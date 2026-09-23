import os
import time
import logging
import pandas as pd
import datetime as dt
import processor.reporting.fbapi as fbapi
import processor.reporting.awapi as awapi
import processor.reporting.twapi as twapi
import processor.reporting.gaapi as gaapi
import processor.reporting.nbapi as nbapi
import processor.reporting.afapi as afapi
import processor.reporting.scapi as scapi
import processor.reporting.ajapi as ajapi
import processor.reporting.dcapi as dcapi
import processor.reporting.rsapi as rsapi
import processor.reporting.dbapi as dbapi
import processor.reporting.vkapi as vkapi
import processor.reporting.rcapi as rcapi
import processor.reporting.ttdapi as ttdapi
import processor.reporting.szkapi as szkapi
import processor.reporting.redapi as redapi
import processor.reporting.dvapi as dvapi
import processor.reporting.adkapi as adkapi
import processor.reporting.innapi as innapi
import processor.reporting.tikapi as tikapi
import processor.reporting.amzapi as amzapi
import processor.reporting.criapi as criapi
import processor.reporting.pmapi as pmapi
import processor.reporting.samapi as samapi
import processor.reporting.gsapi as gsapi
import processor.reporting.qtapi as qtapi
import processor.reporting.yvapi as yvapi
import processor.reporting.ssapi as ssapi
import processor.reporting.nzapi as nzapi
import processor.reporting.ytdapi as ytdapi
import processor.reporting.simapi as simapi
import processor.reporting.pixapi as pixapi
import processor.reporting.iasapi as iasapi
import processor.reporting.steapi as steapi
import processor.reporting.asaapi as asaapi
import processor.reporting.ftp as ftp
import processor.reporting.awss3 as awss3
import processor.reporting.azapi as azu
import processor.reporting.export as export
import processor.reporting.vmcolumns as vmc
import processor.reporting.vendormatrix as vm
import processor.reporting.utils as utl


class ImportHandler(object):
    def __init__(self, args, matrix):
        self.args = args
        self.matrix = matrix
        self.class_list = {
            vmc.api_fb_key: fbapi.FbApi,
            vmc.api_aw_key: awapi.AwApi,
            vmc.api_goad_key: awapi.AwApi,
            vmc.api_tw_key: twapi.TwApi,
            vmc.api_ttd_key: ttdapi.TtdApi,
            vmc.api_ga_key: gaapi.GaApi,
            vmc.api_nb_key: nbapi.NbApi,
            vmc.api_af_key: afapi.AfApi,
            vmc.api_sc_key: scapi.ScApi,
            vmc.api_aj_key: ajapi.AjApi,
            vmc.api_dc_key: dcapi.DcApi,
            vmc.api_db_key: dbapi.DbApi,
            vmc.api_dvo_key: dbapi.DbApi,
            vmc.api_vk_key: vkapi.VkApi,
            vmc.api_rs_key: rsapi.RsApi,
            vmc.api_rc_key: rcapi.RcApi,
            vmc.api_szk_key: szkapi.SzkApi,
            vmc.api_red_key: redapi.RedApi,
            vmc.api_dv_key: dvapi.DvApi,
            vmc.api_adk_key: adkapi.AdkApi,
            vmc.api_inn_key: innapi.InnApi,
            vmc.api_tik_key: tikapi.TikApi,
            vmc.api_amz_key: amzapi.AmzApi,
            vmc.api_cri_key: criapi.CriApi,
            vmc.api_pm_key: pmapi.PmApi,
            vmc.api_sam_key: samapi.SamApi,
            vmc.api_gs_key: gsapi.GsApi,
            vmc.api_qt_key: qtapi.QtApi,
            vmc.api_yv_key: yvapi.YvApi,
            vmc.api_amd_key: amzapi.AmzApi,
            vmc.api_ss_key: ssapi.SsApi,
            vmc.api_nz_key: nzapi.NzApi,
            vmc.api_ytd_key: ytdapi.YtdApi,
            vmc.api_wal_key: ttdapi.TtdApi,
            vmc.api_sim_key: simapi.SimApi,
            vmc.api_pix_key: pixapi.PixApi,
            vmc.api_ias_key: iasapi.IasApi,
            vmc.api_ste_key: steapi.SteApi,
            vmc.api_asa_key: asaapi.AsaApi,
        }

    @staticmethod
    def raw_file_path(filename):
        """
        Resolves a card's FILENAME to the path it is written to.

        :param filename: the card's FILENAME, bare or already a path
        :returns: the path under raw_path, or the path given
        """
        if '/' in filename:
            return filename
        return os.path.join(utl.raw_path, filename)

    def output(self, api_df, filename, api_merge=None, first_row=None,
               last_row=None, date_col=None, start_date=None, end_date=None,
               merge=False):
        """Writes a df to disk from an API

        When the pull covered only the tail of the file's history, the
        rows the file already holds for earlier dates are kept and the
        pulled window is replaced.  A card with API_MERGE set is merged
        the same way over the window its caller derived from it.  With
        neither, the file is overwritten as it always was.

        :param api_df: the dataframe to be written
        :param filename: the file to write, relative to raw_path
        :param api_merge: the card's API_MERGE days, nan when unset
        :param first_row: the card's FIRSTROW, nan when unset
        :param last_row: the card's LASTROW, nan when unset
        :param date_col: the card's DATE column list
        :param start_date: the start the pull actually asked for
        :param end_date: the end the pull asked for, None when open
        :param merge: True when only start_date to end_date was pulled
        """
        utl.dir_check(utl.raw_path)
        full_file = self.raw_file_path(filename)
        if merge or str(api_merge) != 'nan':
            api_df = self.merge_df(api_df, full_file, date_col,
                                   (start_date, end_date), first_row,
                                   last_row)
        self.write_df(api_df, full_file)

    def write_df(self, api_df, full_file, attempt=0):
        if not api_df.empty:
            file_written = utl.write_file(api_df, full_file)
            if not file_written:
                logging.warning('{} could not be opened.  API data was '
                                'not saved will attempt {} '
                                'more times.'.format(full_file, 4 - attempt))
                attempt += 1
                if attempt < 5:
                    time.sleep(15)
                    self.write_df(api_df, full_file, attempt)
        else:
            logging.warning('Imported df empty - '
                            'not overwriting {}.'.format(full_file))

    def load_output(self, df, params):
        """
        Writes a report a loader fetched whole, merging it when the card
        sets API_MERGE.

        The FTP, database, S3 and Azure loaders take no dates, so the
        window to replace is the trailing API_MERGE days up to the
        card's end, and the report still carries the FIRSTROW rows the
        loader put on it.

        :param df: the report as the loader returned it
        :param params: the card's vendor matrix parameters
        """
        api_merge = params[vmc.apimerge]
        first_row, last_row = params[vmc.firstrow], params[vmc.lastrow]
        sd, ed = params[vmc.startdate], params[vmc.enddate]
        merge = str(api_merge) != 'nan'
        if merge:
            ed = self.pull_end(ed)
            sd = ed - dt.timedelta(days=int(api_merge))
            df = utl.first_last_adj(df, 0 if pd.isna(first_row) else first_row,
                                    0 if pd.isna(last_row) else last_row)
        self.output(df, params[vmc.filename], api_merge, first_row, last_row,
                    params[vmc.date], sd, ed, merge=merge)

    @staticmethod
    def merge_date_col(date_col):
        """
        Picks the column name a merge keys dates on, or None.

        The vendor matrix hands DATE over as a one item list, and an
        unset DATE arrives as the list ['nan'] rather than None.

        :param date_col: the card's DATE parameter
        :returns: the column name, or None when no usable one was set
        """
        if isinstance(date_col, str):
            date_col = [date_col]
        if not isinstance(date_col, list) or not date_col:
            return None
        col = str(date_col[0])
        if col in ('', 'nan', 'None'):
            return None
        return col

    def merge_df(self, api_df, filename, date_col, window, first_row,
                 last_row):
        """
        Folds a fresh pull into the raw file without losing history.

        File rows dated inside the pulled window are replaced and the
        rest kept; fresh rows dated outside it are dropped so they cannot
        double the kept rows.  Undated rows, such as totals, come from
        the fresh pull alone.  An empty pull, or one the file cannot be
        keyed against, leaves the file as it was.

        :param api_df: the fresh pull
        :param filename: the existing raw file
        :param date_col: the card's DATE parameter
        :param window: (start, end) the pull asked for, end may be None
        :param first_row: the card's FIRSTROW, nan tolerated
        :param last_row: the card's LASTROW, nan tolerated
        :returns: the merged dataframe, or the pull when no file exists
        """
        if not os.path.isfile(filename) or api_df is None or api_df.empty:
            return api_df
        sd, ed = window
        col = self.merge_date_col(date_col)
        if not col or sd is None or sd is pd.NaT:
            logging.warning(f'{filename} has no DATE column or start date '
                            'to keep its history apart from the new pull; '
                            'writing the pull as is.')
            return api_df
        first_row = 0 if pd.isna(first_row) else int(first_row)
        last_row = 0 if pd.isna(last_row) else int(last_row)
        df = utl.import_read_csv(filename)
        if df is None or df.empty:
            return api_df
        df = utl.first_last_adj(df, first_row, last_row)
        df = utl.data_to_type(df, date_col=[col], fill_empty=False)
        api_df = utl.data_to_type(api_df, date_col=[col], fill_empty=False)
        if col not in df.columns:
            logging.warning(f'{filename} has no {col} column to keep its '
                            'history apart from the new pull; writing the '
                            'pull as is.')
            return api_df
        if col not in api_df.columns:
            logging.warning(f'The pull for {filename} has no {col} column '
                            'and cannot be merged; the file is kept as is.')
            return api_df.iloc[0:0]
        kept = df[~utl.date_in_window(df[col], sd, ed) & df[col].notna()]
        inside = utl.date_in_window(api_df[col], sd, ed) | api_df[col].isna()
        if (~inside).any():
            logging.info(f'{int((~inside).sum())} rows of the pull fall '
                         'outside the window asked for and are dropped.')
        api_df = api_df[inside]
        logging.info(f'Keeping {len(kept)} rows of history and adding '
                     f'{len(api_df)} fresh rows to {filename}.')
        df = pd.concat([kept, api_df], ignore_index=True,
                       sort=False).reset_index(drop=True)
        df = utl.add_dummy_header(df, first_row)
        df = utl.add_dummy_header(df, last_row, location='foot')
        return df

    @staticmethod
    def create_all_col(df):
        df['ALL'] = ''
        for col in df.columns:
            df['ALL'] = df['ALL'] + df[col].astype('U')
        return df

    def arg_check(self, arg_check):
        if isinstance(self.args, str):
            args = [self.args]
        else:
            args = self.args
        if arg_check in args or 'all' in self.args:
            return True
        else:
            return False

    @staticmethod
    def date_check(date):
        if date.date() is pd.NaT:
            return True
        return False

    @staticmethod
    def pull_end(ed):
        """
        The last day a pull may ask for: the card's end, or today when
        the end is open, unparsable or still in the future.

        :param ed: the card's END DATE as api_calls sees it
        :returns: a Timestamp on or before today
        """
        today = pd.Timestamp(dt.date.today())
        if ed is None or ed is pd.NaT:
            return today
        return min(pd.Timestamp(ed), today)

    @staticmethod
    def set_start(sd, ed, max_date):
        """
        Shortens a card's start to its API_MERGE window.

        An open or future end date reads as today, which is as far as
        any API can serve; without that an API_MERGE card could be
        asked for a window that has not happened yet.

        :param sd: the card's start date
        :param ed: the card's end date, None when open
        :param max_date: the card's API_MERGE days, nan when unset
        :returns: the start date to pull from
        """
        if str(max_date) == 'nan' or sd is None:
            return sd
        ed = ImportHandler.pull_end(ed)
        date_diff = (ed - sd).days
        if date_diff >= max_date:
            sd = ed - dt.timedelta(days=int(max_date))
        return sd

    @staticmethod
    def date_cap(api_class, fields):
        """
        The most days the API serves in one report, or None when the
        card's fields ask for lifetime or total rows, which carry no
        dates to cut or merge on.

        :param api_class: the configured API instance
        :param fields: the card's API_FIELDS, None when unset
        :returns: the cap in days, or None for an uncapped pull
        """
        undated = getattr(api_class, 'undated_fields', ())
        if fields and set(fields) & set(undated):
            return None
        return getattr(api_class, 'max_date_length', None)

    @staticmethod
    def piece_days(max_days):
        """
        Days one pull may span: one short of the API's cap, so an API
        that bumps a same-day end to tomorrow still fits inside it.

        :param max_days: the API's max_date_length
        :returns: the days a piece may cover, at least one
        """
        return max(max_days - 1, 1)

    @staticmethod
    def pull_window(api_class, sd, ed, api_merge, filename, fields=None,
                    date_col=None):
        """
        Decides what part of a card's window one run should pull.

        A card longer than its API serves in one report is pulled in
        full, in pieces, only while it has no raw file.  After that each
        run asks for the trailing piece and merges it, so history the
        platform no longer serves is never re-requested or lost.  A card
        with API_MERGE keeps the window set_start gave it.  An uncapped
        card, one that fits in a piece, or one with no DATE column to
        merge on, is left as it was.

        :param api_class: the configured API instance
        :param sd: the card's start, already through set_start
        :param ed: the card's end; open, unparsable and future ends
            read as today
        :param api_merge: the card's API_MERGE days, nan when unset
        :param filename: the raw file the card writes to
        :param fields: the card's API_FIELDS, None when unset
        :param date_col: the card's DATE parameter, None when unset
        :returns: the pull start, the pull end, and whether to merge
        """
        max_days = ImportHandler.date_cap(api_class, fields)
        has_file = os.path.isfile(filename)
        merge = has_file and str(api_merge) != 'nan'
        if not max_days or sd is None or sd is pd.NaT:
            return sd, ed, merge
        piece = ImportHandler.piece_days(max_days)
        last = ImportHandler.pull_end(ed)
        if (last - pd.Timestamp(sd)).days < piece:
            return sd, ed, merge
        keyed = ImportHandler.merge_date_col(date_col) is not None
        if not has_file or merge or not keyed:
            return sd, last, merge
        return last - dt.timedelta(days=piece - 1), last, True

    @staticmethod
    def get_data_in_windows(api_class, sd, ed, fields, vk):
        """
        Pulls a window from an API in pieces it can serve.

        A window longer than the API's cap is cut into pieces one day
        short of it, none reaching past today, each pulled with its own
        get_data call, and the frames concatenated.  A window that fits,
        or an uncapped pull, is one call with the dates untouched, so an
        open end still reaches the API as it always did.

        :param api_class: the configured API instance
        :param sd: the start to pull from
        :param ed: the end to pull to, None when open
        :param fields: the card's API_FIELDS
        :param vk: the vendor key, for the log line
        :returns: the concatenated dataframe, empty when nothing came
        """
        max_days = ImportHandler.date_cap(api_class, fields)
        split_ed = ed
        if max_days:
            split_ed = ImportHandler.pull_end(ed)
            max_days = ImportHandler.piece_days(max_days)
        windows = utl.split_date_range(sd, split_ed, max_days)
        if len(windows) == 1:
            df = api_class.get_data(sd=sd, ed=ed, fields=fields)
            return pd.DataFrame() if df is None else df
        logging.info(f'{vk} is pulled in {len(windows)} pieces of at most '
                     f'{max_days} days.')
        frames = []
        for piece_sd, piece_ed in windows:
            df = api_class.get_data(sd=piece_sd, ed=piece_ed, fields=fields)
            if df is None or df.empty:
                logging.warning(f'{vk} returned no rows for '
                                f'{piece_sd:%Y-%m-%d} to {piece_ed:%Y-%m-%d}; '
                                'if the API failed, delete the raw file to '
                                'pull the card in full again.')
                continue
            frames.append(df)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True, sort=False)

    def api_calls(self, key_list, api_class):
        """Makes an API Call

        Keyword arguments:
        key_list -- list of Vendormatrix keys for a given API
        api_class -- The class of API to call
        """
        stats_by_vk = {}
        for vk in key_list:
            params = self.matrix.vendor_set(vk)
            try:
                api_class.input_config(params[vmc.apifile])
            except (FileNotFoundError, ValueError, SystemExit) as e:
                logging.warning(e)
                continue
            # Clear records a previous key's failure left behind,
            # so nothing is attributed to the wrong card.
            utl.drain_campaign_filter_stats()
            start_check = self.date_check(params[vmc.startdate])
            end_check = self.date_check(params[vmc.enddate])
            if params[vmc.apifields] == ['nan']:
                params[vmc.apifields] = None
            if start_check:
                params[vmc.startdate] = None
            if end_check:
                params[vmc.enddate] = None
            params[vmc.startdate] = self.set_start(params[vmc.startdate],
                                                   params[vmc.enddate],
                                                   params[vmc.apimerge])
            full_file = self.raw_file_path(params[vmc.filename])
            pull_sd, pull_ed, merge = self.pull_window(
                api_class, params[vmc.startdate], params[vmc.enddate],
                params[vmc.apimerge], full_file, params[vmc.apifields],
                params[vmc.date])
            df = pd.DataFrame()
            try:
                df = self.get_data_in_windows(api_class, pull_sd, pull_ed,
                                              params[vmc.apifields], vk)
            except Exception as e:
                logging.error("API error occurred", exc_info=True)
                if hasattr(api_class, 'sw') and api_class.sw:
                    api_class.sw.quit()
                else:
                    raise e
            self.output(df, params[vmc.filename], params[vmc.apimerge],
                        params[vmc.firstrow], params[vmc.lastrow],
                        params[vmc.date], pull_sd, pull_ed, merge=merge)
            stat = utl.drain_campaign_filter_stats()
            if stat:
                stat['date'] = dt.datetime.today().strftime(
                    '%Y-%m-%d %H:%M:%S')
                stats_by_vk[vk] = stat
        utl.write_campaign_filter_stats(stats_by_vk)

    def api_loop(self):
        """Loops through all APIs and makes function call to retrieve data.

        """
        for key, api in self.class_list.items():
            if (self.arg_check(vmc.api_translation[key]) and
                    self.matrix.vks[key]):
                self.api_calls(self.matrix.vks[key], api())

    def test_api_calls(self, key_list):
        """Makes an API Call to Test Connection

        Keyword arguments:
        key_list -- list of Vendormatrix keys to test
        """
        import_config = vm.ImportConfig()
        import_config.import_vm()
        df = pd.DataFrame()
        for vk in key_list:
            data_source = self.matrix.get_data_source(vk=vk)
            config_name = str(data_source.params[import_config.config_file])
            api_type = vk.split('_')[1]
            api_class = self.class_list[api_type]()
            ic_df = import_config.df.loc[
                import_config.df[import_config.key] == api_type]
            acc_col = ic_df.iloc[0][import_config.account_id]
            camp_col = ic_df.iloc[0][import_config.filter]
            acc_pre = ic_df.iloc[0][import_config.account_id_pre]
            api_class.input_config(config_name)
            tdf = api_class.test_connection(acc_col, camp_col, acc_pre)
            tdf[vmc.vendorkey] = vk
            df = pd.concat([df, tdf])
        return df

    def ftp_load(self, ftp_key, ftp_class):
        for vk in ftp_key:
            params = self.matrix.vendor_set(vk)
            ftp_class.input_config(params[vmc.apifile])
            ftp_class.header = params[vmc.firstrow]
            df = ftp_class.get_data()
            self.load_output(df, params)

    def ftp_loop(self):
        if self.arg_check('sz'):
            self.ftp_load(self.matrix.ftp_sz_key, ftp.FTP())

    def db_load(self, db_key, db_class):
        for vk in db_key:
            params = self.matrix.vendor_set(vk)
            db_class.input_config(params[vmc.apifile])
            df = db_class.get_data(filename=params[vmc.apifields][0])
            self.load_output(df, params)

    def db_loop(self):
        if self.arg_check('dna'):
            self.db_load(self.matrix.db_dna_key, export.DB())

    def s3_load(self, s3_key, s3_class):
        for vk in s3_key:
            params = self.matrix.vendor_set(vk)
            s3_class.input_config(params[vmc.apifile])
            start_check = self.date_check(params[vmc.startdate])
            end_check = self.date_check(params[vmc.enddate])
            if start_check:
                params[vmc.startdate] = None
            if end_check:
                params[vmc.enddate] = None
            df = s3_class.get_data(sd=params[vmc.startdate],
                                   ed=params[vmc.enddate])
            self.load_output(df, params)

    def s3_loop(self):
        if self.arg_check('dna'):
            self.s3_load(self.matrix.s3_dna_key, awss3.S3())

    def azu_load(self, azu_key, azu_class):
        for vk in azu_key:
            params = self.matrix.vendor_set(vk)
            azu_class.input_config(params[vmc.apifile])
            azu_class.header = params[vmc.firstrow]
            df = azu_class.get_data()
            self.load_output(df, params)

    def azu_loop(self):
        if self.arg_check('dna'):
            self.azu_load(self.matrix.azu_dna_key, azu.AzuApi())
