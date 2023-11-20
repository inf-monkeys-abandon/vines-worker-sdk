import requests
import time
import threading
import traceback


class ConductorClient:
    task_types = {}

    # 当前正在运行的 task 列表
    tasks = {}

    def __init__(self, conductor_base_url, worker_id, poll_interval_ms=500):
        self.conductor_base_url = conductor_base_url
        self.worker_id = worker_id
        self.poll_interval_ms = poll_interval_ms

    def register_handler(self, name, callback):
        self.task_types[name] = callback

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
        )
