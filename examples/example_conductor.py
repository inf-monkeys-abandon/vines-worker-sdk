import sys

from vines_worker_sdk.conductor import ConductorClient
import threading
import time
import signal

client = ConductorClient(
    service_registration_url="",
    service_registration_token="",
    conductor_base_url="https://conductor.infmonkeys.com/api",
    worker_id="some-infer-worker"
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
    start_mock_result_thread(task)


if __name__ == '__main__':
    client.register_block(
        {
            "name": "infer_sdk_test",
            "description": "test"
        }
    )
    client.register_handler("infer_sdk_test", test_handler)
    client.start_polling()
