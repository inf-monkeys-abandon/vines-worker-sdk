# Vines Python 训练项目 SDK （供内部使用）

这个项目希望解决的问题，将开发一个新的训练项目中的很多重复性工作进行统一封装：

1. 每次开一个新训练项目都需要起 HTTP Server
2. 里面有可能会用到很多通用能力，比如上传、下载文件、以及一些基础方法等，这些都应该封装好。
3. 错误日志推送逻辑
4. 运行时日志逻辑
5. api 入参、出参统一格式封装
6. 统一的日志格式、日志收集

## 使用示例

### 作为 conductor 客户端

详情见 `exampels/example_conductor.py` 文件中的内容：

```python
from vines_infer_sdk.conductor import ConductorClient
import threading
import time

client = ConductorClient(
    conductor_base_url="http://172.29.110.16:28080/api",
    worker_id="some-infer-worker"
)

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
    client.register_handler("infer_sdk_test", test_handler)
    client.start_polling()

```

### 使用 flask http server

从 `lib.server` 引入 `create_server` 方法，初始化 flask app，参数：

- sentry_dsn: sentry dsn, 如果配置，会自动收集异常推送到 sentry
- log_redis_queue_url: 如果配置，在调用 request.logger 方法的时候，会自动推送到消息队列，从而给前端展示。

打印日志的方法：直接使用 `request.logger` 实例的方法。

```python
from vines_infer_sdk.server import create_server
from flask import request

sentry_dsn = ""
redis_queue_url = ""
app = create_server(
    __name__,
    sentry_dsn=sentry_dsn,
    log_redis_queue_url=redis_queue_url
)


@app.get("/test")
def test():
    # 获取 request 下的 logger
    # 会自动打印到控制台和推送给 redis 消息队列，再给到客户端
    request.logger.info("hello")

    return "<p>Hello, World!</p>"


@app.get("/test-error")
def test():
    1 / 0
    return "<p>Hello, World!</p>"


if __name__ == '__main__':
    app.run(port=8899)
```