import logging

import requests
import time
import threading
import traceback
from requests.auth import HTTPBasicAuth
from vines_worker_sdk.exceptions import ServiceRegistrationException
import json
import redis
import os

from vines_worker_sdk.oss import OSSClient


class ConductorClient:
    task_types = {}

    # 当前正在运行的 task 列表
    tasks = {}

    def __init__(
            self,
            service_registration_url: str,
            service_registration_token: str,
            worker_id,
            redis_url: str,
            conductor_base_url: str,
            poll_interval_ms=500,
            authentication_settings=None,
            task_output_payload_size_threshold_kb=1024,
            external_storage: OSSClient = None,
            external_storage_tmp_folder: str = "/tmp",
            worker_name_prefix=None
    ):
        self.service_registration_url = service_registration_url
        self.service_registration_token = service_registration_token
        self.conductor_base_url = conductor_base_url
        self.worker_id = worker_id
        self.poll_interval_ms = poll_interval_ms
        self.authentication_settings = authentication_settings
        self.task_output_payload_size_threshold_kb = task_output_payload_size_threshold_kb
        self.external_storage = external_storage
        self.external_storage_tmp_folder = external_storage_tmp_folder
        self.worker_name_prefix = worker_name_prefix
        self.redis_client = redis.from_url(redis_url)

    def __get_auth(self):
        if not self.authentication_settings:
            return None
        username = self.authentication_settings.get('username')
        password = self.authentication_settings.get('password')
        if username and password:
            auth = HTTPBasicAuth(
                username=username,
                password=password
            ) if self.authentication_settings else None
            return auth
        return None

    def __add_source_for_block(self, block):
        if not block.get('extra'):
            block['extra'] = {}
        if not block.get('extra').get('meta'):
            block['extra']['meta'] = {}
        block['extra']['meta']['source'] = self.worker_id

    def __register_task_def(self, task_def):
        """
        向 conductor 注册 task
        """
        requests.post(
            url=f"{self.conductor_base_url}/metadata/taskdefs",
            json=[task_def]
        )

    def register_block(self, block, retry_count=3, timeout_seconds=86400, owner_email='dev@infmonkeys.com'):
        task_def = {
            "name": block.get('name'),
            "inputKeys": [input.get('name') for input in block.get('input')],
            "outputKeys": [output.get('name') for output in block.get('output')],
            "retryCount": retry_count,
            "timeoutSeconds": timeout_seconds,
            "ownerEmail": owner_email
        }
        self.__register_task_def(task_def)
        self.__add_source_for_block(block)
        r = requests.post(
            url=f"{self.service_registration_url}/api/blocks/register",
            json={
                "blocks": [block]
            },
            headers={
                "x-vines-service-registration-key": self.service_registration_token
            }
        )
        json = r.json()
        code, message = json.get('code'), json.get('message')
        if code != 200:
            raise ServiceRegistrationException(message)
        data = json.get('data', {})
        success = data.get('success')
        if not success:
            raise ServiceRegistrationException("Register blocks failed")

    def register_handler(self, name, callback):
        if self.worker_name_prefix:
            name = self.worker_name_prefix + name
        self.task_types[name] = callback

    def __poll_by_task_type(self, task_type, worker_id, count=1, domain=None):
        params = {
            "workerid": worker_id,
            "count": count
        }
        if domain:
            params['domain'] = domain

        r = requests.get(
            url=f"{self.conductor_base_url}/tasks/poll/batch/{task_type}",
            params=params,
            auth=self.__get_auth()
        )
        tasks = r.json()
        return tasks

    def __get_workflow_context_cache_key(self, workflow_instance_id: str):
        return f"workflow:context:{workflow_instance_id}"

    def __get_real_workflow_instance_id_start_by_server(self, workflow_instance_id):
        has_parent_workflow = True
        while has_parent_workflow:
            r = requests.get(
                url=f"{self.conductor_base_url}/workflow/{workflow_instance_id}",
                auth=self.__get_auth()
            )
            data = r.json()
            if data.get('parentWorkflowId'):
                workflow_instance_id = data.get('parentWorkflowId')
            else:
                has_parent_workflow = False
        return workflow_instance_id

    def get_workflow_context(self, workflow_instance_id):
        workflow_instance_id = self.__get_real_workflow_instance_id_start_by_server(workflow_instance_id)
        key = self.__get_workflow_context_cache_key(workflow_instance_id)
        str_result = self.redis_client.get(key)
        if str_result is None:
            raise Exception(f"无法获取 workflow context for workflowInstanceId={workflow_instance_id}")
        return json.loads(str_result)

    def start_polling(self):

        def callback_wrapper(callback, task):
            def wrapper():
                workflow_instance_id = task.get('workflowInstanceId')
                task_id = task.get('taskId')
                externalInputPayloadStoragePath = task.get('externalInputPayloadStoragePath')
                try:
                    if externalInputPayloadStoragePath:
                        tmp_file_name = os.path.join(self.external_storage_tmp_folder, f"{task_id}.json")
                        self.external_storage.download_file_tos(tmp_file_name, externalInputPayloadStoragePath)
                        input_data = {}
                        with open(tmp_file_name, 'r', encoding='utf-8') as f:
                            input_data = json.load(f)
                        task['inputData'] = input_data
                        os.remove(tmp_file_name)
                    workflow_context = self.get_workflow_context(workflow_instance_id)
                    result = callback(task, workflow_context)
                    # 如果有明确返回值，说明是同步执行逻辑，否则是一个异步函数，由开发者自己来修改 task 状态
                    if result:
                        self.update_task_result(
                            workflow_instance_id=workflow_instance_id,
                            task_id=task_id,
                            status="COMPLETED",
                            output_data=result
                        )
                        del self.tasks[task_id]
                except Exception as e:
                    print(str(e))
                    traceback.print_stack()
                    self.update_task_result(
                        workflow_instance_id=workflow_instance_id,
                        task_id=task_id,
                        status="FAILED",
                        output_data={
                            "success": False,
                            "errMsg": str(e)
                        }
                    )
                    del self.tasks[task_id]

            return wrapper

        logging.info(f"开始从 conductor 轮询拉取任务：{self.task_types.keys()}")
        while True:
            for task_type in self.task_types:
                try:
                    tasks = self.__poll_by_task_type(task_type, self.worker_id, 1)
                    if len(tasks) > 0:
                        logging.info(f"拉取到 {len(tasks)} 条 {task_type} 任务")
                    for task in tasks:
                        callback = self.task_types[task_type]
                        task_id = task.get('taskId')
                        self.tasks[task_id] = task
                        t = threading.Thread(
                            target=callback_wrapper(callback, task)
                        )
                        t.start()
                except Exception:
                    traceback.print_exc()
                time.sleep(self.poll_interval_ms / 1000)

    def set_all_tasks_to_failed_state(self):
        running_task_ids = self.tasks.keys()
        for task_id in running_task_ids:
            task = self.tasks[task_id]
            workflow_instance_id = task.get('workflowInstanceId')
            self.update_task_result(
                workflow_instance_id=workflow_instance_id,
                task_id=task_id,
                status="FAILED",
                output_data={
                    "success": False,
                    "errMsg": "worker 已重启，请重新运行"
                }
            )

    def update_task_result(self, workflow_instance_id, task_id, status,
                           output_data=None,
                           reason_for_incompletion=None,
                           callback_after_seconds=None,
                           worker_id=None
                           ):

        if status not in ['COMPLETED', 'FAILED']:
            raise Exception("status must be COMPLETED or FAILED")
        body = {
            "workflowInstanceId": workflow_instance_id,
            "taskId": task_id,
            "status": status,
            "workerId": self.worker_id
        }
        if output_data:
            obj_bytes = json.dumps(output_data).encode('utf-8')
            size = len(obj_bytes)
            size_in_kb = size / 1024
            # 大于临界值，需要上传
            if size_in_kb > self.task_output_payload_size_threshold_kb:
                key = f"task/output/{task_id}.json"
                start = time.time()
                print(
                    f"检测到 {task_id} 的 output ({size_in_kb} kb) 大于临界值 {self.task_output_payload_size_threshold_kb} kb，开始上传到 oss 外部存储")
                self.external_storage.upload_bytes(
                    key,
                    obj_bytes
                )
                end = time.time()
                spend = end - start
                print(f"上传到 oss 外部存储成功：path={key}, 耗时={spend} s")
                body['outputData'] = {}
                body['externalOutputPayloadStoragePath'] = key
            else:
                body['outputData'] = output_data
        if reason_for_incompletion:
            body['reasonForIncompletion'] = reason_for_incompletion
        if callback_after_seconds:
            body['callbackAfterSeconds'] = callback_after_seconds
        if worker_id:
            body['workerId'] = worker_id
        requests.post(
            f"{self.conductor_base_url}/tasks",
            json=body,
            auth=self.__get_auth()
        )
