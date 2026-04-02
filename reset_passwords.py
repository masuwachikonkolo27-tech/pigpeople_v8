from run import app
from app import db
from app.models import User

with app.app_context():

    print("Resetting database...")

    db.drop_all()
    db.create_all()

    admin = User(
        name="Administrator",
        username="admin",
        password="admin123",
        role="admin"
    )

    worker = User(
        name="Worker One",
        username="worker1",
        password="worker123",
        role="worker"
    )

    db.session.add(admin)
    db.session.add(worker)
    db.session.commit()

    print("Database reset complete!")
    print("Admin login: admin / admin123")
    print("Worker login: worker1 / worker123")