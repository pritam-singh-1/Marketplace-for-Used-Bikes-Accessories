from flask import jsonify, redirect, render_template, request, session, url_for

from ..database import db


def register_message_routes(app):
    @app.route('/messages')
    def messages():
        if not session.get('uid'):
            return redirect(url_for('login'))
        c = db()
        convos = c.execute('''SELECT DISTINCT
            CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END as oid,
            MAX(created_at) as lt, listing_id
            FROM messages WHERE sender_id=? OR receiver_id=?
            GROUP BY oid,listing_id ORDER BY lt DESC''', (session['uid'],) * 3).fetchall()
        result = []
        for cv in convos:
            other = c.execute('SELECT id,username,full_name FROM users WHERE id=?', (cv['oid'],)).fetchone()
            lst = c.execute('SELECT id,title FROM listings WHERE id=?', (cv['listing_id'],)).fetchone()
            last = c.execute('''SELECT * FROM messages WHERE
                ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?))
                AND listing_id=? ORDER BY created_at DESC LIMIT 1''',
                (session['uid'], cv['oid'], cv['oid'], session['uid'], cv['listing_id'])).fetchone()
            unread = c.execute('SELECT COUNT(*) FROM messages WHERE sender_id=? AND receiver_id=? AND listing_id=? AND is_read=0',
                (cv['oid'], session['uid'], cv['listing_id'])).fetchone()[0]
            if other and lst and last:
                result.append({'other': other, 'listing': lst, 'last': last, 'unread': unread})
        c.close()
        return render_template('messages.html', convos=result)

    @app.route('/chat/<int:oid>/<int:lid>')
    def chat(oid, lid):
        if not session.get('uid'):
            return redirect(url_for('login'))
        c = db()
        c.execute('UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=? AND listing_id=?', (oid, session['uid'], lid))
        c.commit()
        msgs = c.execute('''SELECT m.*,u.username FROM messages m
            JOIN users u ON m.sender_id=u.id
            WHERE ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)) AND listing_id=?
            ORDER BY created_at''', (session['uid'], oid, oid, session['uid'], lid)).fetchall()
        other = c.execute('SELECT * FROM users WHERE id=?', (oid,)).fetchone()
        lst = c.execute('SELECT * FROM listings WHERE id=?', (lid,)).fetchone()
        c.close()
        return render_template('chat.html', msgs=msgs, other=other, lst=lst, lid=lid)

    @app.route('/messages/send', methods=['POST'])
    def send_msg():
        if not session.get('uid'):
            return jsonify({'error': 'Unauthorized'}), 401
        d = request.json or {}
        receiver_id = d.get('receiver_id')
        listing_id = d.get('listing_id')
        content = d.get('content')
        if receiver_id is None or listing_id is None or not content:
            return jsonify({'error': 'receiver_id, listing_id and content are required'}), 400
        c = db()
        c.execute('INSERT INTO messages(sender_id,receiver_id,listing_id,content) VALUES(?,?,?,?)',
            (session['uid'], receiver_id, listing_id, content))
        c.commit()
        m = c.execute('SELECT m.*,u.username FROM messages m JOIN users u ON m.sender_id=u.id WHERE m.sender_id=? ORDER BY m.created_at DESC LIMIT 1', (session['uid'],)).fetchone()
        c.close()
        return jsonify({'ok': True, 'msg': {'content': m['content'], 'created_at': m['created_at'], 'username': m['username']}})
