# app/routes.py

from urllib.parse import urlsplit
from app import app, db
from flask import render_template, flash, redirect, url_for, request
from app.forms import LoginForm, RegistrationForm
from app.models import User

from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa


@app.route('/')
@app.route('/index')
@login_required
def index():
    user = {'username': 'Rian'}
    posts = [
        {
            'author': {'username': 'Maria'},
            'body': 'Bora para folia!'
        },
        {
            'author': {'username': 'João'},
            'body': 'Belo dia em Vila Velha!'
        },
    ]
    return render_template('index.html', user=user, posts=posts)

@app.route('/login', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password (form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)

        next_page = request.args.get('next')
        if next_page:
            parsed_url = urlsplit(next_page)
            if parsed_url.netloc == '' and parsed_url.path.startswith('/'):
                return redirect(next_page) 
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    return render_template('user.html', user=user, posts=posts) 