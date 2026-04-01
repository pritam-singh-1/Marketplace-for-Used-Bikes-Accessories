from flask import jsonify, request, session

from ..database import db


def register_offer_routes(app):
    @app.route('/offer/make', methods=['POST'])
    def make_offer():
        if not session.get('uid'):
            return jsonify({'error': 'Login required'}), 401
        d = request.json or {}
        listing_id = d.get('listing_id')
        amount = d.get('amount')
        if listing_id is None or amount is None:
            return jsonify({'error': 'listing_id and amount are required'}), 400
        c = db()
        item = c.execute('SELECT * FROM listings WHERE id=?', (listing_id,)).fetchone()
        if not item:
            c.close()
            return jsonify({'error': 'Listing not found'}), 404
        if item['status'] != 'active':
            c.close()
            return jsonify({'error': 'Listing is not available'}), 400
        if item['seller_id'] == session['uid']:
            c.close()
            return jsonify({'error': 'Cannot offer on own listing'}), 400
        c.execute('INSERT INTO offers(listing_id,buyer_id,seller_id,amount,message) VALUES(?,?,?,?,?)',
            (listing_id, session['uid'], item['seller_id'], amount, d.get('message', '')))
        c.commit()
        c.close()
        return jsonify({'ok': True, 'msg': 'Offer sent!'})

    @app.route('/offer/<int:oid>/respond', methods=['POST'])
    def respond_offer(oid):
        if not session.get('uid'):
            return jsonify({'error': 'Unauthorized'}), 401
        payload = request.json or {}
        status = payload.get('status')
        if status not in {'accepted', 'rejected', 'pending'}:
            return jsonify({'error': 'Invalid status'}), 400
        c = db()
        c.execute('UPDATE offers SET status=? WHERE id=? AND seller_id=?', (status, oid, session['uid']))
        c.commit()
        c.close()
        return jsonify({'ok': True})
