import os
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from dataclasses import dataclass, field

class Base(AsyncAttrs, DeclarativeBase):
    pass

@dataclass
class Database:
    ''' database config'''
    DRIVER: str
    TYPE: str
    USER: str
    PASSWORD: str
    HOST: str
    NAME: str
    CONN: str
    ENGINE : object = field(init=False, default=None)

    def __post_init__(self):
        self.load_env_variables()  # Carga las variables de entorno
        self.ENGINE = self.get_engine()

    def load_env_variables(self):
        """Cargar variables de entorno en función del tipo de base de datos. audit o public"""
        suffix = "_AUDIT" if self.TYPE == "audit" else ""
        self.DRIVER = os.environ.get(f"DB_DRIVER{suffix}", "root")
        self.USER = os.environ.get(f"DB_USER{suffix}", "root")
        self.PASSWORD = os.environ.get(f"DB_PASS{suffix}", "pass")
        self.HOST = os.environ.get(f"DB_HOST{suffix}", "127.0.0.1")
        self.NAME = os.environ.get(f"DB_NAME{suffix}", "db")
        self.CONN = os.environ.get(f"DB_CONN{suffix}", "TCP")

    @property
    def connection_url(self) -> dict:
        if self.CONN == "SOCKET":
            print(" ### Database Unix Socket ### ")
            # build path string replacing special characters with UNICODE UTF-8
            path = self.HOST.replace("/","%2F").replace(".","%2E").replace("-","%2D").replace(":","%3A")
            url = f"{self.DRIVER}://{self.USER}:{self.PASSWORD}@/{self.NAME}?host={path}" 
        else:
            print(" ### Database TCP Connection  ### ")
            url = F'{self.DRIVER}://{self.USER}:{self.PASSWORD}@{self.HOST}/{self.NAME}'
        return url
    
    def get_engine(self,future: bool = True, echo: bool = False):
        """ return a engine instance """
        if self.ENGINE is not None:
            return self.ENGINE
        
        url = self.connection_url
        self.ENGINE = create_async_engine(
            url,
            future=future,
            echo=echo,
            pool_size=5,
            max_overflow=0,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_use_lifo=True
            )
        return self.ENGINE

    async def session_maker(self):
        ''' return session maker '''
        engine = self.get_engine()
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
        return SessionLocal()

async def get_db_public():
    try:
        session = await GLOBAL_DB_PUBLIC.session_maker()
        yield session
    finally:
        await session.close()

GLOBAL_DB_PUBLIC = Database(
    DRIVER=None,TYPE="public",USER=None, PASSWORD=None,
    HOST=None, NAME=None, CONN=None
)