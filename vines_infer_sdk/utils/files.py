import os


def ensure_directory_exists(dir_path):
    """
        如果目录不存在则创建目录
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path
