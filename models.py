import rsa

from app import db, app
from flask_login import UserMixin
from datetime import datetime
import pyotp
from cryptography.fernet import Fernet
import bcrypt
import pickle


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # User authentication information.
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

    # User information
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    birthdate = db.Column(db.String(10), nullable=False)
    postcode = db.Column(db.String(7), nullable=False)
    phone = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False, default='user')
    pin_key = db.Column(db.String(32), nullable=False, default=pyotp.random_base32())

    # Event Logging information
    registered_on = db.Column(db.DateTime(), nullable=False)
    current_login = db.Column(db.DateTime(), nullable=True)
    current_login_ip = db.Column(db.String(), nullable=True)
    last_login = db.Column(db.DateTime(), nullable=True)
    last_login_ip = db.Column(db.String(), nullable=True)
    total_logins = db.Column(db.Integer, nullable=True)

    # Symmetric encryption
    # draw_pin = db.Column(db.BLOB, nullable=False, default=Fernet.generate_key())

    # Asymmetric encryption
    public_key = db.Column(db.BLOB, nullable=True)
    private_key = db.Column(db.BLOB, nullable=True)

    # Define the relationship to Draw
    draws = db.relationship('Draw')

    def __init__(self, email, firstname, lastname, birthdate, postcode, phone, password, role, public_key, private_key):
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.birthdate = birthdate
        self.postcode = postcode
        self.phone = phone
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.role = role
        self.registered_on = datetime.now()
        self.current_login = None
        self.current_login_ip = None
        self.last_login = None
        self.last_login_ip = None
        self.total_logins = 0
        self.public_key = pickle.dumps(public_key)
        self.private_key = pickle.dumps(private_key)

    # Method to verify password at login
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password)

    # Method to verify postcode at login
    def verify_postcode(self, postcode):
        return self.postcode.replace(" ", "") == postcode.replace(" ", "").upper()

    # Method to return URI string
    def get_2fa_uri(self):
        return str(pyotp.totp.TOTP(self.pin_key).provisioning_uri(
            name=self.email,
            issuer_name='LotteryWebApp')
        )

    # Method to verify pin on login
    def verify_pin(self, pin):
        return pyotp.TOTP(self.pin_key).verify(pin)


# Encryption and Decryption procedures
def encrypt(data, draw_key):
    return Fernet(draw_key).encrypt(bytes(data, 'utf-8'))


def decrypt(data, draw_key):
    return Fernet(draw_key).decrypt(data).decode('utf-8')


class Draw(db.Model):
    __tablename__ = 'draws'

    id = db.Column(db.Integer, primary_key=True)

    # ID of user who submitted draw
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)

    # 6 draw numbers submitted
    numbers = db.Column(db.String(200), nullable=False)
    # Draw has already been played (can only play draw once)
    been_played = db.Column(db.BOOLEAN, nullable=False, default=False)

    # Draw matches with master draw created by admin (True = draw is a winner)
    matches_master = db.Column(db.BOOLEAN, nullable=False, default=False)

    # True = draw is master draw created by admin. User draws are matched to master draw
    master_draw = db.Column(db.BOOLEAN, nullable=False)

    # Lottery round that draw is used
    lottery_round = db.Column(db.Integer, nullable=False, default=0)

    # Symmetric encryption
    # def __init__(self, user_id, numbers, master_draw, lottery_round, draw_key):

    # Asymmetric encryption
    def __init__(self, user_id, numbers, master_draw, lottery_round, public_key):
        self.user_id = user_id
        # Symmetric encryption
        # self.numbers = encrypt(numbers, draw_key)

        # Asymmetric encryption
        self.numbers = rsa.encrypt(numbers.encode(), public_key)
        self.been_played = False
        self.matches_master = False
        self.master_draw = master_draw
        self.lottery_round = lottery_round

    # Symmetric decryption function
    # def view_numbers(self, draw_key):
    #    self.numbers = decrypt(self.numbers, draw_key)

    # Asymmetric decryption function
    def view_numbers(self, private_key):
        self.numbers = rsa.decrypt(self.numbers, private_key).decode()


def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        public_key, private_key = rsa.newkeys(512)
        admin = User(email='admin@email.com',
                     password='Admin1!',
                     firstname='Alice',
                     lastname='Jones',
                     birthdate='01/01/1999',
                     postcode='NE4 5SA',
                     phone='0191-123-4567',
                     role='admin',
                     public_key=public_key,
                     private_key=private_key)

        db.session.add(admin)
        db.session.commit()
