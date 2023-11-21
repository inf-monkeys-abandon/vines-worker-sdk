import sentry_sdk
from flask import Flask, request, jsonify
import json
import os

from sentry_sdk.integrations.flask import FlaskIntegration
from vines_worker_sdk.logger import Logger


def create_server(
        import_name: str,
        static_url_path: str | None = None,
        static_folder: str | os.PathLike | None = "static",
        static_host: str | None = None,
        host_matching: bool = False,
        subdomain_matching: bool = False,
        template_folder: str | os.PathLike | None = "templates",
        instance_path: str | None = None,
        instance_relative_config: bool = False,
        root_path: str | None = None,
        sentry_dsn: str | None = None,
        log_redis_queue_url: str | None = None,
        log_redis_queue_prefix: str | None = "vines_"
):
    app = Flask(
        import_name,
        static_url_path,
        static_folder,
        static_host,
        host_matching,
        subdomain_matching,
        template_folder,
        instance_path,
        instance_relative_config,
        root_path
    )

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            # Enable performance monitoring
            enable_tracing=True,
            integrations=[
                FlaskIntegration(
                    transaction_style="url",
                ),
            ],
        )

    @app.errorhandler(Exception)
    def handle_exception(error):
        if sentry_dsn:
            sentry_sdk.capture_exception(error=error)
        response = {'error': str(error)}

        if hasattr(error, 'code'):
            response['status_code'] = error.code
        else:
            response['status_code'] = 500

        return jsonify(response), response['status_code']

    @app.before_request
    def before_request():
        # Define the header you want to check for
        required_headers = [
            "x-vines-workflow-instance-id",
            "x-vines-workflow-task-id",
            "x-vines-workflow-id"
        ]

        if request.method != 'OPTIONS':  # Exclude pre-flight requests
            for required_header in required_headers:
                if required_header not in request.headers:
                    # Return a 400 Bad Request response if the required header is missing
                    return jsonify({'error': f'Required header {required_header} missing', 'status_code': 400}), 400

        request.workflow_instance_id = request.headers['x-vines-workflow-instance-id']
        request.workflow_id = request.headers['x-vines-workflow-id']
        request.workflow_task_id = request.headers['x-vines-workflow-task-id']

        request.logger = Logger(
            project_name=import_name,
            workflow_id=request.workflow_id,
            workflow_task_id=request.workflow_task_id,
            workflow_instance_id=request.workflow_instance_id,
            redis_queue_url=log_redis_queue_url,
            redis_queue_prefix=log_redis_queue_prefix
        )

    @app.after_request
    def after_request(response):
        # You can add your custom response manipulation logic here
        if response.status_code == 200 and response.content_type == 'application/json':
            data = json.loads(response.get_data(as_text=True))
            response.set_data(json.dumps(data))
        return response

    return app
