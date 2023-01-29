import datetime
import glob
import logging
import os.path
import pathlib
from os.path import split, join, isfile
from typing import Dict, Tuple, List

from slugify import slugify


def _list_files_and_folders(path: str):
    files_and_folders = [p for p in pathlib.Path(path).iterdir()]
    files = [str(p.absolute()) for p in files_and_folders if p.is_file()]
    folders = [str(p.absolute()) for p in files_and_folders if p.is_dir()]
    return files, folders


def locate_project_base(folders_of_interest):
    """
    Find the source code base folder, given hints of where to start looking.
    """
    for folder in folders_of_interest:
        folder = str(pathlib.Path(folder).absolute())
        for _ in range(3):
            if isfile(join(folder, 'requirements.txt')):
                return folder
            folder = str(pathlib.Path(folder).absolute().parent)

    return None


def _get_project_m_timestamp() -> int:
    """
    Get the time the code base was last modified.
    """
    project_base = locate_project_base([os.getcwd(), split(__file__)[1]])
    if project_base is None:
        logging.error("Unable to locate project source files, using now as the expiration time for dynamic files.")
        return int(datetime.datetime.now().timestamp())

    # Find the most recently modified .py file.
    py_files = pathlib.Path(project_base).rglob("*.py")
    modification_time = int(max([p.stat().st_mtime for p in py_files]))

    msg = f"Expiring dynamic files using project modification time: {datetime.datetime.fromtimestamp(modification_time)}"
    logging.info(msg)
    print(msg)

    return modification_time


class DynamicFileManager:
    """
    Some files are procedurally generated, and need to be refreshed if the code base changes.

    This class manages a store of such files, in hierarchy on the filesystem.
    """
    def __init__(self, base_dir: str, expiration_time_stamp=None):
        self.base_dir = str(pathlib.Path(base_dir).absolute())
        # eg: path, m_time = file_map["ground_tiles"]["blured"]["foo.png"]
        self.file_map: Dict[Tuple, Tuple[str, int]] = {}

        if expiration_time_stamp is not None:
            self.expiration_time = expiration_time_stamp
        else:
            self.expiration_time = _get_project_m_timestamp()

        self.rescan()

    def rescan(self):
        # todo: prune old files to save disk space
        file_map = {}
        for filename in glob.iglob(join(self.base_dir, '**/**'), recursive=True):
            if os.path.isfile(filename):
                rel_path = os.path.relpath(filename, self.base_dir)
                # sub_path, file_name = split(rel_path)
                parts = pathlib.Path(rel_path).parts
                parts = tuple([p for p in parts if p not in "\\/"])
                m_time = int(os.stat(filename).st_mtime)
                file_map[parts] = (filename, m_time)

        self.file_map = file_map

    def query(self, categories: List[str], file_name: str):
        """
        Queries if a valid (non-expired) files exists.
        If it does not, the required folder structure is created.
        """
        parts = [slugify(c) for c in categories]
        parts.append(file_name)

        # do we have cached metadata
        if parts in self.file_map:
            # file exists, check modification time to see if it is expired
            path, m_time = self.file_map[parts]
            return path, m_time > self.expiration_time

        # file metadata does not exist in cache, was it newly created
        dest_dir = join(self.base_dir, *[slugify(c) for c in categories])
        dest_file = join(dest_dir, file_name)

        if os.path.isfile(dest_file):
            m_time = int(os.stat(dest_file).st_mtime)
            self.file_map[parts] = (dest_file, m_time)  # update cached metadata
            return dest_file, m_time > self.expiration_time

        # file does not exist, make sure it's folder does before exiting.
        os.makedirs(dest_dir, exist_ok=True)
        return dest_file, False


def main():
    dfm = DynamicFileManager("../game_files/dynamic_files")


if __name__ == '__main__':
    main()


