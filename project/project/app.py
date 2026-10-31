from flask import Flask, abort, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from api import api_bp
from config import Config
from helpers import csrf_is_valid
from models import db
from routes import main_bp
from seed import seed_demo_data


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def protect_forms_from_csrf():
        if request.method == "POST" and not csrf_is_valid():
            abort(400, description="Your session has expired. Please refresh the page and try again.")

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": error.description}), error.code
        return render_template("error.html", error=error), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled error: %s", error)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Something went wrong on our side."}), 500
        return render_template("error.html", error=None), 500

    with app.app_context():
        db.create_all()
        seed_demo_data()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
