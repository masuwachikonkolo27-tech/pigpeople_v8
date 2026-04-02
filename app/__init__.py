from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = "pigpeople_secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pigpeople.db"

    db.init_app(app)

    # 🔐 LOGIN SETUP
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .routes import main
    app.register_blueprint(main)

    # 🧠 CREATE DB + DEFAULT ADMIN
    with app.app_context():
        db.create_all()

        from werkzeug.security import generate_password_hash

        # 🔍 Check if admin already exists
        existing_admin = User.query.filter_by(username="masuwa_chikonkolo").first()

        if not existing_admin:
            admin = User(
                name="Masuwa Chikonkolo",
                username="masuwa_chikonkolo",
                password=generate_password_hash("chikonkz999"),
                role="admin"
            )

            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created!")

    return app