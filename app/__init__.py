from datetime import date, datetime
from urllib.parse import urlencode

from flask import Flask, render_template

from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app import db as db_module

    db_module.init_app(app)

    with app.app_context():
        from app.services.cuisines import seed_default_cuisines

        seed_default_cuisines(app.config["DEFAULT_CUISINES"])

    register_blueprints(app)
    register_template_helpers(app)
    register_error_handlers(app)

    return app


def register_blueprints(app):
    from app.routes.main import bp as main_bp
    from app.routes.orders import bp as orders_bp
    from app.routes.analytics import bp as analytics_bp
    from app.routes.restaurants import bp as restaurants_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.import_routes import bp as import_bp
    from app.routes.api import bp as api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(restaurants_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(api_bp)


def register_template_helpers(app):
    from app.services.settings import get_setting

    @app.context_processor
    def inject_globals():
        return {
            "currency_symbol": get_setting("currency_symbol", app.config["DEFAULT_CURRENCY_SYMBOL"]),
            "theme_setting": get_setting("theme", "system"),
            "current_year": date.today().year,
        }

    @app.template_filter("money")
    def money_filter(value):
        if value is None:
            return "0"
        value = float(value)
        formatted = f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
        return formatted

    @app.template_filter("friendly_date")
    def friendly_date_filter(value):
        if not value:
            return ""
        try:
            d = datetime.fromisoformat(str(value)).date() if "T" in str(value) else date.fromisoformat(str(value))
        except ValueError:
            return value
        return d.strftime("%b %-d, %Y") if hasattr(d, "strftime") else value

    @app.template_filter("friendly_time")
    def friendly_time_filter(value):
        if not value:
            return ""
        try:
            hh, mm = value.split(":")
            hh = int(hh)
        except (ValueError, AttributeError):
            return value
        period = "AM" if hh < 12 else "PM"
        hour12 = hh % 12
        hour12 = 12 if hour12 == 0 else hour12
        return f"{hour12}:{mm} {period}"

    @app.template_filter("urlencode")
    def urlencode_filter(d):
        return urlencode({k: v for k, v in d.items() if v not in (None, "")})


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/error.html", message="That file is too large to upload (max 10 MB)."), 413

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/error.html", message="Something went wrong on our end. Please try again."), 500
