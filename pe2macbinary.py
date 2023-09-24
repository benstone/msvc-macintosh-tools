import os
import pathlib
import argparse
import shutil
import logging
import subprocess
import tempfile
import time
import winreg
from datetime import datetime

from macbinary import MacBinaryIIFile

logger = logging.getLogger("pe2macbinary")


def get_msvc_cde_path() -> str:
    """ Get path used for Visual C++ Cross Development Edition build tools. """
    build_tools_key = "SOFTWARE\\Microsoft\\Developer\\Build System\\Components\\Platforms\\Macintosh\\Directories"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, build_tools_key) as key:
        value_data, value_type = winreg.QueryValueEx(key, "Path Dirs")
        assert value_type == winreg.REG_SZ
        return value_data


def find_mrc():
    """ Locate mrc.exe, the Macintosh resource compiler from Visual C++ Cross Development Edition """

    # Set search path
    try:
        path = get_msvc_cde_path()
    except FileNotFoundError:
        path = None

    # Search for mrc.exe
    mrc_path = shutil.which("mrc.exe", path=path)
    if mrc_path is not None:
        logger.debug(f"Found MRC on path: {mrc_path}")
        return mrc_path

    # Not found
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Convert a Portable Executable compiled by Visual C++ Cross Development Edition to a MacBinary file")
    parser.add_argument("pe_file", help="Portable Executable file compiled by Visual C++ Cross Development Edition")
    parser.add_argument("macbinary_file", help="MacBinary file to write")
    parser.add_argument("--name", help="File name on Macintosh file system")
    parser.add_argument("--data", help="Path to data fork", required=False)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    pe_file_path = pathlib.Path(args.pe_file).absolute()
    macbinary_path = pathlib.Path(args.macbinary_file).absolute()

    if args.name is not None:
        program_name = args.name
    else:
        program_name = pe_file_path.name
        # Strip file extension
        if program_name.lower().endswith(".exe"):
            program_name = program_name[:-4]

    logger.info(f"Program name: {program_name}")
    data_fork = None
    if args.data:
        with open(args.data, "rb") as data_file:
            data_fork = data_file.read()
    pe_to_macbinary(pe_file_path, macbinary_path, program_name, data_fork=data_fork)


def pe_to_macbinary(pe_file_path: str, macbinary_path: str, program_name: str, data_fork=None):
    """
    Convert a PE file from Visual C++ Cross Development Edition to a MacBinary file
    :param pe_file_path: Path to PE file produced by link.exe
    :param macbinary_path: Path to MacBinary file to create
    :param program_name: File name displayed in Finder
    :param data_fork: Optional data fork to add to file
    """
    mrc_path = find_mrc()
    if mrc_path is None:
        raise Exception("Cannot find mrc.exe on path / from registry")

    # Create temp files for the resource fork, data fork, and file info
    rsrc_temp_path = tempfile.NamedTemporaryFile(delete=False)
    rsrc_temp_path.close()

    data_temp_path = tempfile.NamedTemporaryFile(delete=False)
    data_temp_path.close()

    afp_fileinfo_path = tempfile.NamedTemporaryFile(delete=False)
    afp_fileinfo_path.close()

    # Generate resource fork from PE using mrc.exe
    args = [
        mrc_path,
        "-e", pe_file_path,
        "-o", rsrc_temp_path.name,
        "-w", data_temp_path.name,
        "-x", afp_fileinfo_path.name,
    ]
    subprocess.check_call(args)

    # Load resource fork
    with open(rsrc_temp_path.name, "rb") as rsrc_temp_file:
        resource_fork = rsrc_temp_file.read()
    logger.info(f"Resource fork: {len(resource_fork)} bytes")

    if data_fork is None:
        data_fork = b''

    logger.info(f"Data fork: {len(data_fork)} bytes")

    # Get creator and type from AFP file info
    with open(afp_fileinfo_path.name, "rb") as afp_fileinfo_file:
        afp_fileinfo = afp_fileinfo_file.read()
    file_creator, file_type = parse_afp_file_info(afp_fileinfo)

    logger.info(f"File type: {file_type}")
    logger.info(f"File creator: {file_creator}")

    # Clean up temporary files
    for temp_path in (rsrc_temp_path.name, data_temp_path.name, afp_fileinfo_path.name):
        pathlib.Path(temp_path).unlink(missing_ok=True)

    # Get file dates from environment for reproducible builds
    file_date = datetime.utcfromtimestamp(int(os.environ.get("SOURCE_DATE_EPOCH", time.time())))
    logger.info(f"File creation date: {file_date}")

    macbinary_file = MacBinaryIIFile(file_name=program_name,
                                     file_type=file_type,
                                     file_creator=file_creator,
                                     resource_fork=resource_fork,
                                     data_fork=data_fork,
                                     creation_date=file_date,
                                     modification_date=file_date)

    logger.info(f"Writing {macbinary_path}")
    with open(macbinary_path, "wb") as output_file:
        macbinary_file.write(output_file)


def parse_afp_file_info(afp_fileinfo):
    """ Get file type and creator from an AFP_FileInfo stream """

    if len(afp_fileinfo) != 60 or afp_fileinfo[0:3] != b'AFP':
        raise ValueError("invalid AFP file info stream")

    finder_info = afp_fileinfo[16:48]
    file_type = finder_info[0:4].decode("macroman")
    file_creator = finder_info[4:8].decode("macroman")
    return file_creator, file_type


if __name__ == "__main__":
    main()
