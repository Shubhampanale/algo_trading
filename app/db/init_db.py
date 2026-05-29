from app.db.base import Base
from app.db.session import engine

# import all models so they register
from app.db.models import user, broker_account, api_log, input_data  # noqa


def init_db():
    Base.metadata.create_all(bind=engine)