from abc import ABC, abstractmethod
from pathlib import Path
import networkx as nx
from sqlalchemy import create_engine
from log import general_logger

from config import Config
from storage.common import Base


class StorageBase(ABC):
    def __init__(self, db_name: str, dest_dir: Path = None, overwrite: bool = False):
        _dest_dir = dest_dir / "db" if dest_dir else Config.DEFAULT_DB_DIR
        db_path = _dest_dir / Path(f"{self.get_filename_prefix()}-{db_name}.db")

        if overwrite and db_path.exists():
            db_path.unlink()
            general_logger.debug(f"Старая база удалена: {db_path}")

        if not _dest_dir.exists():
            _dest_dir.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
        Base.metadata.create_all(self.engine)

    @staticmethod
    @abstractmethod
    def get_filename_prefix() -> str:
        ...

    @abstractmethod
    def dump(self, g: nx.DiGraph):
        pass

    @abstractmethod
    def load(self):
        pass
