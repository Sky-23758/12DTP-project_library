from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from config import app, get_db

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, real_name, email, role):
        self.id = id
        self.username = username
        self.real_name = real_name
        self.email = email
        self._role = int(float(str(role))) if role is not None and str(
            role).strip() else 0

    def get_id(self):
        return str(self.id)

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, value):
        self._role = int(float(str(value))) if value is not None and str(
            value).strip() else 0


@login_manager.user_loader
def load_user(user_id):
    try:
        db = get_db()
        cursor = db.execute(
            "SELECT id, username, password, real_name, email, role FROM Users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        print("Loading user - user_id:", user_id, "user_data:", user_data)

        if user_data is not None:
            user_id = user_data[0]
            username = user_data[1]
            real_name = user_data[3]
            email = user_data[4]
            role = int(float(str(user_data[5]))) if user_data[5] is not None and str(
                user_data[5]).strip() else 0
            return User(user_id, username, real_name, email, role)
        return None
    except Exception as e:
        print("Error in load_user:", e)
        return None
