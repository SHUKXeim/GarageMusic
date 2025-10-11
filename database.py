# database.py
import sqlite3

class Database:
    def __init__(self, path="database.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self._create_tables()
        self._ensure_columns()

    def _create_tables(self):
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                name TEXT
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                artist_id INTEGER,
                title TEXT,
                performer TEXT,
                file_id TEXT,
                storage_message_id INTEGER,
                is_common INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS bot_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS sent_updates (
                version TEXT PRIMARY KEY
            )
        ''')

        self.conn.commit()


    def _ensure_columns(self):
        try:
            self.cur.execute("PRAGMA table_info(tracks)")
            cols = [r[1] for r in self.cur.fetchall()]
            if "artist_id" not in cols:
                try:
                    self.cur.execute("ALTER TABLE tracks ADD COLUMN artist_id INTEGER")
                except Exception:
                    pass
            if "storage_message_id" not in cols:
                try:
                    self.cur.execute("ALTER TABLE tracks ADD COLUMN storage_message_id INTEGER")
                except Exception:
                    pass
            self.conn.commit()
        except Exception:
            pass

    # users
    def add_user(self, telegram_id, name):
        self.cur.execute("INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)", (telegram_id, name))
        self.conn.commit()

    def get_user(self, telegram_id):
        self.cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return self.cur.fetchone()

    def get_all_users(self):
        self.cur.execute("SELECT telegram_id FROM users")
        rows = [row[0] for row in self.cur.fetchall()]
        # приводим к int и фильтруем None
        clean = []
        for r in rows:
            try:
                clean.append(int(r))
            except Exception:
                continue
        return clean


    # artists
    def add_artist(self, user_id, name):
        self.cur.execute("INSERT INTO artists (user_id, name) VALUES (?, ?)", (user_id, name))
        self.conn.commit()
        return self.cur.lastrowid

    def get_all_artists(self):
        self.cur.execute("SELECT id, user_id, name FROM artists ORDER BY name ASC")
        return self.cur.fetchall()

    def get_artist(self, artist_id):
        self.cur.execute("SELECT id, user_id, name FROM artists WHERE id = ?", (artist_id,))
        return self.cur.fetchone()

    def get_user_artists(self, user_id):
        self.cur.execute("SELECT id, name FROM artists WHERE user_id = ?", (user_id,))
        return self.cur.fetchall()

    def delete_artist(self, artist_id, user_id):
        self.cur.execute("DELETE FROM artists WHERE id = ? AND user_id = ?", (artist_id, user_id))
        self.conn.commit()

    def get_or_create_first_artist(self, user_id, username_fallback):
        artists = self.get_user_artists(user_id)
        if artists:
            return artists[0][0], artists[0][1]
        name = (username_fallback or f"artist_{user_id}")[:128]
        aid = self.add_artist(user_id, name)
        return aid, name

    # tracks
    def add_user_track(self, user_id, file_id, title, performer, artist_id=None, storage_message_id=None):
        self.cur.execute("""
            INSERT INTO tracks (user_id, artist_id, title, performer, file_id, storage_message_id, is_common)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (user_id, artist_id, title, performer, file_id, storage_message_id))
        self.conn.commit()
        return self.cur.lastrowid

    def add_common_track(self, user_id, file_id, title, performer, artist_id=None, storage_message_id=None):
        self.cur.execute("""
            INSERT INTO tracks (user_id, artist_id, title, performer, file_id, storage_message_id, is_common)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (user_id, artist_id, title, performer, file_id, storage_message_id))
        self.conn.commit()
        return self.cur.lastrowid

    def get_user_tracks(self, user_id):
        self.cur.execute("SELECT * FROM tracks WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return self.cur.fetchall()

    def get_common_tracks(self):
        self.cur.execute("SELECT * FROM tracks WHERE is_common = 1 ORDER BY created_at DESC")
        return self.cur.fetchall()

    def get_track(self, track_id):
        self.cur.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
        return self.cur.fetchone()

    def delete_track(self, track_id):
        self.cur.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
        self.conn.commit()

    # notifications (utility)
    def add_notification(self, user_id, message):
        self.cur.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, message))
        self.conn.commit()

    def get_bot_version(self):
        self.cur.execute("SELECT value FROM bot_meta WHERE key = 'version'")
        row = self.cur.fetchone()
        return row[0] if row else None

    def set_bot_version(self, version):
        self.cur.execute("INSERT OR REPLACE INTO bot_meta (key, value) VALUES ('version', ?)", (version,))
        self.conn.commit()

        # --- version updates ---
    def has_version_been_sent(self, version: str) -> bool:
        self.cur.execute("SELECT version FROM sent_updates WHERE version = ?", (version,))
        return self.cur.fetchone() is not None

    def mark_version_as_sent(self, version: str):
        self.cur.execute("INSERT OR IGNORE INTO sent_updates (version) VALUES (?)", (version,))
        self.conn.commit()
