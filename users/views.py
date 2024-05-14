# IMPORTS
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
from markupsafe import Markup
from datetime import datetime
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User
from users.forms import RegisterForm, LoginForm, UpdatePasswordForm
import logging
import rsa

# CONFIG
users_blueprint = Blueprint('users', __name__, template_folder='templates')


# VIEWS
# view registration
@users_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    # create signup form object
    form = RegisterForm()

    # if request method is POST or form is valid
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        # if email already exists redirect user back to signup page with error message so user can try again
        if user:
            flash('Email address already exists')
            return render_template('users/register.html', form=form)

        # create a new user with the form data
        public_key, private_key = rsa.newkeys(512)
        new_user = User(email=form.email.data,
                        firstname=form.firstname.data,
                        lastname=form.lastname.data,
                        birthdate=form.birthdate.data,
                        postcode=form.postcode.data,
                        phone=form.phone.data,
                        password=form.password.data,
                        role='user',
                        public_key=public_key,
                        private_key=private_key)

        # add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        # logging the user register activity
        logging.warning('SECURITY - User registration [%s, %s]',
                        form.email.data,
                        request.remote_addr)

        # Username stored in app session
        session['email'] = new_user.email

        # sends user to 2-factor authentication page
        return redirect(url_for('users.setup_2fa'))
    # if request method is GET or form not valid re-render signup page
    return render_template('users/register.html', form=form)


@users_blueprint.route('/setup_2fa')
def setup_2fa():
    # Redirect user to home page if the username is not in the app session
    if 'email' not in session:
        return redirect(url_for('index'))

    # Retrieve user entry from the database
    user = User.query.filter_by(email=session['email']).first()
    # Check if user exist
    if not user:
        return redirect(url_for('index'))
    del session['email']

    return (render_template('users/setup_2fa.html', email=user.email, uri=user.get_2fa_uri())
            , 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })


# view user login
@users_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # Checks if the session contains an authentication_attempts key
    if not session.get('authentication_attempts'):
        session['authentication_attempts'] = 0

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        # if the login attempt fails the authentication attempt count is incremented
        if (not user or not user.verify_password(form.password.data) or not user.verify_pin(form.pin.data) or
                not user.verify_postcode(form.postcode.data)):

            session['authentication_attempts'] += 1

            # Logging of invalid login attempt
            logging.warning('SECURITY- Invalid Log In Attempt [%s, %s]',
                            form.email.data,
                            request.remote_addr)

            # Once the limit is reached the login is blocked and user is given option to reset attempts
            if session.get('authentication_attempts') >= 3:
                flash(Markup('Number of incorrect login attempts exceeded.'
                             ' Please click <a href="/reset">here</a> to reset.'))
                return render_template('users/login.html')

            attempts_remaining = 3 - session.get('authentication_attempts')
            flash('Please check your login details and try again,'
                  ' {} login attempts remaining'.format(attempts_remaining))

            return render_template('users/login.html', form=form)
        else:
            # Logs the user in
            login_user(user)

            # Logging the successful log in
            logging.warning('SECURITY - Log in [%s, %s, %s]',
                            current_user.id,
                            current_user.email,
                            request.remote_addr)

            # Assign last login time and ip
            current_user.last_login = current_user.current_login
            current_user.last_login_ip = current_user.current_login_ip
            # Assign current login to current date, time and ip
            current_user.current_login = datetime.now()
            current_user.current_login_ip = request.remote_addr
            # Add to total successful logins
            current_user.total_logins += 1
            db.session.commit()

            # Redirects user to links specific to its role
            if current_user.role == 'admin':
                return redirect(url_for('admin.admin'))
            else:
                return redirect(url_for('lottery.lottery'))

    return render_template('users/login.html', form=form)


# Resets the exceeded authentication attempt number to 0
@users_blueprint.route('/reset')
def reset():
    session['authentication_attempts'] = 0
    return redirect(url_for('users.login'))


# Log out user
@users_blueprint.route('/logout')
@login_required
def logout():
    # logging the logout of user
    logging.warning('SECURITY - Log out [%s, %s, %s, %s]',
                    current_user.id,
                    current_user.email,
                    current_user.role,
                    request.remote_addr)
    logout_user()
    return redirect(url_for('index'))


# view user account
@users_blueprint.route('/account')
@login_required
def account():
    return render_template('users/account.html',
                           acc_no=current_user.id,
                           email=current_user.email,
                           firstname=current_user.firstname,
                           lastname=current_user.lastname,
                           birthdate=current_user.birthdate,
                           postcode=current_user.postcode,
                           phone=current_user.phone,
                           role=current_user.role)


# view update user account password
@users_blueprint.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    form = UpdatePasswordForm()

    if form.validate_on_submit():
        if current_user.password != form.current_password.data:
            flash('Current password is incorrect')
            return render_template('users/update_password.html', form=form)

        if current_user.password == form.new_password.data:
            flash('New password is the same as the current password')
            return render_template('users/update_password.html', form=form)

        current_user.password = form.new_password.data
        # save changed password to database
        db.session.commit()
        flash('Password changed successfully')

        return redirect(url_for('users.account'))

    return render_template('users/update_password.html', form=form)
