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
        item = c.execute('''SELECT l.*,u.username,u.full_name
            FROM listings l JOIN users u ON l.seller_id=u.id
            WHERE l.id=? AND l.status="active"''', (lid,)).fetchone()
        c.close()
        if not item:
            return redirect(url_for('browse'))
        if item['seller_id'] == session['uid']:
            return redirect(url_for('listing', lid=lid))
        return render_template('checkout.html', item=item)

    @app.route('/payment/process', methods=['POST'])
    def process_payment():
        if not session.get('uid'):
            return jsonify({'error': 'Unauthorized'}), 401
        d = request.json or {}
        listing_id = d.get('listing_id')
        seller_id = d.get('seller_id')
        amount = d.get('amount')
        method = d.get('method')
        if listing_id is None or seller_id is None or amount is None or not method:
            return jsonify({'error': 'listing_id, seller_id, amount and method are required'}), 400
        tx = 'GS' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        c = db()
        listing = c.execute(
            'SELECT id,seller_id,price,status FROM listings WHERE id=?',
            (listing_id,)
        ).fetchone()
        if not listing or listing['status'] != 'active':
            c.close()
            return jsonify({'error': 'Listing is not available'}), 400
        if listing['seller_id'] != seller_id:
            c.close()
            return jsonify({'error': 'Invalid seller'}), 400
        if listing['seller_id'] == session['uid']:
            c.close()
            return jsonify({'error': 'Invalid seller'}), 400
        if float(amount) != float(listing['price']):
            c.close()
            return jsonify({'error': 'Invalid amount'}), 400
        c.execute('INSERT INTO orders(listing_id,buyer_id,seller_id,amount,method,tx_id) VALUES(?,?,?,?,?,?)',
            (listing_id, session['uid'], seller_id, amount, method, tx))
        c.execute('UPDATE listings SET status="sold" WHERE id=?', (listing_id,))
        c.commit()
        c.close()
        return jsonify({'ok': True, 'tx': tx})
