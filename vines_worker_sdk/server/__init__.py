import sentry_sdk
from flask import Flask, request, jsonify
import os

from sentry_sdk.integrations.flask import FlaskIntegration
from .exceptions import ClientException, ServiceException


def create_server(
        service_token: str,
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
        response = {'message': str(error)}

        if isinstance(error, ClientException):
            response['code'] = 400
        elif isinstance(error, ServiceException):
            response['code'] = 500
        else:
            response['code'] = 500

        return jsonify(response), response['code']

    @app.before_request
    def before_request():
        # Define the header you want to check for
        required_headers = [
            "x-vines-service-token",
        ]

        if request.method != 'OPTIONS':  # Exclude pre-flight requests
            for required_header in required_headers:
                if required_header not in request.headers:
                    # Return a 400 Bad Request response if the required header is missing
                    return jsonify({'error': f'Required header {required_header} missing', 'status_code': 403}), 403

        service_token_in_header = request.headers['x-vines-service-token']
        if service_token_in_header != service_token:
            return jsonify({'error': f'Invalid header service token provided', 'status_code': 403}), 403

    return app
