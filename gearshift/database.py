import sqlite3

from werkzeug.security import generate_password_hash


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
            except sqlite3.IntegrityError:
                pass

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
