# IMPORTS
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from lottery.forms import DrawForm
from models import Draw, User
from sqlalchemy.orm import make_transient
import pickle

# CONFIG
lottery_blueprint = Blueprint('lottery', __name__, template_folder='templates')


# VIEWS
# view lottery page
@lottery_blueprint.route('/lottery')
@login_required
def lottery():
    return render_template('lottery/lottery.html', name=current_user.firstname)


# view all draws that have not been played
@lottery_blueprint.route('/create_draw', methods=['POST'])
def create_draw():
    form = DrawForm()

    if not form.validate():
        flash("Draw numbers must be unique")
        return render_template('lottery/lottery.html', name=current_user.firstname, form=form)

    if form.validate_on_submit():
        if (not form.number1.data or not form.number2.data or not form.number3.data or not form.number4.data
                or not form.number5.data or not form.number6.data):
            flash("Draw must contain 6 numbers between 1 and 60")
            return render_template('lottery/lottery.html', name=current_user.firstname, form=form)

        if ((form.number1.data > 60 or form.number1.data < 0) or (form.number2.data > 60 or form.number2.data < 0) or
                (form.number3.data > 60 or form.number3.data < 0) or (form.number4.data > 60 or form.number4.data < 0)
                or (form.number5.data > 60 or form.number5.data < 0) or
                (form.number6.data > 60 or form.number6.data < 0)):
            flash("Draw numbers must be in between 1 and 60")
            return render_template('lottery/lottery.html', name=current_user.firstname, form=form)

        submitted_numbers = (str(form.number1.data) + ' '
                             + str(form.number2.data) + ' '
                             + str(form.number3.data) + ' '
                             + str(form.number4.data) + ' '
                             + str(form.number5.data) + ' '
                             + str(form.number6.data))
        # Symmetric create a new draw with the form data.
        # new_draw = Draw(user_id=current_user.id, numbers=submitted_numbers, master_draw=False, lottery_round=0,
        #                 draw_key=current_user.draw_pin)

        # Asymmetric create a new draw with the form data
        crypto_key = pickle.loads(current_user.public_key)
        new_draw = Draw(user_id=current_user.id, numbers=submitted_numbers, master_draw=False, lottery_round=0,
                        public_key=crypto_key)

        # add the new draw to the database
        db.session.add(new_draw)
        db.session.commit()

        # re-render lottery.page
        flash('Draw %s submitted.' % submitted_numbers)
        return redirect(url_for('lottery.lottery'))

    return render_template('lottery/lottery.html', name=current_user.firstname, form=form)


# view all draws that have not been played
@lottery_blueprint.route('/view_draws', methods=['POST'])
def view_draws():
    # get all draws that have not been played [played=0]
    playable_draws = Draw.query.filter_by(been_played=False, user_id=current_user.id).all()
    '''
    # Symmetric decryption of each draw queried before view in it in browser
     for draw in playable_draws:
        # Making draw transient so the draw numbers are not readable in plain text in db
         make_transient(draw)
         draw.view_numbers(current_user.draw_pin)
     '''
    # Asymmetric decryption
    for draw in playable_draws:
        make_transient(draw)
        crypto_key = pickle.loads(current_user.private_key)
        draw.view_numbers(crypto_key)

    # if playable draws exist
    if len(playable_draws) != 0:
        # re-render lottery page with playable draws
        return render_template('lottery/lottery.html', playable_draws=playable_draws)
    else:
        flash('No playable draws.')
        return lottery()


# view lottery results
@lottery_blueprint.route('/check_draws', methods=['POST'])
def check_draws():
    # get played draws
    played_draws = Draw.query.filter_by(been_played=True, user_id=current_user.id).all()

    # if played draws exist
    if len(played_draws) != 0:
        return render_template('lottery/lottery.html', results=played_draws, played=True,
                               name=current_user.firstname)

    # if no played draws exist [all draw entries have been played therefore wait for next lottery round]
    else:
        flash("Next round of lottery yet to play. Check you have playable draws.")
        return lottery()


# delete all played draws
@lottery_blueprint.route('/play_again', methods=['POST'])
def play_again():
    Draw.query.filter_by(been_played=True, master_draw=False, user_id=current_user.id).delete(synchronize_session=False)
    db.session.commit()

    flash("All played draws deleted.")
    return lottery()
