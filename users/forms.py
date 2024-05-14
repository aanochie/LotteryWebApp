from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms.validators import *
import re


# Checks for invalid chars in input field
def char_check(form, field):
    excluded_chars = "*?!'^+%&/()=}][{$#@<>"
    for char in field.data:
        if char in excluded_chars:
            raise ValidationError("Characters: *?!'^+%&/()=}][{$#@<> are not allowed")


# Checks for password in correct format
def password_check(form, password):
    p = re.compile(r'(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*\W)')
    if not p.match(password.data):
        raise ValidationError("Password must be inbetween 6 and 12 characters. Password must contain at least 1"
                              "digit, 1 lowercase, 1 uppercase word character. Must contain at least 1 symbol.")


# Checks for phone number in correct format
def phone_format(form, phone):
    p = re.compile("[0-9]{4}-[0-9]{3}-[0-9]{4}")
    if not p.match(phone.data):
        raise ValidationError("Phone number should be in the format 1234-123-1234 including dashes.")


# Checks for birthdate in correct format
def birthdate_format(form, birthdate):
    p = re.compile("^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/((19|20)[0-9]{2})$")
    if not p.match(birthdate.data):
        raise ValidationError("Birthdate should be in format DD/MM/YYYY")


# Checks for postcode in correct format
def postcode_format(form, postcode):
    p = re.compile("^[A-Z][0-9] [0-9][A-Z]{2}$|^[A-Z][0-9]{2} [0-9][A-Z]{2}$"
                   "|^[A-Z]{2}[0-9] [0-9][A-Z]{2}$")
    if not p.match(postcode.data):
        raise ValidationError("Invalid postcode. Should be in format XY YXX, XYY YXX, XXY YXX. X are capital letters"
                              " Y are digits.")


class RegisterForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Email()])
    firstname = StringField(validators=[InputRequired(), char_check])
    lastname = StringField(validators=[InputRequired(), char_check])
    birthdate = StringField(validators=[InputRequired(), birthdate_format])
    postcode = StringField(validators=[InputRequired(), postcode_format])
    phone = StringField(validators=[InputRequired(), phone_format])
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=12), password_check])
    confirm_password = PasswordField(validators=[InputRequired(), EqualTo('password',
                                                                        message='Both password fields must be equal')])
    submit = SubmitField()


class LoginForm(FlaskForm):
    recaptcha = RecaptchaField()
    email = StringField(validators=[InputRequired(), Email()])
    password = PasswordField(validators=[InputRequired()])
    postcode = StringField(validators=[InputRequired()])
    pin = StringField(validators=[InputRequired()])
    submit = SubmitField()


class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField(id='password', validators=[InputRequired()])
    show_password = BooleanField('Show password', id='check')
    new_password = PasswordField(validators=[InputRequired(), NoneOf(['<', '>', '&', '%']), Length(min=4, max=15),
                                             password_check])
    confirm_new_password = PasswordField(validators=[InputRequired(), EqualTo('new_password',
                                                        message='Both new password fields must be equal')])
    submit = SubmitField()
