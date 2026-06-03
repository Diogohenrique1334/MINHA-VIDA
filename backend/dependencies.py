from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from backend.models import engine

@contextmanager
def pegar_sessao():
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
