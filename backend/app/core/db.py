from sqlmodel import SQLModel, create_engine, Session
from app.models.job import ProcessingJob # Import our model so SQLModel knows about it
from app.core.config import settings

# Create the SQLAlchemy Engine
# echo=True means it will print the raw SQL queries to your terminal (great for debugging)
engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    """
    Looks at all SQLModel classes imported into this file and creates 
    the corresponding tables in PostgreSQL if they don't exist.
    """
    print("Initializing Database Tables...")
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    Generator function to provide a database session to our FastAPI endpoints.
    """
    with Session(engine) as session:
        yield session