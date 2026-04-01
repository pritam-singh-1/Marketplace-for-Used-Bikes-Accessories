from flask import flash, jsonify, redirect, render_template, request, session, url_for

from ..database import db


def register_dashboard_routes(app):
    @app.route('/dashboard')
    def dashboard():
        if not session.get('uid'):
            return redirect(url_for('login'))
        c = db()
        uid = session['uid']
        u = c.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
        my_listings = c.execute('SELECT * FROM listings WHERE seller_id=? AND status!="deleted" ORDER BY created_at DESC', (uid,)).fetchall()
        offers_in = c.execute('''SELECT o.*,u.username as bname,l.title as ltitle,l.price as lprice
            FROM offers o JOIN users u ON o.buyer_id=u.id JOIN listings l ON o.listing_id=l.id
            WHERE o.seller_id=? AND o.status="pending" ORDER BY o.created_at DESC''', (uid,)).fetchall()
        offers_out = c.execute('''SELECT o.*,l.title as ltitle,u.username as sname
            FROM offers o JOIN listings l ON o.listing_id=l.id JOIN users u ON o.seller_id=u.id
            WHERE o.buyer_id=? ORDER BY o.created_at DESC LIMIT 5''', (uid,)).fetchall()
        purchases = c.execute('''SELECT ord.*,l.title FROM orders ord
            JOIN listings l ON ord.listing_id=l.id WHERE ord.buyer_id=? ORDER BY ord.created_at DESC LIMIT 5''', (uid,)).fetchall()
        bookings = c.execute('''SELECT sb.*,m.name as mname FROM service_bookings sb
            LEFT JOIN mechanics m ON sb.mechanic_id=m.id WHERE sb.user_id=? ORDER BY sb.created_at DESC LIMIT 5''', (uid,)).fetchall()
        favs = c.execute('''SELECT l.*,u.username FROM favorites f
            JOIN listings l ON f.listing_id=l.id JOIN users u ON l.seller_id=u.id
            WHERE f.user_id=? AND l.status="active"''', (uid,)).fetchall()
        unread = c.execute('SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0', (uid,)).fetchone()[0]
        c.close()
        return render_template('dashboard.html', u=u, my_listings=my_listings,
            offers_in=offers_in, offers_out=offers_out, purchases=purchases,
            bookings=bookings, favs=favs, unread=unread)

    @app.route('/profile/<username>')
    def profile(username):
        c = db()
        u = c.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if not u:
            c.close()
            return redirect(url_for('index'))
        listings = c.execute('SELECT * FROM listings WHERE seller_id=? AND status="active" ORDER BY created_at DESC', (u['id'],)).fetchall()
        reviews = c.execute('''SELECT r.*,u.username FROM reviews r
            JOIN users u ON r.reviewer_id=u.id WHERE r.reviewed_id=? ORDER BY r.created_at DESC LIMIT 8''', (u['id'],)).fetchall()
        c.close()
        return render_template('profile.html', u=u, listings=listings, reviews=reviews)

    @app.route('/profile/edit', methods=['GET', 'POST'])
    def edit_profile():
        if not session.get('uid'):
            return redirect(url_for('login'))
        c = db()
        u = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
        if request.method == 'POST':
            d = request.form
            c.execute('UPDATE users SET full_name=?,phone=?,location=?,bio=? WHERE id=?',
                (d['full_name'], d['phone'], d['location'], d['bio'], session['uid']))
            c.commit()
            c.close()
            flash('Profile updated!', 'success')
            return redirect(url_for('dashboard'))
        c.close()
        return render_template('edit_profile.html', u=u)

    @app.route('/fav/toggle', methods=['POST'])
    def fav_toggle():
        if not session.get('uid'):
            return jsonify({'error': 'Login required'}), 401
        d = request.json or {}
        lid = d.get('lid')
        if lid is None:
            return jsonify({'error': 'lid is required'}), 400
        c = db()
        ex = c.execute('SELECT id FROM favorites WHERE user_id=? AND listing_id=?', (session['uid'], lid)).fetchone()
        if ex:
            c.execute('DELETE FROM favorites WHERE user_id=? AND listing_id=?', (session['uid'], lid))
            state = 'removed'
        else:
            c.execute('INSERT INTO favorites(user_id,listing_id) VALUES(?,?)', (session['uid'], lid))
            state = 'added'
        c.commit()
        c.close()
        return jsonify({'ok': True, 'state': state})
