from vines_worker_sdk.server import create_server
from flask import request

sentry_dsn = "https://45426676ad0c4ea9628deef009d11620@o4506154455531520.ingest.sentry.io/4506188249694208"
redis_queue_url = "redis://localhost:6379/0"

app = create_server(
    service_token="",
    import_name=__name__,
)


@app.get("/test")
def test():
    # 获取 request 下的 logger
    # 会自动打印到控制台和推送给 redis 消息队列，再给到客户端
    request.logger.info("hello")

    return "<p>Hello, World!</p>"


if __name__ == '__main__':
    app.run(debug=True, port=8899)
