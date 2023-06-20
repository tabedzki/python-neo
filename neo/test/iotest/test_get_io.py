from pathlib import Path
from tempfile import TemporaryDirectory
from neo.io import get_io, list_candidate_ios, NixIO


def test_list_candidate_ios_non_existant_file():
    # use plexon io suffix for testing here
    non_existant_file = 'non_existant_folder/non_existant_file.plx'
    ios = list_candidate_ios(non_existant_file)

    assert ios


def test_list_candidate_ios_filename_stub():
    # create dummy folder with dummy files
    with TemporaryDirectory(prefix='filename_stub_test_') as test_folder:
        test_folder = Path(test_folder)
        test_filename = (test_folder / 'dummy_file.nix')
        test_filename.touch()
        filename_stub = test_filename.with_suffix('')

        # check that io is found even though file suffix was not provided
        ios = list_candidate_ios(filename_stub)

        assert NixIO in ios


def test_get_io_non_existant_file_writable_io():
    # use nixio for testing with writable io
    non_existant_file = 'non_existant_file.nix'
    io = get_io(non_existant_file)

    assert isinstance(io, NixIO)
