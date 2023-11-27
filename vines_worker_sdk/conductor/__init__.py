import logging

import requests
import time
import threading
import traceback
from requests.auth import HTTPBasicAuth
from vines_worker_sdk.exceptions import ServiceRegistrationException


class ConductorClient:
    task_types = {}

    # 当前正在运行的 task 列表
    tasks = {}

    def __init__(
            self,
            service_registration_url: str,
            service_registration_token: str,
            conductor_base_url: str,
            worker_id,
            poll_interval_ms=500,
            authentication_settings=None
    ):
        self.service_registration_url = service_registration_url
        self.service_registration_token = service_registration_token
        self.conductor_base_url = conductor_base_url
        self.worker_id = worker_id
        self.poll_interval_ms = poll_interval_ms
        self.authentication_settings = authentication_settings

    def __get_auth(self):
        auth = HTTPBasicAuth(
            username=self.authentication_settings.get('username'),
            password=self.authentication_settings.get('password')
        ) if self.authentication_settings else None
        return auth

    def __add_source_for_blocks(self, blocks):
        for block in blocks:
            if not block.get('extra'):
                block['extra'] = {}
            if not block.get('extra').get('meta'):
                block['extra']['meta'] = {}
            block['extra']['meta']['source'] = self.worker_id

    def register_blocks(self, blocks):
        self.__add_source_for_blocks(blocks)
        r = requests.post(
            url=f"{self.service_registration_url}/api/blocks/register",
            json={
                "blocks": blocks
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

    def start_polling(self):

        def callback_wrapper(callback, task):
            def wrapper():
                workflow_instance_id = task.get('workflowInstanceId')
                task_id = task.get('taskId')
                try:
                    result = callback(task)
                    # 如果有明确返回值，说明是同步执行逻辑，否则是一个异步函数，由开发者自己来修改 task 状态
                    if result:
                        del self.tasks[task_id]
                        self.update_task_result(
                            workflow_instance_id=workflow_instance_id,
                            task_id=task_id,
                            status="COMPLETED",
                            output_data=result
                        )
                except Exception as e:
                    del self.tasks[task_id]
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

            return wrapper

        while True:
            for task_type in self.task_types:
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
