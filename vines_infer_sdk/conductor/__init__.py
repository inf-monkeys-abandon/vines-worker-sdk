import requests
import time
import threading
import traceback


class ConductorClient:
    tasks = {}

    def __init__(self, conductor_base_url, worker_id, poll_interval_ms=500):
        self.conductor_base_url = conductor_base_url
        self.worker_id = worker_id
        self.poll_interval_ms = poll_interval_ms

    def register_handler(self, name, callback):
        self.tasks[name] = callback

    def __poll_by_task_type(self, task_type, worker_id, count=1, domain=None):
        params = {
            "workerid": worker_id,
            "count": count
        }
        if domain:
            params['domain'] = domain
        r = requests.get(f"{self.conductor_base_url}/tasks/poll/batch/{task_type}", params=params)
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
                        self.update_task_result(
                            workflow_instance_id=workflow_instance_id,
                            task_id=task_id,
                            status="COMPLETED",
                            output_data=result
                        )
                except Exception as e:
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
            for task_type in self.tasks:
                tasks = self.__poll_by_task_type(task_type, self.worker_id, 1)
                for task in tasks:
                    callback = self.tasks[task_type]
                    t = threading.Thread(
                        target=callback_wrapper(callback, task)
                    )
                    t.start()
                time.sleep(self.poll_interval_ms / 1000)

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
        )
