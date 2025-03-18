# app/routes.py

from app import app
from flask import render_template, flash, redirect, url_for
from app.forms import LoginForm

@app.route('/')
@app.route('/index')
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
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login solicitado para o usuario {}, remember me ={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('index')) 
    return render_template('login.html', title='Sign In', form=form)