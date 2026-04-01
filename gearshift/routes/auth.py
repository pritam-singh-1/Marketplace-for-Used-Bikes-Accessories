import sqlite3

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..database import db


def register_auth_routes(app):
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            d = request.form
            c = db()
            try:
                c.execute('INSERT INTO users(username,email,password,full_name,phone,location) VALUES(?,?,?,?,?,?)',
                    (d['username'], d['email'], generate_password_hash(d['password']), d['full_name'], d.get('phone', ''), d.get('location', '')))
                c.commit()
                u = c.execute('SELECT * FROM users WHERE username=?', (d['username'],)).fetchone()
                session['uid'] = u['id']
                session['uname'] = u['username']
                c.close()
                flash('Welcome to GearShift! Start riding.', 'success')
                return redirect(url_for('index'))
            except sqlite3.IntegrityError:
                c.close()
                flash('Username or email already taken.', 'error')
        return render_template('auth.html', mode='register')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            c = db()
            u = c.execute('SELECT * FROM users WHERE email=? OR username=?', (request.form['login'],) * 2).fetchone()
            c.close()
            if u and check_password_hash(u['password'], request.form['password']):
                session['uid'] = u['id']
                session['uname'] = u['username']
                flash(f'Back in gear, {u["full_name"] or u["username"]}!', 'success')
                return redirect(url_for('index'))
            flash('Invalid credentials.', 'error')
        return render_template('auth.html', mode='login')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))
