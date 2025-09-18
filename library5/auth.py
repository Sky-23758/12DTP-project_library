from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from config import app, get_db

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role
    def get_id(self):
        return str(self.id)
    @property
    def role(self):
        return self._role
    @role.setter
    def role(self, value):
        self._role = value

@login_manager.user_loader
def load_user(user_id):
    try:
        db = get_db()
        cursor = db.execute("SELECT id, username, password, role FROM Users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        print("Loading user - user_id:", user_id, "user_data:", user_data)

        if user_data is not None:
            user_id = user_data[0]
            username = user_data[1]
            role = user_data[3] 
            return User(user_id, username, role)
        return None
    except Exception as e:
        print("Error in load_user:", e)
        return None