import asyncio
import os
import importlib
import importlib.util
import inspect
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError
import logging
from dotenv import load_dotenv

load_dotenv()  
from app.database import GLOBAL_DB_PUBLIC, Base

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, database_instance):
        self.db = database_instance
        self.engine = database_instance.get_engine()
        
    async def create_database_if_not_exists(self):
        """Crear la base de datos si no existe"""
        try:
            # Crear URL sin el nombre de la base de datos para conectar al servidor
            base_url = self.db.connection_url.rsplit('/', 1)[0]
            
            # Si es MySQL, usar pymysql como driver
            if self.db.DRIVER.startswith('mysql'):
                base_url = base_url.replace('mysql+asyncmy', 'mysql+pymysql')
                # Para MySQL, necesitamos una conexión síncrona temporal
                from sqlalchemy import create_engine
                sync_engine = create_engine(base_url, echo=False)
                
                try:
                    with sync_engine.connect() as conn:
                        # Verificar si la base de datos existe
                        result = conn.execute(text(f"SHOW DATABASES LIKE '{self.db.NAME}'"))
                        if not result.fetchone():
                            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{self.db.NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                            logger.info(f"Base de datos '{self.db.NAME}' creada exitosamente")
                        else:
                            logger.info(f"Base de datos '{self.db.NAME}' ya existe")
                except Exception as e:
                    logger.error(f"Error creando base de datos MySQL: {e}")
                    raise
                finally:
                    sync_engine.dispose()
                    
            elif self.db.DRIVER.startswith('postgresql'):
                # Para PostgreSQL
                from sqlalchemy import create_engine
                import asyncpg
                
                try:
                    # Conectar a la base de datos postgres por defecto
                    conn = await asyncpg.connect(
                        user=self.db.USER,
                        password=self.db.PASSWORD,
                        host=self.db.HOST,
                        database='postgres'
                    )
                    
                    # Verificar si la base de datos existe
                    exists = await conn.fetchval(
                        "SELECT 1 FROM pg_database WHERE datname = $1", 
                        self.db.NAME
                    )
                    
                    if not exists:
                        await conn.execute(f'CREATE DATABASE "{self.db.NAME}"')
                        logger.info(f"Base de datos '{self.db.NAME}' creada exitosamente")
                    else:
                        logger.info(f"Base de datos '{self.db.NAME}' ya existe")
                        
                    await conn.close()
                    
                except Exception as e:
                    logger.error(f"Error creando base de datos PostgreSQL: {e}")
                    raise
                    
        except Exception as e:
            logger.warning(f"No se pudo crear la base de datos automáticamente: {e}")
            logger.info("Asegúrate de que la base de datos existe manualmente")

    def load_models_from_tables(self):
        """Importar todos los modelos desde la carpeta tables usando importación directa"""
        import sys
        
        tables_dir = Path(__file__).parent / "app/tables"
        
        if not tables_dir.exists():
            logger.error(f"Directorio 'tables' no encontrado en {tables_dir}")
            return []
        
        models = []
        
        # Obtener todos los archivos .py en la carpeta tables
        for py_file in tables_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
                
            try:
                # Importación directa usando spec_from_file_location
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    logger.error(f"No se pudo crear spec para {py_file}")
                    continue
                    
                module = importlib.util.module_from_spec(spec)
                
                # Agregar al sys.modules antes de ejecutar para evitar problemas de importación circular
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Buscar clases que hereden de Base
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        hasattr(obj, '__tablename__') and 
                        issubclass(obj, Base) and 
                        obj != Base):
                        models.append(obj)
                        logger.info(f"Modelo encontrado: {obj.__name__} desde {py_file.name}")
                        
            except Exception as e:
                logger.error(f"Error procesando {py_file.name}: {e}")
                # Limpiar sys.modules si hubo error
                if module_name in sys.modules:
                    del sys.modules[module_name]
        
        logger.info(f"Total de modelos encontrados: {len(models)}")
        return models

    async def create_tables(self):
        """Crear todas las tablas definidas en los modelos"""
        try:
            # Cargar todos los modelos
            models = self.load_models_from_tables()
            
            if not models:
                logger.warning("No se encontraron modelos para crear tablas")
                return False
            
            # Crear todas las tablas
            async with self.engine.begin() as conn:
                # Usar run_sync para operaciones síncronas dentro del contexto async
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Todas las tablas han sido creadas exitosamente")
                
            return True
            
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
            raise

    async def check_tables_exist(self):
        """Verificar qué tablas existen en la base de datos"""
        try:
            async with self.engine.connect() as conn:
                if self.db.DRIVER.startswith('mysql'):
                    result = await conn.execute(text("SHOW TABLES"))
                elif self.db.DRIVER.startswith('postgresql'):
                    result = await conn.execute(text("""
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public'
                    """))
                else:
                    # SQLite u otros
                    result = await conn.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table'
                    """))
                
                tables = [row[0] for row in result.fetchall()]
                return tables
                
        except Exception as e:
            logger.error(f"Error verificando tablas existentes: {e}")
            return []

    async def initialize_database(self):
        """Proceso completo de inicialización"""
        logger.info("Iniciando proceso de inicialización de base de datos...")
        
        try:
            # 1. Crear base de datos si no existe
            await self.create_database_if_not_exists()
            
            # 2. Verificar tablas existentes
            existing_tables = await self.check_tables_exist()
            logger.info(f"Tablas existentes: {existing_tables}")
            
            # 3. Crear tablas si no existen
            if not existing_tables:
                logger.info("No se encontraron tablas. Creando estructura completa...")
                await self.create_tables()
            else:
                logger.info("Se encontraron tablas existentes. Verificando estructura...")
                # Aquí podrías agregar lógica adicional para verificar la estructura
                await self.create_tables()  # create_all solo crea las que no existen
            
            logger.info("Inicialización de base de datos completada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error durante la inicialización: {e}")
            raise

async def main():
    """Función principal para ejecutar la inicialización"""
    initializer = DatabaseInitializer(GLOBAL_DB_PUBLIC)
    await initializer.initialize_database()

if __name__ == "__main__":
    asyncio.run(main())