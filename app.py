# IMPORTS
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_qrcode import QRcode
from flask_login import LoginManager, current_user
from flask_talisman import Talisman
from functools import wraps
import os
import logging
from dotenv import load_dotenv

# CONFIG
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['RECAPTCHA_PUBLIC_KEY'] = os.getenv('RECAPTCHA_PUBLIC_KEY')
app.config['RECAPTCHA_PRIVATE_KEY'] = os.getenv('RECAPTCHA_PRIVATE_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_ECHO'] = os.getenv('SQLALCHEMY_ECHO') == 'True'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS') == 'True'

# initialise database
db = SQLAlchemy(app)

# defining custom content security policy
csp = {
    'default-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.2/css/bulma.min.css'
    ],
    'frame-src': [
        '\'self\'',
        'https://www.google.com/recaptcha/',
        'https://recaptcha.google.com/recaptcha/'
    ],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://www.google.com/recaptcha/',
        'https://www.gstatic.com/recaptcha/'
    ],
    'img-src': [
        '\'self\'',
        'data:'
    ]
}

# register app with the http security header class
talisman = Talisman(app, content_security_policy=csp)


# LOGGER
# Define logger filter class
class SecurityFilter(logging.Filter):
    def filter(self, record):
        return 'SECURITY' in record.getMessage()


# creating logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# file to append records to
file_handler = logging.FileHandler('lottery.log', 'a')
file_handler.setLevel(logging.WARNING)

# Only writes to the log file message containing security string
file_handler.addFilter(SecurityFilter())

# Defining how log records are presented
formatter = logging.Formatter('%(asctime)s : %(message)s', '%m/%d/%Y %I:%M:%S %p')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


# custom wrapper function for role access
def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                logging.warning('SECURITY - Forbidden Access [%s, %s, %s, %s]',
                                current_user.id,
                                current_user.email,
                                current_user.role,
                                request.remote_addr)
                return render_template('403.html')
            return f(*args, **kwargs)

        return wrapped

    return wrapper


# initialise QRcode
qrcode = QRcode(app)
# initialise login manager
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.init_app(app)


# HOME PAGE VIEW
@app.route('/')
def index():
    return render_template('main/index.html')


# BLUEPRINTS
# import blueprints
from models import User
from users.views import users_blueprint
from admin.views import admin_blueprint
from lottery.views import lottery_blueprint

# register blueprints with app
app.register_blueprint(users_blueprint)
app.register_blueprint(admin_blueprint)
app.register_blueprint(lottery_blueprint)


@login_manager.user_loader
def load_user(session_id):
    return User.query.get(int(session_id))


# ERROR HANDLERS
@app.errorhandler(400)
def bad_request(error):
    return render_template('400.html'), 400


@app.errorhandler(403)
def forbidden_access(error):
    return render_template('403.html'), 403


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


@app.errorhandler(503)
def service_unavailable(error):
    return render_template('503.html'), 503


if __name__ == "__main__":
    app.run(ssl_context=('cert.pem', 'key.pem'))
