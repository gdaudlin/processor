import os
import shutil
import pytest
from main import main
import reporting.utils as utl
import reporting.vmcolumns as vmc
import reporting.vendormatrix as vm
import reporting.dictcolumns as dctc


@pytest.fixture(scope='module')
def load_config():
    test_path = 'tests'
    tmp_path_str = 'tmp'
    file_name = 'end_to_end_config.xlsx'
    tmp_path = os.path.join(test_path, tmp_path_str)
    utl.dir_check(tmp_path)
    load_config = utl.import_read_csv(os.path.join(test_path, file_name))
    for old_path in [utl.config_path, utl.dict_path, utl.raw_path]:
        full_new_path = os.path.join(tmp_path, old_path)
        utl.dir_check(full_new_path)
        utl.dir_check(old_path)
        utl.copy_tree_no_overwrite(old_path, full_new_path, log=False,
                                   overwrite=True)
        if old_path != utl.config_path:
            shutil.rmtree(old_path)
        if old_path == utl.dict_path:
            new_t = os.path.join(full_new_path, dctc.filepath_tran_config)
            old_t = os.path.join(old_path, dctc.filepath_tran_config)
            utl.dir_check(old_t)
            utl.copy_tree_no_overwrite(new_t, old_t, log=False, overwrite=True)
    yield load_config
    for old_path in [utl.config_path, utl.dict_path, utl.raw_path]:
        utl.dir_check(old_path)
        full_new_path = os.path.join(tmp_path, old_path)
        utl.copy_tree_no_overwrite(full_new_path, old_path, log=False,
                                   overwrite=True)
        shutil.rmtree(full_new_path)


@pytest.mark.usefixtures('load_config')
class TestEndToEnd:
    def test_load_config(self, load_config):
        config_cols = [vm.ImportConfig.key, vm.ImportConfig.account_id,
                       vm.ImportConfig.filter, vm.ImportConfig.name,
                       vmc.startdate, vmc.enddate]
        assert config_cols == load_config.columns.to_list()

    def test_config_to_vm(self, load_config):
        for col in [vmc.vendorkey, vmc.apifields]:
            load_config[col] = ''
        cols = [vmc.startdate, vmc.enddate]
        load_config = utl.data_to_type(load_config, str_col=cols)
        load_config = load_config.to_dict(orient='records')
        ic = vm.ImportConfig()
        ic.add_and_remove_from_vm(load_config, matrix=True)
        matrix = vm.VendorMatrix()
        for x in load_config:
            vk_parts = (x[vm.ImportConfig.key], x[vm.ImportConfig.name])
            vk = 'API_{}_{}'.format(*vk_parts)
            assert vk in matrix.vm_df[vmc.vendorkey].values
            matrix.vm_change_on_key(vk, vmc.enddate, x[vmc.enddate])
        matrix.write()

    def test_run_processor(self):
        main('--api all --analyze')
