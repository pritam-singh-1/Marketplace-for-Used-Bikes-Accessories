from flask import jsonify, request, session

from ..database import db


def register_offer_routes(app):
    @app.route('/offer/make', methods=['POST'])
    def make_offer():
        if not session.get('uid'):
            return jsonify({'error': 'Login required'}), 401
        d = request.json
        c = db()
        item = c.execute('SELECT * FROM listings WHERE id=?', (d['listing_id'],)).fetchone()
        if item['seller_id'] == session['uid']:
            c.close()
            return jsonify({'error': 'Cannot offer on own listing'}), 400
        c.execute('INSERT INTO offers(listing_id,buyer_id,seller_id,amount,message) VALUES(?,?,?,?,?)',
            (d['listing_id'], session['uid'], item['seller_id'], d['amount'], d.get('message', '')))
        c.commit()
        c.close()
        return jsonify({'ok': True, 'msg': 'Offer sent!'})

    @app.route('/offer/<int:oid>/respond', methods=['POST'])
    def respond_offer(oid):
        if not session.get('uid'):
            return jsonify({'error': 'Unauthorized'}), 401
        c = db()
        c.execute('UPDATE offers SET status=? WHERE id=? AND seller_id=?', (request.json['status'], oid, session['uid']))
        c.commit()
        c.close()
        return jsonify({'ok': True})
