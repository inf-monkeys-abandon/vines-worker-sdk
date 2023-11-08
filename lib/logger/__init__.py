from bullmq import Queue
import asyncio
import time
import logging

QUEUE_NAME = "task-logs"
QUEUE_PROCESS_NAME = "event"


class Logger:
    def __init__(self,
                 project_name,
                 level=logging.DEBUG,
                 format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                 filename=None,  # 将日志记录到文件
                 redis_queue_url=None,
                 redis_queue_prefix="vines_",
                 workflow_id=None, workflow_instance_id=None, workflow_task_id=None
                 ):
        self.project_name = project_name
        self.redis_queue_url = redis_queue_url
        self.redis_queue_prefix = redis_queue_prefix
        self.workflow_id = workflow_id
        self.workflow_instance_id = workflow_instance_id
        self.workflow_task_id = workflow_task_id

        self.logger = logging.getLogger(project_name)
        self.logger.setLevel(level)  # Set the lowest logging level
        formatter = logging.Formatter(format)

        # Create a stream handler to write log messages to the terminal
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        # Add the handlers to the logger
        self.logger.addHandler(stream_handler)

        if filename:
            # Create a file handler to write log messages to a file
            file_handler = logging.FileHandler(filename)
            file_handler.setFormatter(formatter)
            # Add the handlers to the logger
            self.logger.addHandler(file_handler)

    def debug(self, message, workflow_id=None, workflow_instance_id=None, workflow_task_id=None):
        self.__log(message, "debug", workflow_id, workflow_instance_id, workflow_task_id)

    def info(self, message, workflow_id=None, workflow_instance_id=None, workflow_task_id=None):
        self.__log(message, "info", workflow_id, workflow_instance_id, workflow_task_id)

    def warn(self, message, workflow_id=None, workflow_instance_id=None, workflow_task_id=None):
        self.__log(message, "warn", workflow_id, workflow_instance_id, workflow_task_id)

    def error(self, message, workflow_id=None, workflow_instance_id=None, workflow_task_id=None):
        self.__log(message, "error", workflow_id, workflow_instance_id, workflow_task_id)

    def __log(self, message, level, workflow_id=None, workflow_instance_id=None, workflow_task_id=None):
        # 打印日志到控制台
        getattr(self.logger, level)(message)

        # 发送到消息队列
        workflow_id = workflow_id or self.workflow_id
        workflow_instance_id = workflow_instance_id or self.workflow_instance_id
        workflow_task_id = workflow_task_id or self.workflow_task_id
        if self.redis_queue_url and workflow_id and workflow_instance_id and workflow_task_id:
            payload = {
                "version": "1",
                "dataContentType": "text/json",
                "data": {
                    "workflowId": workflow_id,
                    "workflowInstanceId": workflow_instance_id,
                    "taskId": workflow_task_id
                },
                "timestamp": int(round(time.time() * 1000)),
                "origin": self.project_name,
            }
            self.__send_event_to_queue(payload)

    def __send_event_to_queue(self, payload):
        queue = Queue(QUEUE_NAME, self.redis_queue_url, {"prefix": self.redis_queue_prefix})
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(queue.add(QUEUE_PROCESS_NAME, payload))
        loop.run_until_complete(task)
