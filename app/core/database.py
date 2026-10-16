from threading import Lock

from mysql.connector import pooling

from app.core.config import settings


class DatabaseNotConfiguredError(RuntimeError):
    pass


class DatabaseManager:
    """Crea el pool bajo demanda para que la API pueda arrancar y mostrar /docs."""

    def __init__(self) -> None:
        self._pool = None
        self._lock = Lock()

    def _create_pool(self):
        if not settings.database_configured:
            raise DatabaseNotConfiguredError("Configura DB_HOST, DB_USER y DB_PASSWORD en el archivo .env")
        return pooling.MySQLConnectionPool(
            pool_name="iot_pool",
            pool_size=settings.DB_POOL_SIZE,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            connection_timeout=10,
            autocommit=False,
        )

    def get_connection(self):
        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    self._pool = self._create_pool()
        return self._pool.get_connection()

    def ping(self) -> bool:
        connection = self.get_connection()
        try:
            connection.ping(reconnect=True, attempts=1, delay=0)
            return True
        finally:
            connection.close()


db_manager = DatabaseManager()

