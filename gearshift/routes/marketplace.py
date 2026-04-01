import json
import os
from datetime import datetime

from flask import current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from ..database import db
from ..utils import allowed


def register_marketplace_routes(app):
    @app.route('/')
    def index():
        c = db()
        featured = c.execute('''SELECT l.*,u.username,u.rating as sr,u.is_verified
            FROM listings l JOIN users u ON l.seller_id=u.id
            WHERE l.status="active" ORDER BY l.created_at DESC LIMIT 8''').fetchall()
        stats = {
            'listings': c.execute('SELECT COUNT(*) FROM listings WHERE status="active"').fetchone()[0],
            'users': c.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'sold': c.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
        }
        c.close()
        return render_template('index.html', featured=featured, stats=stats)

    @app.route('/browse')
    def browse():
        c = db()
        q = request.args.get('q', '')
        cat = request.args.get('category', '')
        cond = request.args.get('condition', '')
        minp = request.args.get('min_price', 0)
        maxp = request.args.get('max_price', 999999)
        sort = request.args.get('sort', 'newest')
        sql = '''SELECT l.*,u.username,u.rating as sr,u.is_verified
            FROM listings l JOIN users u ON l.seller_id=u.id WHERE l.status="active"'''
        params = []
        if q:
            sql += ' AND (l.title LIKE ? OR l.brand LIKE ? OR l.description LIKE ?)'
            params += [f'%{q}%'] * 3
        if cat:
            sql += ' AND l.category=?'
            params.append(cat)
        if cond:
            sql += ' AND l.condition=?'
            params.append(cond)
        sql += ' AND l.price BETWEEN ? AND ?'
        params += [minp, maxp]
        order_map = {
            'newest': 'l.created_at DESC',
            'price_low': 'l.price ASC',
            'price_high': 'l.price DESC',
            'popular': 'l.views DESC',
        }
        order = order_map.get(sort, order_map['newest'])
        sql += f' ORDER BY {order}'
        listings = c.execute(sql, params).fetchall()
        c.close()
        return render_template('browse.html', listings=listings, q=q, category=cat, condition=cond, sort=sort)

    @app.route('/listing/<int:lid>')
    def listing(lid):
        c = db()
        c.execute('UPDATE listings SET views=views+1 WHERE id=?', (lid,))
        c.commit()
        item = c.execute('''SELECT l.*,u.username,u.full_name,u.rating as sr,u.is_verified,
            u.reviews_count,u.location as sloc,u.joined
            FROM listings l JOIN users u ON l.seller_id=u.id WHERE l.id=?''', (lid,)).fetchone()
        if not item:
            c.close()
            return redirect(url_for('browse'))
        others = c.execute('SELECT * FROM listings WHERE seller_id=? AND id!=? AND status="active" LIMIT 3', (item['seller_id'], lid)).fetchall()
        fav = bool(session.get('uid') and c.execute('SELECT id FROM favorites WHERE user_id=? AND listing_id=?', (session['uid'], lid)).fetchone())
        c.close()
        return render_template('listing.html', item=item, others=others, fav=fav)

    @app.route('/listing/new', methods=['GET', 'POST'])
    def new_listing():
        if not session.get('uid'):
            return redirect(url_for('login'))
        if request.method == 'POST':
            d = request.form
            imgs = []
            for f in request.files.getlist('images'):
                if f and allowed(f.filename):
                    fn = f'{int(datetime.now().timestamp())}_{secure_filename(f.filename)}'
                    f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], fn))
                    imgs.append(fn)
            c = db()
            c.execute('''INSERT INTO listings(seller_id,title,category,brand,model,year,condition,
                price,negotiable,description,frame_size,color,mileage,location,service_history,images)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (session['uid'], d['title'], d['category'], d['brand'], d['model'],
                 d.get('year'), d['condition'], d['price'], int(d.get('negotiable', 0)),
                 d['description'], d.get('frame_size'), d.get('color'), d.get('mileage'),
                 d['location'], d.get('service_history', ''), json.dumps(imgs)))
            c.commit()
            lid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
            c.close()
            flash('Listing published!', 'success')
            return redirect(url_for('listing', lid=lid))
        return render_template('new_listing.html', listing=None)

    @app.route('/listing/<int:lid>/edit', methods=['GET', 'POST'])
    def edit_listing(lid):
        if not session.get('uid'):
            return redirect(url_for('login'))
        c = db()
        item = c.execute('SELECT * FROM listings WHERE id=? AND seller_id=?', (lid, session['uid'])).fetchone()
        if not item:
            c.close()
            flash('Not found.', 'error')
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            d = request.form
            c.execute('''UPDATE listings SET title=?,category=?,brand=?,model=?,year=?,condition=?,
                price=?,negotiable=?,description=?,frame_size=?,color=?,mileage=?,location=?,service_history=?
                WHERE id=?''', (d['title'], d['category'], d['brand'], d['model'], d.get('year'),
                d['condition'], d['price'], int(d.get('negotiable', 0)), d['description'],
                d.get('frame_size'), d.get('color'), d.get('mileage'), d['location'],
                d.get('service_history', ''), lid))
            c.commit()
            c.close()
            flash('Listing updated!', 'success')
            return redirect(url_for('listing', lid=lid))
        c.close()
        return render_template('new_listing.html', listing=item)

    @app.route('/listing/<int:lid>/delete', methods=['POST'])
    def delete_listing(lid):
        if not session.get('uid'):
            return jsonify({'error': 'Unauthorized'}), 401
        c = db()
        c.execute('UPDATE listings SET status="deleted" WHERE id=? AND seller_id=?', (lid, session['uid']))
        c.commit()
        c.close()
        return jsonify({'ok': True})
