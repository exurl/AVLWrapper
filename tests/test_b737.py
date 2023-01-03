import glob
import os.path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import pytest

import avlwrapper as avl

CDIR = os.path.dirname(os.path.realpath(__file__))
RES_DIR = os.path.join(CDIR, 'resources')
AVL_FILE = os.path.join(RES_DIR, 'b737.avl')
CASE_FILE = os.path.join(RES_DIR, 'b737.run')

OUT_FILES = ['st', 'sb', 'ft', 'fn', 'fs', 'fe', 'fb', 'hm', 'vm']

B737_SURFACES = ['Wing', 'Stab', 'Fin', 'Fuselage H', 'Fuselage V Bottom', 'Fuselage V Top', 'Nacelle']


@pytest.fixture(scope='session')
def manual_run():
    avl_bin = avl.default_config['avl_bin']
    run_file = 'runfile'
    with TemporaryDirectory(prefix='avltest_') as working_dir:
        run_file_path = os.path.join(working_dir, run_file)
        with open(run_file_path, 'w') as run_file:
            run_file.write('load b737.avl\n')
            run_file.write('case b737.run\n')
            run_file.write('oper\nx\n')
            for f in OUT_FILES:
                run_file.write(f'{f}\nb737.{f}\n')
            run_file.write('\n\nq\n')
        for b737_file in glob.glob(os.path.join(RES_DIR, 'b737*')):
            shutil.copy(b737_file, working_dir)
        shutil.copy(os.path.join(RES_DIR, 'a1.dat'), working_dir)
        with open(run_file_path) as ifile:
            proc = subprocess.Popen(avl_bin, cwd=working_dir, stdin=ifile, stdout=open(os.devnull, "w"))
            proc.wait()
        outputs = {}
        for f in OUT_FILES:
            f_path = os.path.join(working_dir, f'b737.{f}')
            outputs[f] = avl.OutputReader(f_path).get_content()
    return outputs


@pytest.fixture()
def model():
    return avl.Aircraft.from_file(AVL_FILE)


@pytest.fixture()
def run_case():
    return avl.Case.from_file(CASE_FILE)


def test_model(model):
    for surf in B737_SURFACES:
        assert surf in [s.name for s in model.surfaces]


def test_case(run_case):
    assert run_case


def test_b737_session(model, run_case, manual_run):
    session = avl.Session(geometry=model, cases=[run_case])
    results = session.run_all_cases()[run_case.name]

    def check_all_entries(result, reference):
        for key in result:
            if isinstance(result[key], dict):
                check_all_entries(result[key], reference[key])
            elif isinstance(result[key], list):
                for el, ref in zip(result[key], reference[key]):
                    assert el == pytest.approx(ref, 1e-6)
            else:
                assert result[key] == pytest.approx(reference[key], 1e-6)

    for res_key in results:
        man_key = session.OUTPUTS[res_key]
        check_all_entries(results[res_key], manual_run[man_key])