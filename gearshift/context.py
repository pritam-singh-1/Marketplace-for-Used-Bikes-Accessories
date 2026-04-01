from flask import session

from .database import db


def register_context_processors(app):
    @app.context_processor
    def globals():
        unread = 0
        if session.get('uid'):
            c = db()
            unread = c.execute('SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0', (session['uid'],)).fetchone()[0]
            c.close()
        return dict(uid=session.get('uid'), uname=session.get('uname'), unread=unread)
