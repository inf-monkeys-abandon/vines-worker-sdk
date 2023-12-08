import os
import sentry_sdk
from flask import Flask, request, jsonify
from sentry_sdk.integrations.flask import FlaskIntegration
from .exceptions import ClientException, ServerException
import jwt


def verify_jwt(token: str, secret: str):
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload  # 如果成功，返回 payload 数据
    except jwt.InvalidTokenError:
        return None  # 如果失败，返回 None


def create_server(
        jwt_secret: str,
        import_name: str,
        service_token: str = None,
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
        elif isinstance(error, ServerException):
            response['code'] = 500
        else:
            response['code'] = 500

        return jsonify(response), response['code']

    @app.before_request
    def before_request():
        # 用户发起的，使用
        authorization_key = 'authorization'
        team_id_key = 'x-vines-team-id'
        token = request.headers[authorization_key]
        if not token:
            return jsonify({'error': f'Required header {authorization_key} missing', 'status_code': 403}), 403

        if token.startswith("System "):
            token = token.replace("System ", "")
            if not service_token:
                return jsonify({'error': f'Service authentication method not supported', 'status_code': 403}), 403
            if service_token != token:
                return jsonify({'error': f'Invalid {authorization_key} value provided', 'status_code': 403}), 403
            request.is_super_user = True
        elif token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
            verified_payload = verify_jwt(token, jwt_secret)
            if not verified_payload:
                return jsonify({'error': f'Invalid {authorization_key} value provided', 'status_code': 403}), 403
            team_id = request.headers.get(team_id_key)
            if not team_id:
                return jsonify(
                    {'error': f'{team_id_key} must be provided when use user authentication', 'status_code': 403}), 403
            request.user_id = verified_payload['id']
            request.team_id = team_id
        else:
            return jsonify({'error': f'Invalid {authorization_key} value provided', 'status_code': 403}), 403

    return app
