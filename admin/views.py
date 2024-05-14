# IMPORTS
import random

import rsa
from flask import Blueprint, render_template, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db, requires_roles
from models import User, Draw, encrypt
from users.forms import RegisterForm
from sqlalchemy.orm import make_transient
import pickle
import secrets

# CONFIG
admin_blueprint = Blueprint('admin', __name__, template_folder='templates')


# VIEWS
# view admin homepage
@admin_blueprint.route('/admin')
@login_required
@requires_roles('admin')
def admin():
    return render_template('admin/admin.html', name=current_user.firstname)


# create a new winning draw
@admin_blueprint.route('/generate_winning_draw')
@login_required
@requires_roles('admin')
def generate_winning_draw():
    # get current winning draw
    current_winning_draw = Draw.query.filter_by(master_draw=True).first()
    lottery_round = 1

    # if a current winning draw exists
    if current_winning_draw:
        # update lottery round by 1
        lottery_round = current_winning_draw.lottery_round + 1

        # delete current winning draw
        db.session.delete(current_winning_draw)
        db.session.commit()

    # get new winning numbers for draw using cryptographically secure random numbers generation
    # Empty set created as set cannot contain duplicates
    winning_numbers_set = set()
    while len(winning_numbers_set) < 6:
        winning_numbers_set.add(secrets.choice(range(1, 60)))

    winning_numbers_set = sorted(winning_numbers_set)

    winning_numbers_string = ''
    for i in range(6):
        winning_numbers_string += str(winning_numbers_set[i]) + ' '
    winning_numbers_string = winning_numbers_string[:-1]

    # create a new draw object
    # Symmetric encryption
    # new_winning_draw = Draw(user_id=current_user.id, numbers=winning_numbers_string, master_draw=True,
    #                        lottery_round=lottery_round, draw_key=current_user.draw_pin)

    # Asymmetric encryption
    crypto_key = pickle.loads(current_user.public_key)
    new_winning_draw = Draw(user_id=current_user.id, numbers=winning_numbers_string, master_draw=True,
                            lottery_round=lottery_round, public_key=crypto_key)

    # add the new winning draw to the database
    db.session.add(new_winning_draw)
    db.session.commit()

    # re-render admin page
    flash("New winning draw %s added." % winning_numbers_string)
    return redirect(url_for('admin.admin'))


# view current winning draw
@admin_blueprint.route('/view_winning_draw')
@login_required
@requires_roles('admin')
def view_winning_draw():
    # get winning draw from DB
    current_winning_draw = Draw.query.filter_by(master_draw=True, been_played=False).first()

    # if a winning draw exists
    if current_winning_draw:
        # Decrypt current winning draw
        make_transient(current_winning_draw)
        # Symmetric decrypting
        # current_winning_draw.view_numbers(current_user.draw_pin)

        # Asymmetric decrypting
        crypto_key = pickle.loads(current_user.private_key)
        current_winning_draw.view_numbers(crypto_key)

        # re-render admin page with current winning draw and lottery round
        return render_template('admin/admin.html', winning_draw=current_winning_draw,
                               name=current_user.firstname)

    # if no winning draw exists, rerender admin page with flash message
    flash("No valid winning draw exists. Please add new winning draw.")
    return redirect(url_for('admin.admin'))


# view lottery results and winners
@admin_blueprint.route('/run_lottery')
@login_required
@requires_roles('admin')
def run_lottery():
    # get current unplayed winning draw
    current_winning_draw = Draw.query.filter_by(master_draw=True, been_played=False).first()

    # if current unplayed winning draw exists
    if current_winning_draw:

        # get all unplayed user draws
        user_draws = Draw.query.filter_by(master_draw=False, been_played=False).all()

        results = []

        # if at least one unplayed user draw exists
        if user_draws:

            # update current winning draw as played
            current_winning_draw.been_played = True

            db.session.add(current_winning_draw)
            db.session.commit()

            # Decrypting draw numbers for winning user
            winning_draw_creator = User.query.filter_by(id=current_winning_draw.user_id).first()
            make_transient(current_winning_draw)
            # Symmetric decryption
            # current_winning_draw.view_numbers(winning_draw_creator.draw_pin)

            # Asymmetric decryption
            w_draw_crypto_key = pickle.loads(winning_draw_creator.private_key)
            current_winning_draw.view_numbers(w_draw_crypto_key)

            # for each un-played user draw
            for draw in user_draws:

                # get the owning user (instance/object)
                user = User.query.filter_by(id=draw.user_id).first()

                # Symmetric decryption
                # draw.view_numbers(user.draw_pin)

                # Asymmetric decryption
                crypto_key = pickle.loads(user.private_key)
                draw.view_numbers(crypto_key)

                # if user draw matches current un-played winning draw
                if draw.numbers == current_winning_draw.numbers:
                    # add details of winner to list of results
                    results.append((current_winning_draw.lottery_round, draw.numbers, draw.user_id, user.email))

                    # update draw as a winning draw (this will be used to highlight winning draws in the user's
                    # lottery page)
                    draw.matches_master = True

                # update draw as played
                draw.been_played = True

                # update draw with current lottery round
                draw.lottery_round = current_winning_draw.lottery_round

                # commit draw changes to DB
                db.session.add(draw)
                db.session.commit()

            if len(results) == 0:
                flash("No winners.")

            return render_template('admin/admin.html', results=results,
                                   name=current_user.firstname)

        flash("No user draws entered.")
        return admin()

    # if current un-played winning draw does not exist
    flash("Current winning draw expired. Add new winning draw for next round.")
    return redirect(url_for('admin.admin'))


# view all registered users
@admin_blueprint.route('/view_all_users')
@login_required
@requires_roles('admin')
def view_all_users():
    current_users = User.query.filter_by(role='user').all()

    return render_template('admin/admin.html', name=current_user.firstname,
                           current_users=current_users)


# view last 10 log entries
@admin_blueprint.route('/logs')
@login_required
@requires_roles('admin')
def logs():
    with open("lottery.log", "r") as f:
        content = f.read().splitlines()[-10:]
        content.reverse()

    return render_template('admin/admin.html', logs=content, name=current_user.firstname)


# register admin users
@admin_blueprint.route('/register_admin', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def register_admin():
    form = RegisterForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # if this returns a user, then the email already exists in database

        # if email already exists redirect user back to signup page with error message so user can try again
        if user:
            flash('Email address already exists')
            return render_template('users/register.html', form=form)

        # create a new admin user with the form data
        public_key, private_key = rsa.newkeys(512)
        new_admin = User(email=form.email.data,
                         firstname=form.firstname.data,
                         lastname=form.lastname.data,
                         birthdate=form.birthdate.data,
                         postcode=form.postcode.data,
                         phone=form.phone.data,
                         password=form.password.data,
                         role='admin',
                         public_key=public_key,
                         private_key=private_key)

        # add the new user to the database
        db.session.add(new_admin)
        db.session.commit()
        flash('New admin user registered successfully')

        # Username stored in app session
        session['email'] = new_admin.email

        return redirect(url_for('admin.admin'))

    # if request method is GET or form not valid re-render signup page
    return render_template('users/register.html', form=form)
