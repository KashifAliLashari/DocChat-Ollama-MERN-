import sqlite3
from pathlib import Path
from typing import Optional

from .settings import settings


def ensure_sqlite_path(path: Optional[Path] = None) -> Path:
    """Ensure the SQLite parent directory exists and return the path."""
    target = path or settings.sqlite_path
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def get_connection(path: Optional[Path] = None) -> sqlite3.Connection:
    """Create a SQLite connection with row_factory for dict-like rows."""
    db_path = ensure_sqlite_path(path)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create core tables if they do not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()


def ensure_conversation(
    conn: sqlite3.Connection, conversation_id: str, title: str = "Conversation"
) -> None:
    """Insert a conversation if it does not already exist."""
    conn.execute(
        """
        INSERT OR IGNORE INTO conversations (id, title) VALUES (?, ?)
        """,
        (conversation_id, title),
    )
    conn.commit()


def update_conversation_title_if_empty(
    conn: sqlite3.Connection, conversation_id: str, title: str
) -> None:
    """
    Set the conversation title if it is empty or still at the default.

    Avoids overwriting user-updated titles.
    """
    conn.execute(
        """
        UPDATE conversations
        SET title = ?
        WHERE id = ?
          AND (title IS NULL OR title = '' OR title = 'Conversation')
        """,
        (title, conversation_id),
    )
    conn.commit()


def insert_message(
    conn: sqlite3.Connection, message_id: str, conversation_id: str, role: str, content: str
) -> None:
    """Insert a message row."""
    conn.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content)
        VALUES (?, ?, ?, ?)
        """,
        (message_id, conversation_id, role, content),
    )
    conn.commit()


def insert_document(conn: sqlite3.Connection, document_id: str, name: str, path: str) -> None:
    """Insert a document record."""
    conn.execute(
        """
        INSERT INTO documents (id, name, path)
        VALUES (?, ?, ?)
        """,
        (document_id, name, path),
    )
    conn.commit()


def list_documents(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all documents ordered by creation time desc."""
    cur = conn.execute(
        """
        SELECT id, name, path, created_at
        FROM documents
        ORDER BY datetime(created_at) DESC
        """
    )
    return cur.fetchall()


def delete_document(conn: sqlite3.Connection, document_id: str) -> bool:
    """Delete a document by ID. Returns True if deleted, False if not found."""
    cur = conn.execute("SELECT path FROM documents WHERE id = ?", (document_id,))
    row = cur.fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    conn.commit()
    return True


def list_conversations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all conversations ordered by creation time desc."""
    cur = conn.execute(
        """
        SELECT id, title, created_at
        FROM conversations
        ORDER BY datetime(created_at) DESC
        """
    )
    return cur.fetchall()


def list_messages(conn: sqlite3.Connection, conversation_id: str) -> list[sqlite3.Row]:
    """Return messages for a conversation ordered by creation time asc."""
    cur = conn.execute(
        """
        SELECT id, conversation_id, role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY datetime(created_at) ASC
        """,
        (conversation_id,),
    )
    return cur.fetchall()


def delete_conversation(conn: sqlite3.Connection, conversation_id: str) -> bool:
    """Delete a conversation and its messages. Returns True if deleted."""
    conn.execute(
        """
        DELETE FROM messages WHERE conversation_id = ?
        """,
        (conversation_id,),
    )
    cur = conn.execute(
        """
        DELETE FROM conversations WHERE id = ?
        """,
        (conversation_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def rename_conversation(conn: sqlite3.Connection, conversation_id: str, new_title: str) -> bool:
    """Rename a conversation. Returns True if updated."""
    cur = conn.execute(
        """
        UPDATE conversations SET title = ? WHERE id = ?
        """,
        (new_title, conversation_id),
    )
    conn.commit()
    return cur.rowcount > 0

