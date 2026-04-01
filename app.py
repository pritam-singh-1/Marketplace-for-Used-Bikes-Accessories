from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, json, random, string
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'gearshift_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED

def db():
    conn = sqlite3.connect('gearshift.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        phone TEXT,
        location TEXT,
        bio TEXT,
        avatar TEXT,
        rating REAL DEFAULT 4.5,
        reviews_count INTEGER DEFAULT 0,
        is_verified INTEGER DEFAULT 0,
        joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        title TEXT NOT NULL,
        category TEXT,
        brand TEXT,
        model TEXT,
        year INTEGER,
        condition TEXT,
        price REAL,
        negotiable INTEGER DEFAULT 1,
        description TEXT,
        frame_size TEXT,
        color TEXT,
        mileage INTEGER,
        location TEXT,
        service_history TEXT,
        images TEXT DEFAULT '[]',
        status TEXT DEFAULT 'active',
        views INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(seller_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        buyer_id INTEGER,
        seller_id INTEGER,
        amount REAL,
        message TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        listing_id INTEGER,
        content TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        buyer_id INTEGER,
        seller_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'completed',
        method TEXT,
        tx_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS service_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bike_info TEXT,
        package TEXT,
        mechanic_id INTEGER,
        scheduled_date TEXT,
        status TEXT DEFAULT 'pending',
        cost REAL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS mechanics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialization TEXT,
        experience INTEGER,
        rating REAL DEFAULT 4.7,
        available INTEGER DEFAULT 1,
        bio TEXT
    );
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        listing_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reviewer_id INTEGER,
        reviewed_id INTEGER,
        listing_id INTEGER,
        rating INTEGER,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    if c.execute('SELECT COUNT(*) FROM mechanics').fetchone()[0] == 0:
        c.executemany('INSERT INTO mechanics(name,specialization,experience,rating,bio) VALUES(?,?,?,?,?)', [
            ('Reza Tehrani', 'Road & Triathlon', 11, 4.9, 'Former pro mechanic for UCI road teams. Shimano Di2 certified.'),
            ('Yuki Okonkwo', 'Mountain & Enduro', 8, 4.8, 'SRAM certified. Suspension setup specialist. Raced EWS.'),
            ('Carmen Delgado', 'E-Bikes & Electronics', 6, 4.7, 'Bosch & Shimano EP8 master technician. Battery diagnostics expert.'),
            ('Donal Kerrigan', 'Vintage & Custom Builds', 18, 4.9, 'Frame builder and restorer. Steel is real advocate since 2006.'),
            ('Aiko Nasser', 'BMX & Urban', 5, 4.6, 'Park and street specialist. Custom wheel builds, brake conversions.'),
        ])

    if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        users = [
            ('chain_rex', 'rex@demo.com', generate_password_hash('demo123'), 'Rex Hartman', '555-0101', 'Austin, TX', 'Serious road cyclist and gear hoarder. 12 years in the saddle.', 4.9, 27, 1),
            ('velodrome_v', 'vera@demo.com', generate_password_hash('demo123'), 'Vera Stokes', '555-0102', 'Boulder, CO', 'Ex-semi-pro MTB racer. Selling the whole fleet to fund the next build.', 4.8, 19, 1),
            ('sprocket_joe', 'joe@demo.com', generate_password_hash('demo123'), 'Joe Matsuda', '555-0103', 'Portland, OR', 'Small shop owner. Quality used parts since 2016. Honest grading always.', 4.7, 34, 1),
        ]
        for u in users:
            try:
                c.execute('INSERT INTO users(username,email,password,full_name,phone,location,bio,rating,reviews_count,is_verified) VALUES(?,?,?,?,?,?,?,?,?,?)', u)
            except: pass

        u1 = c.execute('SELECT id FROM users WHERE username="chain_rex"').fetchone()
        u2 = c.execute('SELECT id FROM users WHERE username="velodrome_v"').fetchone()
        u3 = c.execute('SELECT id FROM users WHERE username="sprocket_joe"').fetchone()

        if u1 and u2 and u3:
            listings = [
                (u1['id'], 'Trek Domane SL 6 Disc', 'Road Bike', 'Trek', 'Domane SL 6', 2022, 'Excellent', 3200, 1, 'Full carbon frame. Shimano 105 Di2. 600 miles. Immaculate condition — stored indoors, never raced.', '56cm', 'Matte Charcoal', 600, 'Austin, TX', 'Professional service 2 months ago', '[]'),
                (u2['id'], 'Specialized Stumpjumper EVO Comp', 'Mountain Bike', 'Specialized', 'Stumpjumper EVO', 2021, 'Good', 2100, 1, '29er. SRAM GX Eagle 12-speed. Fox 36 fork. Some trail wear on chainstay but mechanically perfect.', 'Large', 'Forest Green', 1800, 'Boulder, CO', 'Fork service & brake bleed done recently', '[]'),
                (u3['id'], 'Cannondale SuperSix EVO Hi-MOD', 'Road Bike', 'Cannondale', 'SuperSix EVO', 2023, 'Like New', 5400, 0, 'Demo bike. 200 miles. Full Dura-Ace Di2. Carbon wheels included. Fastest production road bike available.', '54cm', 'Jet Black', 200, 'Portland, OR', 'Brand new — no service needed', '[]'),
                (u1['id'], 'Shimano Dura-Ace R9270 Groupset', 'Accessories', 'Shimano', 'Dura-Ace R9270', 2022, 'Excellent', 1800, 1, 'Complete Di2 12-speed groupset. Removed for frame upgrade. Includes derailleurs, shifters, chainring, cassette.', '—', '—', None, 'Austin, TX', '—', '[]'),
                (u2['id'], 'RockShox Lyrik Ultimate 29" 160mm', 'Accessories', 'RockShox', 'Lyrik Ultimate', 2022, 'Good', 480, 1, 'Charger 3 damper. New seals 3 months ago. 160mm travel, runs perfectly.', '—', 'Gold/Black', None, 'Boulder, CO', 'Full service 3 months ago', '[]'),
                (u3['id'], 'Giant Reign Advanced Pro 29 1', 'Mountain Bike', 'Giant', 'Reign Advanced Pro', 2023, 'Like New', 4100, 1, 'Near-new enduro machine. 150mm travel, SRAM X01 Eagle, FOX Factory suspension. Won\'t find better value.', 'Medium', 'Metallic Blue', 300, 'Portland, OR', 'Dealer serviced before listing', '[]'),
                (u1['id'], 'Wahoo ELEMNT BOLT V2', 'Accessories', 'Wahoo', 'ELEMNT BOLT V2', 2022, 'Excellent', 220, 1, 'Perfect navigation computer. All mounts included. Screen protector from day one.', '—', 'White', None, 'Austin, TX', '—', '[]'),
                (u2['id'], 'Yeti SB150 TURQ Carbon', 'Mountain Bike', 'Yeti', 'SB150 TURQ', 2021, 'Excellent', 4800, 0, 'Switch Infinity suspension. Fox Factory. SRAM X01 Eagle. Carbon enduro perfection.', 'Large', 'Turquoise', 900, 'Boulder, CO', 'Full Fox service completed', '[]'),
            ]
            for l in listings:
                c.execute('INSERT INTO listings(seller_id,title,category,brand,model,year,condition,price,negotiable,description,frame_size,color,mileage,location,service_history,images) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', l)

    c.commit()
    c.close()

@app.context_processor
def globals():
    unread = 0
    if session.get('uid'):
        c = db()
        unread = c.execute('SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0', (session['uid'],)).fetchone()[0]
        c.close()
    return dict(uid=session.get('uid'), uname=session.get('uname'), unread=unread)

# ── AUTH ─────────────────────────────────────────────
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

# ── PAGES ─────────────────────────────────────────────
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
    order = {'newest': 'l.created_at DESC', 'price_low': 'l.price ASC', 'price_high': 'l.price DESC', 'popular': 'l.views DESC'}.get(sort, 'l.created_at DESC')
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
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
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

# ── OFFERS ────────────────────────────────────────────
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

# ── MESSAGES ──────────────────────────────────────────
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
    d = request.json
    c = db()
    c.execute('INSERT INTO messages(sender_id,receiver_id,listing_id,content) VALUES(?,?,?,?)',
        (session['uid'], d['receiver_id'], d['listing_id'], d['content']))
    c.commit()
    m = c.execute('SELECT m.*,u.username FROM messages m JOIN users u ON m.sender_id=u.id WHERE m.sender_id=? ORDER BY m.created_at DESC LIMIT 1', (session['uid'],)).fetchone()
    c.close()
    return jsonify({'ok': True, 'msg': {'content': m['content'], 'created_at': m['created_at'], 'username': m['username']}})

# ── CHECKOUT ──────────────────────────────────────────
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

# ── SERVICE ────────────────────────────────────────────
@app.route('/service')
def service():
    c = db()
    mechs = c.execute('SELECT * FROM mechanics WHERE available=1').fetchall()
    c.close()
    packages = [
        {'id': 'tune', 'name': 'Quick Tune', 'price': 59, 'time': '2–3 hrs',
         'checklist': ['Safety check', 'Brake adjustment', 'Gear indexing', 'Tyre pressure', 'Chain lube']},
        {'id': 'standard', 'name': 'Full Service', 'price': 99, 'time': '4–5 hrs',
         'checklist': ['All in Quick Tune', 'Wheel truing', 'Cable replacement', 'BB check', 'Full clean', 'Bearing inspection']},
        {'id': 'overhaul', 'name': 'Premium Overhaul', 'price': 169, 'time': '6–8 hrs',
         'checklist': ['All in Full Service', 'Complete drivetrain strip', 'Headset service', 'Hub service', 'Hydraulic bleed', 'Written condition report']},
        {'id': 'ebike', 'name': 'E-Bike Specialist', 'price': 149, 'time': '5–6 hrs',
         'checklist': ['Battery health test', 'Motor diagnostic', 'Firmware update', 'Sensor calibration', 'Full Service items']},
    ]
    return render_template('service.html', mechs=mechs, packages=packages)

@app.route('/service/book', methods=['POST'])
def book_service():
    if not session.get('uid'):
        return jsonify({'error': 'Login required'}), 401
    d = request.json
    prices = {'tune': 59, 'standard': 99, 'overhaul': 169, 'ebike': 149}
    c = db()
    c.execute('INSERT INTO service_bookings(user_id,bike_info,package,mechanic_id,scheduled_date,cost,notes) VALUES(?,?,?,?,?,?,?)',
        (session['uid'], d['bike_info'], d['package'], d['mechanic_id'], d['date'], prices.get(d['package'], 99), d.get('notes', '')))
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

# ── DASHBOARD & PROFILE ────────────────────────────────
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
    d = request.json
    c = db()
    ex = c.execute('SELECT id FROM favorites WHERE user_id=? AND listing_id=?', (session['uid'], d['lid'])).fetchone()
    if ex:
        c.execute('DELETE FROM favorites WHERE user_id=? AND listing_id=?', (session['uid'], d['lid']))
        state = 'removed'
    else:
        c.execute('INSERT INTO favorites(user_id,listing_id) VALUES(?,?)', (session['uid'], d['lid']))
        state = 'added'
    c.commit()
    c.close()
    return jsonify({'ok': True, 'state': state})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
