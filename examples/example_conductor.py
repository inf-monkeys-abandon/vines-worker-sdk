import sys

from vines_worker_sdk.conductor import ConductorClient
from vines_worker_sdk.oss import OSSClient
import threading
import time
import signal
from dotenv import load_dotenv
import os

load_dotenv()

S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY")
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")
S3_REGION_NAME = os.environ.get("S3_REGION_NAME")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = os.environ.get("S3_BASE_URL")
oss_client = OSSClient(
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    endpoint_url=S3_ENDPOINT_URL,
    region_name=S3_REGION_NAME,
    bucket_name=S3_BUCKET_NAME,
    base_url=S3_BASE_URL,
)

client = ConductorClient(
    service_registration_url="http://localhost:3000",
    service_registration_token="T19lwWwQP4721HUUgssSq7L2Wgw5JO25oFTLD2toGFUWd7JEejfg7G7ZtO88uSlfzGp",
    conductor_base_url="http://localhost:8080/api",
    worker_id="some-infer-worker",
    external_storage=oss_client
)


def signal_handler(signum, frame):
    print('SIGTERM or SIGINT signal received.')
    print('开始标记所有 task 为失败状态 ...')

    client.set_all_tasks_to_failed_state()
    sys.exit()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def start_mock_result_thread(task):
    def handler():
        time.sleep(5)
        client.update_task_result(
            workflow_instance_id=task.get('workflowInstanceId'),
            task_id=task.get('taskId'),
            status='COMPLETED',
            output_data={
                "success": True
            }
        )

    t = threading.Thread(target=handler)
    t.start()


def test_handler(task):
    workflow_instance_id = task.get('workflowInstanceId')
    task_id = task.get('taskId')
    print(f"开始执行任务：workflow_instance_id={workflow_instance_id}, task_id={task_id}")

    # 这个 mock 一个异步线程，模拟一段时间之后手动更新 task 状态的场景
    with open('./test.txt', 'r') as f:
        data = f.read()
        return {
            "data": data
        }


if __name__ == '__main__':
    client.register_block(
        {
            "name": "infer_sdk_test",
            "description": "test",
            "displayName": "测试",
            "icon": "emoji:🖥️:#434343",
            "input": [
                {
                    "name": "text",
                    "type": "string",
                    "displayName": "测试"
                }
            ],
            "output": [
                {
                    "name": "data",
                    "type": "string",
                    "displayName": "data"
                }
            ]
        }
    )
    client.register_handler("cj_infer_sdk_test", test_handler)
    client.start_polling()
