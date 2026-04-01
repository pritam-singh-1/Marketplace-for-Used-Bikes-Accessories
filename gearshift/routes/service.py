from flask import jsonify, redirect, render_template, request, session, url_for

from ..database import db

SERVICE_PACKAGES = [
    {'id': 'tune', 'name': 'Quick Tune', 'price': 59, 'time': '2–3 hrs',
     'checklist': ['Safety check', 'Brake adjustment', 'Gear indexing', 'Tyre pressure', 'Chain lube']},
    {'id': 'standard', 'name': 'Full Service', 'price': 99, 'time': '4–5 hrs',
     'checklist': ['All in Quick Tune', 'Wheel truing', 'Cable replacement', 'BB check', 'Full clean', 'Bearing inspection']},
    {'id': 'overhaul', 'name': 'Premium Overhaul', 'price': 169, 'time': '6–8 hrs',
     'checklist': ['All in Full Service', 'Complete drivetrain strip', 'Headset service', 'Hub service', 'Hydraulic bleed', 'Written condition report']},
    {'id': 'ebike', 'name': 'E-Bike Specialist', 'price': 149, 'time': '5–6 hrs',
     'checklist': ['Battery health test', 'Motor diagnostic', 'Firmware update', 'Sensor calibration', 'Full Service items']},
]
SERVICE_PRICES = {p['id']: p['price'] for p in SERVICE_PACKAGES}


def register_service_routes(app):
    @app.route('/service')
    def service():
        c = db()
        mechs = c.execute('SELECT * FROM mechanics WHERE available=1').fetchall()
        c.close()
        return render_template('service.html', mechs=mechs, packages=SERVICE_PACKAGES)

    @app.route('/service/book', methods=['POST'])
    def book_service():
        if not session.get('uid'):
            return jsonify({'error': 'Login required'}), 401
        d = request.json or {}
        bike_info = d.get('bike_info')
        package = d.get('package')
        mechanic_id = d.get('mechanic_id')
        date = d.get('date')
        if not bike_info or not package or mechanic_id is None or not date:
            return jsonify({'error': 'bike_info, package, mechanic_id and date are required'}), 400
        if package not in SERVICE_PRICES:
            return jsonify({'error': 'Invalid package'}), 400
        c = db()
        c.execute('INSERT INTO service_bookings(user_id,bike_info,package,mechanic_id,scheduled_date,cost,notes) VALUES(?,?,?,?,?,?,?)',
            (session['uid'], bike_info, package, mechanic_id, date, SERVICE_PRICES[package], d.get('notes', '')))
        c.commit()
        bid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        c.close()
        return jsonify({'ok': True, 'bid': bid, 'ref': f'GS-SVC-{bid:04d}'})

    @app.route('/service/status/<int:bid>')
    def svc_status(bid):
        c = db()
        b = c.execute('SELECT * FROM service_bookings WHERE id=?', (bid,)).fetchone()
        c.close()
        if not b:
            return jsonify({'error': 'Not found'}), 404
        steps = ['pending', 'confirmed', 'in_progress', 'quality_check', 'complete']
        idx = steps.index(b['status']) if b['status'] in steps else 0
        return jsonify({'status': b['status'], 'step': idx + 1, 'total': len(steps)})

    @app.route('/service/bookings')
    def my_bookings():
        if not session.get('uid'):
            return redirect(url_for('login'))
        c = db()
        bkgs = c.execute('''SELECT sb.*,m.name as mname,m.rating as mrat
            FROM service_bookings sb LEFT JOIN mechanics m ON sb.mechanic_id=m.id
            WHERE sb.user_id=? ORDER BY sb.created_at DESC''', (session['uid'],)).fetchall()
        c.close()
        return render_template('bookings.html', bookings=bkgs)
