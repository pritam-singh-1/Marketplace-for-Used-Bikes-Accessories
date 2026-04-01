import random
import string

from flask import jsonify, redirect, render_template, request, session, url_for

from ..database import db


def register_checkout_routes(app):
    @app.route('/checkout/<int:lid>')
    def checkout(lid):
        if not session.get('uid'):
            return redirect(url_for('login'))
        c = db()
        item = c.execute('SELECT l.*,u.username,u.full_name FROM listings l JOIN users u ON l.seller_id=u.id WHERE l.id=?', (lid,)).fetchone()
        c.close()
        return render_template('checkout.html', item=item)

    @app.route('/payment/process', methods=['POST'])
    def process_payment():
        if not session.get('uid'):
            return jsonify({'error': 'Unauthorized'}), 401
        d = request.json
        tx = 'GS' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        c = db()
        c.execute('INSERT INTO orders(listing_id,buyer_id,seller_id,amount,method,tx_id) VALUES(?,?,?,?,?,?)',
            (d['listing_id'], session['uid'], d['seller_id'], d['amount'], d['method'], tx))
        c.execute('UPDATE listings SET status="sold" WHERE id=?', (d['listing_id'],))
        c.commit()
        c.close()
        return jsonify({'ok': True, 'tx': tx})
