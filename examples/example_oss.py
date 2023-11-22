from vines_worker_sdk.oss import OSSClient
import json

aws_access_key_id = ""
aws_secret_access_key = ""
endpoint_url = ""
region_name = ""
bucket_name = ""
base_url = ""
oss_client = OSSClient(
    aws_access_key_id,
    aws_secret_access_key,
    endpoint_url,
    region_name,
    bucket_name,
    base_url,
)

if __name__ == '__main__':
    result = oss_client.upload_directory("")
    print(json.dumps(result, indent=2))
