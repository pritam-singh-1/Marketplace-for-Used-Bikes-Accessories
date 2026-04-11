from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, json, random, string, functools
from datetime import datetime
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# ── DATETIME FILTER ────────────────────────────────────
# MySQL returns datetime objects. This filter safely converts
# them to strings in ALL templates automatically.
@app.template_filter('dt')
def dt_filter(value, fmt='%Y-%m-%d'):
    if value is None:
        return '—'
    if isinstance(value, str):
        return value[:10] if fmt == '%Y-%m-%d' else value[:16]
    try:
        return value.strftime(fmt)
    except:
        return str(value)[:10]
app.secret_key = 'gearshift_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

MYSQL_CONFIG = {
    'host':     'localhost',
    'user':     'gearshift_user',
    'password': 'Gear@1234',
    'database': 'gearshift',
    'charset':  'utf8mb4',
}

def allowed(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED

def db():
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    conn.autocommit = False
    return conn

def get_cursor(conn):
    return conn.cursor(dictionary=True)

def fmt_dates(obj):
    """Recursively convert datetime objects to readable strings.
    Call this on any dict/list before passing to a template."""
    from datetime import datetime as dt_type, date as date_type
    if isinstance(obj, list):
        return [fmt_dates(item) for item in obj]
    if isinstance(obj, dict):
        return {k: fmt_dates(v) for k, v in obj.items()}
    if isinstance(obj, dt_type):
        return obj.strftime('%Y-%m-%d %H:%M')
    if isinstance(obj, date_type):
        return obj.strftime('%Y-%m-%d')
    return obj

# ── DECORATORS ────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('uid'):
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('uid'):
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

# ── INIT DB ───────────────────────────────────────────
def init_db():
    conn = db()
    cur  = get_cursor(conn)

    statements = [
        """CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            username      VARCHAR(80)  UNIQUE NOT NULL,
            email         VARCHAR(120) UNIQUE NOT NULL,
            password      VARCHAR(255) NOT NULL,
            full_name     VARCHAR(120),
            phone         VARCHAR(10),
            location      VARCHAR(120),
            bio           TEXT,
            avatar        VARCHAR(255),
            rating        FLOAT   DEFAULT 4.5,
            reviews_count INT     DEFAULT 0,
            is_verified   TINYINT DEFAULT 0,
            is_admin      TINYINT DEFAULT 0,
            is_banned     TINYINT DEFAULT 0,
            joined        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_phone CHECK (
            phone REGEXP '^[0-9]{10}$'
            )
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS listings (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            seller_id       INT,
            title           VARCHAR(255) NOT NULL,
            category        VARCHAR(80),
            brand           VARCHAR(80),
            model           VARCHAR(80),
            year            INT,
            `condition`     VARCHAR(40),
            price           FLOAT,
            negotiable      TINYINT DEFAULT 1,
            description     TEXT,
            frame_size      VARCHAR(20),
            color           VARCHAR(40),
            mileage         INT,
            location        VARCHAR(120),
            service_history TEXT,
            images          TEXT,
            status          VARCHAR(20) DEFAULT 'active',
            views           INT     DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS offers (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            listing_id  INT, buyer_id INT, seller_id INT,
            amount      FLOAT, message TEXT,
            status      VARCHAR(20) DEFAULT 'pending',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS messages (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            sender_id   INT, receiver_id INT, listing_id INT,
            content     TEXT, is_read TINYINT DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS orders (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            listing_id  INT, buyer_id INT, seller_id INT,
            amount      FLOAT, status VARCHAR(20) DEFAULT 'completed',
            method      VARCHAR(40), tx_id VARCHAR(20),
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS service_bookings (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            user_id        INT, bike_info TEXT, package VARCHAR(40),
            mechanic_id    INT, scheduled_date VARCHAR(20),
            status         VARCHAR(20) DEFAULT 'pending',
            cost           FLOAT, notes TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS mechanics (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            name           VARCHAR(120), specialization VARCHAR(120),
            experience     INT, rating FLOAT DEFAULT 4.7,
            available      TINYINT DEFAULT 1, bio TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS favorites (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT, listing_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS reviews (
            id INT AUTO_INCREMENT PRIMARY KEY,
            reviewer_id INT, reviewed_id INT, listing_id INT,
            rating INT, comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

        """CREATE TABLE IF NOT EXISTS admin_logs (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            admin_id    INT,
            action      VARCHAR(100),
            target_type VARCHAR(40),
            target_id   INT,
            detail      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]

    for stmt in statements:
        cur.execute(stmt)
    conn.commit()

    # Add missing columns if upgrading existing DB
    try:
        cur.execute("ALTER TABLE users ADD COLUMN is_admin TINYINT DEFAULT 0")
        conn.commit()
    except: pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN is_banned TINYINT DEFAULT 0")
        conn.commit()
    except: pass

    # Seed mechanics
    cur.execute("SELECT COUNT(*) AS cnt FROM mechanics")
    if cur.fetchone()['cnt'] == 0:
        cur.executemany(
            "INSERT INTO mechanics(name,specialization,experience,rating,bio) VALUES(%s,%s,%s,%s,%s)",
            [
                ('Reza Tehrani',   'Road & Triathlon',       11, 4.9, 'Former pro mechanic. Shimano Di2 certified.'),
                ('Yuki Okonkwo',   'Mountain & Enduro',       8, 4.8, 'SRAM certified. Suspension specialist.'),
                ('Carmen Delgado', 'E-Bikes & Electronics',   6, 4.7, 'Bosch & Shimano EP8 technician.'),
                ('Donal Kerrigan', 'Vintage & Custom Builds', 18, 4.9, 'Frame builder since 2006.'),
                ('Aiko Nasser',    'BMX & Urban',             5, 4.6, 'Park and street specialist.'),
            ]
        )
        conn.commit()

    # Seed users
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    if cur.fetchone()['cnt'] == 0:
        users = [
            # username, email, password, full_name, phone, location, bio, rating, reviews_count, is_verified, is_admin
            ('admin', 'admin@gearshift.com', generate_password_hash('Admin@1234'), 'Admin User', '9000000000', 'HQ',
             'Site administrator.', 5.0, 0, 1, 1),
            ('chain_rex', 'rex@demo.com', generate_password_hash('demo123'), 'Rex Hartman', '9000000101', 'Austin, TX',
             'Serious road cyclist. 12 years in the saddle.', 4.9, 27, 1, 0),
            ('velodrome_v', 'vera@demo.com', generate_password_hash('demo123'), 'Vera Stokes', '9000000102',
             'Boulder, CO', 'Ex-semi-pro MTB racer.', 4.8, 19, 1, 0),
            ('sprocket_joe', 'joe@demo.com', generate_password_hash('demo123'), 'Joe Matsuda', '9000000103',
             'Portland, OR', 'Small shop owner since 2016.', 4.7, 34, 1, 0),
        ]
        cur.executemany(
            """INSERT INTO users(username,email,password,full_name,phone,location,bio,
               rating,reviews_count,is_verified,is_admin) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            users
        )
        conn.commit()

        def get_uid(uname):
            cur.execute("SELECT id FROM users WHERE username=%s", (uname,))
            r = cur.fetchone()
            return r['id'] if r else None

        u1 = get_uid('chain_rex')
        u2 = get_uid('velodrome_v')
        u3 = get_uid('sprocket_joe')

        if u1 and u2 and u3:
            listings = [
                (u1,'Trek Domane SL 6 Disc','Road Bike','Trek','Domane SL 6',2022,'Excellent',3200,1,'Full carbon. Shimano 105 Di2. 600 miles.','56cm','Charcoal',600,'Austin, TX','Serviced 2 months ago','[]'),
                (u2,'Specialized Stumpjumper EVO','Mountain Bike','Specialized','Stumpjumper EVO',2021,'Good',2100,1,'29er. SRAM GX Eagle. Fox 36 fork.','Large','Forest Green',1800,'Boulder, CO','Fork service done','[]'),
                (u3,'Cannondale SuperSix EVO','Road Bike','Cannondale','SuperSix EVO',2023,'Like New',5400,0,'Demo bike. 200 miles. Full Dura-Ace Di2.','54cm','Jet Black',200,'Portland, OR','Brand new','[]'),
                (u1,'Shimano Dura-Ace R9270','Accessories','Shimano','Dura-Ace R9270',2022,'Excellent',1800,1,'Complete Di2 groupset.','—','—',None,'Austin, TX','—','[]'),
                (u2,'RockShox Lyrik Ultimate','Accessories','RockShox','Lyrik Ultimate',2022,'Good',480,1,'160mm travel, Charger 3.','—','Gold',None,'Boulder, CO','Full service 3 months ago','[]'),
                (u3,'Giant Reign Advanced Pro','Mountain Bike','Giant','Reign Advanced Pro',2023,'Like New',4100,1,'150mm, SRAM X01, FOX Factory.','Medium','Metallic Blue',300,'Portland, OR','Dealer serviced','[]'),
                (u1,'Wahoo ELEMNT BOLT V2','Accessories','Wahoo','ELEMNT BOLT V2',2022,'Excellent',220,1,'Perfect GPS computer. All mounts.','—','White',None,'Austin, TX','—','[]'),
                (u2,'Yeti SB150 TURQ Carbon','Mountain Bike','Yeti','SB150 TURQ',2021,'Excellent',4800,0,'Switch Infinity. Fox Factory. SRAM X01.','Large','Turquoise',900,'Boulder, CO','Full Fox service','[]'),
            ]
            cur.executemany(
                """INSERT INTO listings(seller_id,title,category,brand,model,year,`condition`,price,
                   negotiable,description,frame_size,color,mileage,location,service_history,images)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                listings
            )
            conn.commit()

    cur.close(); conn.close()

def admin_log(action, target_type='', target_id=None, detail=''):
    if not session.get('uid'):
        return
    try:
        conn = db(); cur = get_cursor(conn)
        cur.execute(
            "INSERT INTO admin_logs(admin_id,action,target_type,target_id,detail) VALUES(%s,%s,%s,%s,%s)",
            (session['uid'], action, target_type, target_id, detail)
        )
        conn.commit(); cur.close(); conn.close()
    except: pass

# ── CONTEXT PROCESSOR ────────────────────────────────
@app.context_processor
def inject_globals():
    unread = 0
    if session.get('uid'):
        conn = db(); cur = get_cursor(conn)
        cur.execute("SELECT COUNT(*) AS cnt FROM messages WHERE receiver_id=%s AND is_read=0", (session['uid'],))
        unread = cur.fetchone()['cnt']
        cur.close(); conn.close()
    return dict(uid=session.get('uid'), uname=session.get('uname'),
                is_admin=session.get('is_admin', 0), unread=unread)

# ── AUTH ──────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        d = request.form
        conn = db(); cur = get_cursor(conn)
        try:
            cur.execute(
                "INSERT INTO users(username,email,password,full_name,phone,location) VALUES(%s,%s,%s,%s,%s,%s)",
                (d['username'], d['email'], generate_password_hash(d['password']),
                 d['full_name'], d.get('phone',''), d.get('location',''))
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE username=%s", (d['username'],))
            u = cur.fetchone()
            session['uid']      = u['id']
            session['uname']    = u['username']
            session['is_admin'] = u['is_admin']
            flash('Welcome to GearShift!', 'success')
            return redirect(url_for('index'))
        except Error:
            conn.rollback()
            flash('Username or email already taken.', 'error')
        finally:
            cur.close(); conn.close()
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = db(); cur = get_cursor(conn)
        cur.execute("SELECT * FROM users WHERE email=%s OR username=%s",
                    (request.form['login'], request.form['login']))
        u = cur.fetchone()
        cur.close(); conn.close()
        if u and check_password_hash(u['password'], request.form['password']):
            if u.get('is_banned'):
                flash('Your account has been banned. Contact support.', 'error')
                return redirect(url_for('login'))
            session['uid']      = u['id']
            session['uname']    = u['username']
            session['is_admin'] = u['is_admin']
            flash(f'Welcome back, {u["full_name"] or u["username"]}!', 'success')
            if u['is_admin']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'error')
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── PUBLIC PAGES ──────────────────────────────────────
@app.route('/')
def index():
    conn = db(); cur = get_cursor(conn)
    cur.execute("""SELECT l.*,u.username,u.rating AS sr,u.is_verified
        FROM listings l JOIN users u ON l.seller_id=u.id
        WHERE l.status='active' ORDER BY l.created_at DESC LIMIT 8""")
    featured = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS cnt FROM listings WHERE status='active'")
    stats = {'listings': cur.fetchone()['cnt']}
    cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE is_admin=0")
    stats['users'] = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) AS cnt FROM orders")
    stats['sold'] = cur.fetchone()['cnt']
    cur.close(); conn.close()
    return render_template('index.html', featured=fmt_dates(featured), stats=stats)

@app.route('/browse')
def browse():
    conn = db(); cur = get_cursor(conn)
    q = request.args.get('q',''); cat = request.args.get('category','')
    cond = request.args.get('condition',''); sort = request.args.get('sort','newest')
    minp = request.args.get('min_price',0); maxp = request.args.get('max_price',999999)
    sql = """SELECT l.*,u.username,u.rating AS sr,u.is_verified
        FROM listings l JOIN users u ON l.seller_id=u.id WHERE l.status='active'"""
    params = []
    if q: sql += " AND (l.title LIKE %s OR l.brand LIKE %s OR l.description LIKE %s)"; params += [f'%{q}%']*3
    if cat: sql += " AND l.category=%s"; params.append(cat)
    if cond: sql += " AND l.`condition`=%s"; params.append(cond)
    sql += " AND l.price BETWEEN %s AND %s"; params += [minp, maxp]
    order = {'newest':'l.created_at DESC','price_low':'l.price ASC','price_high':'l.price DESC','popular':'l.views DESC'}.get(sort,'l.created_at DESC')
    sql += f' ORDER BY {order}'
    cur.execute(sql, params); listings = cur.fetchall()
    cur.close(); conn.close()
    return render_template('browse.html', listings=fmt_dates(listings), q=q, category=cat, condition=cond, sort=sort)

@app.route('/listing/<int:lid>')
def listing(lid):
    conn = db(); cur = get_cursor(conn)
    cur.execute("UPDATE listings SET views=views+1 WHERE id=%s", (lid,)); conn.commit()
    cur.execute("""SELECT l.*,u.username,u.full_name,u.rating AS sr,u.is_verified,
        u.reviews_count,u.location AS sloc,u.joined
        FROM listings l JOIN users u ON l.seller_id=u.id WHERE l.id=%s""", (lid,))
    item = cur.fetchone()
    if not item: cur.close(); conn.close(); return redirect(url_for('browse'))
    cur.execute("SELECT * FROM listings WHERE seller_id=%s AND id!=%s AND status='active' LIMIT 3", (item['seller_id'], lid))
    others = cur.fetchall()
    fav = False
    if session.get('uid'):
        cur.execute("SELECT id FROM favorites WHERE user_id=%s AND listing_id=%s", (session['uid'], lid))
        fav = bool(cur.fetchone())
    cur.close(); conn.close()
    return render_template('listing.html', item=fmt_dates(item), others=fmt_dates(others), fav=fav)

@app.route('/listing/new', methods=['GET', 'POST'])
@login_required
def new_listing():
    if request.method == 'POST':
        d = request.form; imgs = []
        for f in request.files.getlist('images'):
            if f and allowed(f.filename):
                fn = f'{int(datetime.now().timestamp())}_{secure_filename(f.filename)}'
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn)); imgs.append(fn)
        conn = db(); cur = get_cursor(conn)
        cur.execute("""INSERT INTO listings(seller_id,title,category,brand,model,year,`condition`,
            price,negotiable,description,frame_size,color,mileage,location,service_history,images)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (session['uid'],d['title'],d['category'],d['brand'],d['model'],d.get('year'),
             d['condition'],d['price'],int(d.get('negotiable',0)),d['description'],
             d.get('frame_size'),d.get('color'),d.get('mileage'),d['location'],
             d.get('service_history',''),json.dumps(imgs)))
        conn.commit(); lid = cur.lastrowid; cur.close(); conn.close()
        flash('Listing published!', 'success'); return redirect(url_for('listing', lid=lid))
    return render_template('new_listing.html', listing=None)

@app.route('/listing/<int:lid>/edit', methods=['GET', 'POST'])
@login_required
def edit_listing(lid):
    conn = db(); cur = get_cursor(conn)
    # Admin can edit any listing
    if session.get('is_admin'):
        cur.execute("SELECT * FROM listings WHERE id=%s", (lid,))
    else:
        cur.execute("SELECT * FROM listings WHERE id=%s AND seller_id=%s", (lid, session['uid']))
    item = cur.fetchone()
    if not item: cur.close(); conn.close(); flash('Not found.', 'error'); return redirect(url_for('dashboard'))
    if request.method == 'POST':
        d = request.form
        cur.execute("""UPDATE listings SET title=%s,category=%s,brand=%s,model=%s,year=%s,
            `condition`=%s,price=%s,negotiable=%s,description=%s,frame_size=%s,color=%s,
            mileage=%s,location=%s,service_history=%s WHERE id=%s""",
            (d['title'],d['category'],d['brand'],d['model'],d.get('year'),d['condition'],
             d['price'],int(d.get('negotiable',0)),d['description'],d.get('frame_size'),
             d.get('color'),d.get('mileage'),d['location'],d.get('service_history',''),lid))
        conn.commit(); cur.close(); conn.close()
        if session.get('is_admin'): admin_log('edit_listing','listing',lid,f'Edited listing #{lid}')
        flash('Listing updated!', 'success'); return redirect(url_for('listing', lid=lid))
    cur.close(); conn.close()
    return render_template('new_listing.html', listing=item)

@app.route('/listing/<int:lid>/delete', methods=['POST'])
@login_required
def delete_listing(lid):
    conn = db(); cur = get_cursor(conn)
    if session.get('is_admin'):
        cur.execute("UPDATE listings SET status='deleted' WHERE id=%s", (lid,))
        admin_log('delete_listing', 'listing', lid, f'Admin deleted listing #{lid}')
    else:
        cur.execute("UPDATE listings SET status='deleted' WHERE id=%s AND seller_id=%s", (lid, session['uid']))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ── OFFERS ────────────────────────────────────────────
@app.route('/offer/make', methods=['POST'])
@login_required
def make_offer():
    d = request.json; conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM listings WHERE id=%s", (d['listing_id'],))
    item = cur.fetchone()
    if not item: cur.close(); conn.close(); return jsonify({'error': 'Not found'}), 404
    if item['seller_id'] == session['uid']: cur.close(); conn.close(); return jsonify({'error': 'Cannot offer on own listing'}), 400
    cur.execute("INSERT INTO offers(listing_id,buyer_id,seller_id,amount,message) VALUES(%s,%s,%s,%s,%s)",
                (d['listing_id'],session['uid'],item['seller_id'],d['amount'],d.get('message','')))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'msg': 'Offer sent!'})

@app.route('/offer/<int:oid>/respond', methods=['POST'])
@login_required
def respond_offer(oid):
    conn = db(); cur = get_cursor(conn)
    cur.execute("UPDATE offers SET status=%s WHERE id=%s AND seller_id=%s", (request.json['status'], oid, session['uid']))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ── MESSAGES ──────────────────────────────────────────
@app.route('/messages')
@login_required
def messages():
    conn = db(); cur = get_cursor(conn)
    cur.execute("""SELECT IF(m.sender_id=%s,m.receiver_id,m.sender_id) AS oid,
        m.listing_id, MAX(m.created_at) AS lt
        FROM messages m WHERE m.sender_id=%s OR m.receiver_id=%s
        GROUP BY IF(m.sender_id=%s,m.receiver_id,m.sender_id), m.listing_id ORDER BY lt DESC""",
        (session['uid'],)*4)
    convos = cur.fetchall(); result = []
    for cv in convos:
        cur.execute("SELECT id,username,full_name FROM users WHERE id=%s", (cv['oid'],)); other = cur.fetchone()
        cur.execute("SELECT id,title FROM listings WHERE id=%s", (cv['listing_id'],)); lst = cur.fetchone()
        cur.execute("""SELECT * FROM messages WHERE
            ((sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s))
            AND listing_id=%s ORDER BY created_at DESC LIMIT 1""",
            (session['uid'],cv['oid'],cv['oid'],session['uid'],cv['listing_id'])); last = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS cnt FROM messages WHERE sender_id=%s AND receiver_id=%s AND listing_id=%s AND is_read=0",
            (cv['oid'],session['uid'],cv['listing_id'])); unread = cur.fetchone()['cnt']
        if other and lst and last: result.append({'other':other,'listing':lst,'last':last,'unread':unread})
    cur.close(); conn.close()
    return render_template('messages.html', convos=fmt_dates(result))

@app.route('/chat/<int:oid>/<int:lid>')
@login_required
def chat(oid, lid):
    conn = db(); cur = get_cursor(conn)
    cur.execute("UPDATE messages SET is_read=1 WHERE sender_id=%s AND receiver_id=%s AND listing_id=%s", (oid,session['uid'],lid)); conn.commit()
    cur.execute("""SELECT m.*,u.username FROM messages m JOIN users u ON m.sender_id=u.id
        WHERE ((sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s)) AND listing_id=%s ORDER BY created_at""",
        (session['uid'],oid,oid,session['uid'],lid)); msgs = cur.fetchall()
    cur.execute("SELECT * FROM users WHERE id=%s", (oid,)); other = cur.fetchone()
    cur.execute("SELECT * FROM listings WHERE id=%s", (lid,)); lst = cur.fetchone()
    cur.close(); conn.close()
    return render_template('chat.html', msgs=fmt_dates(msgs), other=fmt_dates(other), lst=fmt_dates(lst), lid=lid)

@app.route('/messages/send', methods=['POST'])
@login_required
def send_msg():
    d = request.json; conn = db(); cur = get_cursor(conn)
    cur.execute("INSERT INTO messages(sender_id,receiver_id,listing_id,content) VALUES(%s,%s,%s,%s)",
                (session['uid'],d['receiver_id'],d['listing_id'],d['content'])); conn.commit()
    cur.execute("""SELECT m.*,u.username FROM messages m JOIN users u ON m.sender_id=u.id
        WHERE m.sender_id=%s ORDER BY m.created_at DESC LIMIT 1""", (session['uid'],)); m = cur.fetchone()
    cur.close(); conn.close()
    return jsonify({'ok':True,'msg':{'content':m['content'],'created_at':m['created_at'].strftime('%Y-%m-%d %H:%M'),'username':m['username']}})

# ── CHECKOUT ──────────────────────────────────────────
@app.route('/checkout/<int:lid>')
@login_required
def checkout(lid):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT l.*,u.username,u.full_name FROM listings l JOIN users u ON l.seller_id=u.id WHERE l.id=%s", (lid,))
    item = cur.fetchone(); cur.close(); conn.close()
    return render_template('checkout.html', item=fmt_dates(item))

@app.route('/payment/process', methods=['POST'])
@login_required
def process_payment():
    d = request.json; tx = 'GS'+''.join(random.choices(string.ascii_uppercase+string.digits, k=10))
    conn = db(); cur = get_cursor(conn)
    cur.execute("INSERT INTO orders(listing_id,buyer_id,seller_id,amount,method,tx_id) VALUES(%s,%s,%s,%s,%s,%s)",
                (d['listing_id'],session['uid'],d['seller_id'],d['amount'],d['method'],tx))
    cur.execute("UPDATE listings SET status='sold' WHERE id=%s", (d['listing_id'],))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'tx':tx})

# ── SERVICE ───────────────────────────────────────────
@app.route('/service')
def service():
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM mechanics WHERE available=1"); mechs = cur.fetchall()
    cur.close(); conn.close()
    packages = [
        {'id':'tune',    'name':'Quick Tune',      'price':59,  'time':'2–3 hrs','checklist':['Safety check','Brake adjustment','Gear indexing','Tyre pressure','Chain lube']},
        {'id':'standard','name':'Full Service',     'price':99,  'time':'4–5 hrs','checklist':['All in Quick Tune','Wheel truing','Cable replacement','BB check','Full clean']},
        {'id':'overhaul','name':'Premium Overhaul', 'price':169, 'time':'6–8 hrs','checklist':['All in Full Service','Drivetrain strip','Headset service','Hydraulic bleed','Report']},
        {'id':'ebike',   'name':'E-Bike Specialist','price':149, 'time':'5–6 hrs','checklist':['Battery test','Motor diagnostic','Firmware update','Sensor calibration']},
    ]
    return render_template('service.html', mechs=fmt_dates(mechs), packages=packages)

@app.route('/service/book', methods=['POST'])
@login_required
def book_service():
    d = request.json; prices = {'tune':59,'standard':99,'overhaul':169,'ebike':149}
    conn = db(); cur = get_cursor(conn)
    cur.execute("INSERT INTO service_bookings(user_id,bike_info,package,mechanic_id,scheduled_date,cost,notes) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (session['uid'],d['bike_info'],d['package'],d['mechanic_id'],d['date'],prices.get(d['package'],99),d.get('notes','')))
    conn.commit(); bid = cur.lastrowid; cur.close(); conn.close()
    return jsonify({'ok':True,'bid':bid,'ref':f'GS-SVC-{bid:04d}'})

@app.route('/service/status/<int:bid>')
def svc_status(bid):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM service_bookings WHERE id=%s", (bid,)); b = cur.fetchone()
    cur.close(); conn.close()
    if not b: return jsonify({'error':'Not found'}), 404
    steps = ['pending','confirmed','in_progress','quality_check','complete']
    idx = steps.index(b['status']) if b['status'] in steps else 0
    return jsonify({'status':b['status'],'step':idx+1,'total':len(steps)})

@app.route('/service/bookings')
@login_required
def my_bookings():
    conn = db(); cur = get_cursor(conn)
    cur.execute("""SELECT sb.*,m.name AS mname FROM service_bookings sb
        LEFT JOIN mechanics m ON sb.mechanic_id=m.id WHERE sb.user_id=%s ORDER BY sb.created_at DESC""", (session['uid'],))
    bkgs = cur.fetchall(); cur.close(); conn.close()
    return render_template('bookings.html', bookings=fmt_dates(bkgs))

# ── DASHBOARD ─────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    conn = db(); cur = get_cursor(conn); uid = session['uid']
    cur.execute("SELECT * FROM users WHERE id=%s", (uid,)); u = cur.fetchone()
    cur.execute("SELECT * FROM listings WHERE seller_id=%s AND status!='deleted' ORDER BY created_at DESC", (uid,)); my_listings = cur.fetchall()
    cur.execute("""SELECT o.*,u.username AS bname,l.title AS ltitle,l.price AS lprice
        FROM offers o JOIN users u ON o.buyer_id=u.id JOIN listings l ON o.listing_id=l.id
        WHERE o.seller_id=%s AND o.status='pending' ORDER BY o.created_at DESC""", (uid,)); offers_in = cur.fetchall()
    cur.execute("""SELECT o.*,l.title AS ltitle,u.username AS sname
        FROM offers o JOIN listings l ON o.listing_id=l.id JOIN users u ON o.seller_id=u.id
        WHERE o.buyer_id=%s ORDER BY o.created_at DESC LIMIT 5""", (uid,)); offers_out = cur.fetchall()
    cur.execute("""SELECT ord.*,l.title FROM orders ord JOIN listings l ON ord.listing_id=l.id
        WHERE ord.buyer_id=%s ORDER BY ord.created_at DESC LIMIT 5""", (uid,)); purchases = cur.fetchall()
    cur.execute("""SELECT sb.*,m.name AS mname FROM service_bookings sb
        LEFT JOIN mechanics m ON sb.mechanic_id=m.id WHERE sb.user_id=%s ORDER BY sb.created_at DESC LIMIT 5""", (uid,)); bookings = cur.fetchall()
    cur.execute("""SELECT l.*,u.username FROM favorites f JOIN listings l ON f.listing_id=l.id
        JOIN users u ON l.seller_id=u.id WHERE f.user_id=%s AND l.status='active'""", (uid,)); favs = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS cnt FROM messages WHERE receiver_id=%s AND is_read=0", (uid,)); unread = cur.fetchone()['cnt']
    cur.close(); conn.close()
    return render_template('dashboard.html',
        u=fmt_dates(u),
        my_listings=fmt_dates(my_listings),
        offers_in=fmt_dates(offers_in),
        offers_out=fmt_dates(offers_out),
        purchases=fmt_dates(purchases),
        bookings=fmt_dates(bookings),
        favs=fmt_dates(favs),
        unread=unread)

@app.route('/profile/<username>')
def profile(username):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,)); u = cur.fetchone()
    if not u: cur.close(); conn.close(); return redirect(url_for('index'))
    cur.execute("SELECT * FROM listings WHERE seller_id=%s AND status='active' ORDER BY created_at DESC", (u['id'],)); listings = cur.fetchall()
    cur.execute("""SELECT r.*,u.username FROM reviews r JOIN users u ON r.reviewer_id=u.id
        WHERE r.reviewed_id=%s ORDER BY r.created_at DESC LIMIT 8""", (u['id'],)); reviews = cur.fetchall()
    cur.close(); conn.close()
    return render_template('profile.html', u=fmt_dates(u), listings=fmt_dates(listings), reviews=fmt_dates(reviews))

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM users WHERE id=%s", (session['uid'],)); u = cur.fetchone()
    if request.method == 'POST':
        d = request.form
        cur.execute("UPDATE users SET full_name=%s,phone=%s,location=%s,bio=%s WHERE id=%s",
                    (d['full_name'],d['phone'],d['location'],d['bio'],session['uid']))
        conn.commit(); cur.close(); conn.close()
        flash('Profile updated!', 'success'); return redirect(url_for('dashboard'))
    cur.close(); conn.close()
    return render_template('edit_profile.html', u=fmt_dates(u))

@app.route('/fav/toggle', methods=['POST'])
@login_required
def fav_toggle():
    d = request.json; conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT id FROM favorites WHERE user_id=%s AND listing_id=%s", (session['uid'],d['lid']))
    if cur.fetchone():
        cur.execute("DELETE FROM favorites WHERE user_id=%s AND listing_id=%s", (session['uid'],d['lid'])); state='removed'
    else:
        cur.execute("INSERT INTO favorites(user_id,listing_id) VALUES(%s,%s)", (session['uid'],d['lid'])); state='added'
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'state':state})

# ════════════════════════════════════════════════════
#  ADMIN PANEL — ALL ROUTES
# ════════════════════════════════════════════════════

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE is_admin=0"); stats = {'users': cur.fetchone()['cnt']}
    cur.execute("SELECT COUNT(*) AS cnt FROM listings WHERE status='active'"); stats['listings'] = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) AS cnt FROM listings WHERE status='sold'"); stats['sold'] = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) AS cnt FROM orders"); stats['orders'] = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) AS cnt FROM service_bookings"); stats['bookings'] = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE is_banned=1"); stats['banned'] = cur.fetchone()['cnt']
    cur.execute("SELECT COALESCE(SUM(amount),0) AS total FROM orders"); stats['revenue'] = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS cnt FROM messages WHERE is_read=0"); stats['unread_msgs'] = cur.fetchone()['cnt']
    # Recent activity
    cur.execute("""SELECT u.username,u.email,u.joined,u.is_verified,u.is_banned
        FROM users u WHERE u.is_admin=0 ORDER BY u.joined DESC LIMIT 6"""); recent_users = cur.fetchall()
    cur.execute("""SELECT l.title,l.price,l.status,l.created_at,u.username
        FROM listings l JOIN users u ON l.seller_id=u.id ORDER BY l.created_at DESC LIMIT 6"""); recent_listings = cur.fetchall()
    cur.execute("""SELECT al.*,u.username AS aname FROM admin_logs al
        JOIN users u ON al.admin_id=u.id ORDER BY al.created_at DESC LIMIT 8"""); logs = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin/dashboard.html', stats=stats,
        recent_users=fmt_dates(recent_users), recent_listings=fmt_dates(recent_listings), logs=fmt_dates(logs))

# ── ADMIN: USERS ──────────────────────────────────────
@app.route('/admin/users')
@admin_required
def admin_users():
    conn = db(); cur = get_cursor(conn)
    search = request.args.get('q','')
    sql = "SELECT * FROM users WHERE is_admin=0"
    params = []
    if search:
        sql += " AND (username LIKE %s OR email LIKE %s OR full_name LIKE %s)"
        params += [f'%{search}%']*3
    sql += " ORDER BY joined DESC"
    cur.execute(sql, params); users = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin/users.html', users=fmt_dates(users), search=search)

@app.route('/admin/user/<int:uid_target>')
@admin_required
def admin_user_detail(uid_target):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM users WHERE id=%s", (uid_target,)); u = cur.fetchone()
    if not u: cur.close(); conn.close(); flash('User not found.','error'); return redirect(url_for('admin_users'))
    cur.execute("SELECT * FROM listings WHERE seller_id=%s ORDER BY created_at DESC", (uid_target,)); listings = cur.fetchall()
    cur.execute("""SELECT o.*,l.title AS ltitle FROM orders o JOIN listings l ON o.listing_id=l.id
        WHERE o.buyer_id=%s OR o.seller_id=%s ORDER BY o.created_at DESC LIMIT 10""", (uid_target,uid_target)); orders = cur.fetchall()
    cur.execute("""SELECT sb.*,m.name AS mname FROM service_bookings sb LEFT JOIN mechanics m ON sb.mechanic_id=m.id
        WHERE sb.user_id=%s ORDER BY sb.created_at DESC""", (uid_target,)); bookings = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin/user_detail.html', u=fmt_dates(u), listings=fmt_dates(listings), orders=fmt_dates(orders), bookings=fmt_dates(bookings))

@app.route('/admin/user/<int:uid_target>/ban', methods=['POST'])
@admin_required
def admin_ban_user(uid_target):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT is_banned,username FROM users WHERE id=%s", (uid_target,)); u = cur.fetchone()
    new_status = 0 if u['is_banned'] else 1
    cur.execute("UPDATE users SET is_banned=%s WHERE id=%s", (new_status, uid_target))
    conn.commit(); cur.close(); conn.close()
    action = 'ban_user' if new_status else 'unban_user'
    admin_log(action, 'user', uid_target, f'{"Banned" if new_status else "Unbanned"} user {u["username"]}')
    return jsonify({'ok':True,'banned':bool(new_status),'msg':f'User {"banned" if new_status else "unbanned"}'})

@app.route('/admin/user/<int:uid_target>/verify', methods=['POST'])
@admin_required
def admin_verify_user(uid_target):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT is_verified,username FROM users WHERE id=%s", (uid_target,)); u = cur.fetchone()
    new_status = 0 if u['is_verified'] else 1
    cur.execute("UPDATE users SET is_verified=%s WHERE id=%s", (new_status, uid_target))
    conn.commit(); cur.close(); conn.close()
    admin_log('verify_user', 'user', uid_target, f'{"Verified" if new_status else "Unverified"} user {u["username"]}')
    return jsonify({'ok':True,'verified':bool(new_status)})

@app.route('/admin/user/<int:uid_target>/delete', methods=['POST'])
@admin_required
def admin_delete_user(uid_target):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT username FROM users WHERE id=%s", (uid_target,)); u = cur.fetchone()
    cur.execute("UPDATE listings SET status='deleted' WHERE seller_id=%s", (uid_target,))
    cur.execute("DELETE FROM users WHERE id=%s AND is_admin=0", (uid_target,))
    conn.commit(); cur.close(); conn.close()
    admin_log('delete_user', 'user', uid_target, f'Deleted user {u["username"] if u else uid_target}')
    return jsonify({'ok':True})

@app.route('/admin/user/<int:uid_target>/edit', methods=['GET','POST'])
@admin_required
def admin_edit_user(uid_target):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM users WHERE id=%s", (uid_target,)); u = cur.fetchone()
    if request.method == 'POST':
        d = request.form
        cur.execute("""UPDATE users SET full_name=%s,email=%s,phone=%s,location=%s,
            bio=%s,rating=%s,is_verified=%s WHERE id=%s""",
            (d['full_name'],d['email'],d['phone'],d['location'],
             d['bio'],d['rating'],int(d.get('is_verified',0)),uid_target))
        conn.commit(); cur.close(); conn.close()
        admin_log('edit_user','user',uid_target,f'Edited user #{uid_target}')
        flash('User updated!','success'); return redirect(url_for('admin_user_detail', uid_target=uid_target))
    cur.close(); conn.close()
    return render_template('admin/edit_user.html', u=fmt_dates(u))

# ── ADMIN: LISTINGS ───────────────────────────────────
@app.route('/admin/listings')
@admin_required
def admin_listings():
    conn = db(); cur = get_cursor(conn)
    search = request.args.get('q',''); status = request.args.get('status','')
    sql = "SELECT l.*,u.username FROM listings l JOIN users u ON l.seller_id=u.id WHERE 1=1"
    params = []
    if search: sql += " AND (l.title LIKE %s OR l.brand LIKE %s)"; params += [f'%{search}%']*2
    if status: sql += " AND l.status=%s"; params.append(status)
    sql += " ORDER BY l.created_at DESC"
    cur.execute(sql, params); listings = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin/listings.html', listings=fmt_dates(listings), search=search, status=status)

@app.route('/admin/listing/<int:lid>/status', methods=['POST'])
@admin_required
def admin_listing_status(lid):
    new_status = request.json.get('status')
    if new_status not in ['active','sold','deleted','suspended']:
        return jsonify({'error':'Invalid status'}), 400
    conn = db(); cur = get_cursor(conn)
    cur.execute("UPDATE listings SET status=%s WHERE id=%s", (new_status, lid))
    conn.commit(); cur.close(); conn.close()
    admin_log('change_listing_status','listing',lid,f'Set listing #{lid} to {new_status}')
    return jsonify({'ok':True})

# ── ADMIN: ORDERS ─────────────────────────────────────
@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = db(); cur = get_cursor(conn)
    cur.execute("""SELECT o.*,l.title AS ltitle,
        ub.username AS buyer_name, us.username AS seller_name
        FROM orders o JOIN listings l ON o.listing_id=l.id
        JOIN users ub ON o.buyer_id=ub.id JOIN users us ON o.seller_id=us.id
        ORDER BY o.created_at DESC""")
    orders = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin/orders.html', orders=fmt_dates(orders))

# ── ADMIN: SERVICE BOOKINGS ───────────────────────────
@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    conn = db(); cur = get_cursor(conn)
    cur.execute("""SELECT sb.*,u.username,m.name AS mname
        FROM service_bookings sb JOIN users u ON sb.user_id=u.id
        LEFT JOIN mechanics m ON sb.mechanic_id=m.id
        ORDER BY sb.created_at DESC""")
    bookings = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin/bookings.html', bookings=fmt_dates(bookings))

@app.route('/admin/booking/<int:bid>/status', methods=['POST'])
@admin_required
def admin_booking_status(bid):
    new_status = request.json.get('status')
    if new_status not in ['pending','confirmed','in_progress','quality_check','complete']:
        return jsonify({'error':'Invalid status'}), 400
    conn = db(); cur = get_cursor(conn)
    cur.execute("UPDATE service_bookings SET status=%s WHERE id=%s", (new_status, bid))
    conn.commit(); cur.close(); conn.close()
    admin_log('update_booking_status','booking',bid,f'Set booking #{bid} to {new_status}')
    return jsonify({'ok':True})

# ── ADMIN: MECHANICS ──────────────────────────────────
@app.route('/admin/mechanics')
@admin_required
def admin_mechanics():
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT * FROM mechanics ORDER BY name"); mechs = cur.fetchall()
    cur.close(); conn.close()
    return render_template('admin/mechanics.html', mechs=fmt_dates(mechs))

@app.route('/admin/mechanic/add', methods=['POST'])
@admin_required
def admin_add_mechanic():
    d = request.form; conn = db(); cur = get_cursor(conn)
    cur.execute("INSERT INTO mechanics(name,specialization,experience,rating,bio) VALUES(%s,%s,%s,%s,%s)",
                (d['name'],d['specialization'],d.get('experience',0),d.get('rating',4.5),d.get('bio','')))
    conn.commit(); mid = cur.lastrowid; cur.close(); conn.close()
    admin_log('add_mechanic','mechanic',mid,f'Added mechanic {d["name"]}')
    flash(f'Mechanic {d["name"]} added!','success'); return redirect(url_for('admin_mechanics'))

@app.route('/admin/mechanic/<int:mid>/toggle', methods=['POST'])
@admin_required
def admin_mechanic_toggle(mid):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT available,name FROM mechanics WHERE id=%s", (mid,)); m = cur.fetchone()
    cur.execute("UPDATE mechanics SET available=%s WHERE id=%s", (0 if m['available'] else 1, mid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'available': not m['available']})

@app.route('/admin/mechanic/<int:mid>/delete', methods=['POST'])
@admin_required
def admin_mechanic_delete(mid):
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT name FROM mechanics WHERE id=%s", (mid,)); m = cur.fetchone()
    cur.execute("DELETE FROM mechanics WHERE id=%s", (mid,))
    conn.commit(); cur.close(); conn.close()
    admin_log('delete_mechanic','mechanic',mid,f'Deleted mechanic {m["name"] if m else mid}')
    return jsonify({'ok':True})

# ── ADMIN: LOGS ───────────────────────────────────────
@app.route('/admin/logs')
@admin_required
def admin_logs():
    conn = db(); cur = get_cursor(conn)
    cur.execute("""SELECT al.*,u.username AS aname FROM admin_logs al
        JOIN users u ON al.admin_id=u.id ORDER BY al.created_at DESC LIMIT 200""")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template('admin/logs.html', logs=fmt_dates(logs))

# ── ADMIN: STATS API ──────────────────────────────────
@app.route('/admin/stats/api')
@admin_required
def admin_stats_api():
    conn = db(); cur = get_cursor(conn)
    cur.execute("SELECT DATE(created_at) AS d, COUNT(*) AS cnt FROM users WHERE is_admin=0 GROUP BY DATE(created_at) ORDER BY d DESC LIMIT 7")
    users_chart = cur.fetchall()
    cur.execute("SELECT DATE(created_at) AS d, COUNT(*) AS cnt FROM orders GROUP BY DATE(created_at) ORDER BY d DESC LIMIT 7")
    orders_chart = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({'users': [{'d':str(r['d']),'cnt':r['cnt']} for r in users_chart],
                   'orders':[{'d':str(r['d']),'cnt':r['cnt']} for r in orders_chart]})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)