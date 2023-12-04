import logging
import requests
import boto3
from botocore.client import Config
import os

from vines_worker_sdk.utils.files import ensure_directory_exists


class OSSClient():
    def __init__(self,
                 aws_access_key_id,
                 aws_secret_access_key,
                 endpoint_url,
                 region_name,
                 bucket_name,
                 base_url,
                 max_content_length=100 * 1024 * 1024  # 10MB
                 ):
        self.base_url = base_url
        self.bucket_name = bucket_name
        self.max_content_length = max_content_length
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            config=Config(s3={'addressing_style': 'virtual'})
        )

    # 检查 url 里 content length 是否过大
    def get_content_length(self, url):
        r = requests.head(url)
        content_length = r.headers['content-length']
        return int(content_length)

    # 检查文件大小是否超过限制
    def check_file_size(self, file_url):
        if self.get_content_length(file_url) > self.max_content_length:
            return False
        return True

    def get_file_name(self, file_url):
        return file_url.split('/')[-1].split('.')[0]

    def get_file_type(self, file_url):
        return file_url.split('.')[-1]

    def download_file(self, file_url, target_path):
        """
            下载文件进指定目录
            下载成功返回 文件地址
            下载失败返回 False
        """
        try:
            response = requests.get(file_url, stream=True)
            response.raise_for_status()

            filename = self.get_file_name(file_url)
            # 检查filename中的中文是否被编码，如果被编码则解码，以解码后的文件名保存
            filetype = self.get_file_type(file_url)
            ensure_directory_exists(target_path)
            final_path = f"{target_path}/{filename}.{filetype}"
            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return final_path
        except requests.RequestException as e:
            logging.error(f"下载文件失败，错误信息为 {e}")
            return False

    def upload_file_tos(self, file_path, key):
        """ 上传到 TOS

            返回最终的文件地址
        """
        try:
            self.client.upload_file(file_path, self.bucket_name, key)
            return self.base_url + "/" + key
        except Exception as e:
            print('fail with unknown error: {}'.format(e))

    def download_file_tos(self, target_filename, key):
        """ 下载文件到本地 """
        try:
            self.client.download_file(self.bucket_name, key, target_filename)
        except Exception as e:
            print('fail with unknown error: {}'.format(e))

    def upload_bytes(self, key, bytes):
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=bytes
        )

    def __get_file_extension(self, file_path):
        _, file_extension = os.path.splitext(file_path)
        return file_extension

    def upload_directory(self, directory_path, file_extensions=None, url_prefix=None):
        return self.__upload_directory_recursive(
            os.path.dirname(directory_path),
            directory_path,
            file_extensions,
            url_prefix
        )

    def __upload_directory_recursive(self, root_folder, directory_path, file_extensions=None, url_prefix=None):
        result_map = {}
        # 遍历目录
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)

            # 判断是文件还是目录
            if os.path.isfile(item_path):
                # 如果是文件，进行上传
                if file_extensions:
                    file_extension = self.__get_file_extension(item_path)
                    if file_extension not in file_extensions:
                        continue
                file_key = item_path.replace(root_folder, '')
                if file_key[0] == '/':
                    file_key = file_key[1:]
                if url_prefix:
                    file_key = f"{url_prefix}{file_key}"
                file_url = self.upload_file_tos(item_path, file_key)
                print(f"成功将文件 {item_path} 上传到 {file_url}")
                result_map[item] = file_url
            elif os.path.isdir(item_path):
                # 如果是目录，递归调用函数
                result_map[item] = self.__upload_directory_recursive(root_folder, item_path, file_extensions,
                                                                     url_prefix)

        return result_map
