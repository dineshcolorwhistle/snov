import os
import logging
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Dinesh%40%2312312@db.ocydnvzzvfucjxdjochw.supabase.co:5432/postgres")

@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise e
    finally:
        if conn:
            conn.close()

@contextmanager
def get_db_cursor():
    """
    Context manager for database cursors with RealDictCursor for dict-like results.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur

def init_db():
    """
    Initializes the database tables if they do not exist.
    """
    logger.info("Initializing database tables...")
    create_tables_sql = """
    -- Create user_settings table
    CREATE TABLE IF NOT EXISTS public.user_settings (
        id UUID PRIMARY KEY,
        snov_client_id TEXT,
        snov_client_secret TEXT,
        hunter_api_key TEXT,
        email_not_found_list_id TEXT,
        hunter_fallback_list_id TEXT,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
    );

    -- Create linkedin_not_found table
    CREATE TABLE IF NOT EXISTS public.linkedin_not_found (
        id SERIAL PRIMARY KEY,
        user_id UUID NOT NULL,
        first_name TEXT,
        last_name TEXT,
        company_name TEXT,
        platform TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
    );

    -- Create domain_not_found table
    CREATE TABLE IF NOT EXISTS public.domain_not_found (
        id SERIAL PRIMARY KEY,
        user_id UUID NOT NULL,
        first_name TEXT,
        last_name TEXT,
        company_name TEXT,
        linkedin_url TEXT,
        platform TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
    );

    -- Create email_not_found table
    CREATE TABLE IF NOT EXISTS public.email_not_found (
        id SERIAL PRIMARY KEY,
        user_id UUID NOT NULL,
        first_name TEXT,
        last_name TEXT,
        company_name TEXT,
        domain TEXT,
        linkedin_url TEXT,
        platform TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
    );

    -- Create email_unverified table
    CREATE TABLE IF NOT EXISTS public.email_unverified (
        id SERIAL PRIMARY KEY,
        user_id UUID NOT NULL,
        first_name TEXT,
        last_name TEXT,
        company_name TEXT,
        domain TEXT,
        email TEXT NOT NULL,
        linkedin_url TEXT,
        verification_status TEXT,
        platform TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
    );
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_tables_sql)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # We don't crash the server, but log it

# --- User Settings Functions ---

def get_user_settings(user_id: str) -> dict:
    """
    Retrieves the API keys and settings for a specific user.
    """
    sql = "SELECT * FROM public.user_settings WHERE id = %s"
    try:
        with get_db_cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            if row:
                # Convert UUID and datetime to string/standard formats
                row['id'] = str(row['id'])
                row['updated_at'] = row['updated_at'].isoformat()
                return row
    except Exception as e:
        logger.error(f"Error fetching user settings for {user_id}: {e}")
    return {}

def save_user_settings(user_id: str, settings: dict) -> bool:
    """
    Saves or updates the API keys and settings for a specific user.
    """
    sql = """
    INSERT INTO public.user_settings (
        id, snov_client_id, snov_client_secret, hunter_api_key, 
        email_not_found_list_id, hunter_fallback_list_id, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, TIMEZONE('utc'::text, NOW())
    )
    ON CONFLICT (id) DO UPDATE SET
        snov_client_id = EXCLUDED.snov_client_id,
        snov_client_secret = EXCLUDED.snov_client_secret,
        hunter_api_key = EXCLUDED.hunter_api_key,
        email_not_found_list_id = EXCLUDED.email_not_found_list_id,
        hunter_fallback_list_id = EXCLUDED.hunter_fallback_list_id,
        updated_at = TIMEZONE('utc'::text, NOW())
    """
    params = (
        user_id,
        settings.get("snov_client_id"),
        settings.get("snov_client_secret"),
        settings.get("hunter_api_key"),
        settings.get("email_not_found_list_id"),
        settings.get("hunter_fallback_list_id")
    )
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        return True
    except Exception as e:
        logger.error(f"Error saving user settings for {user_id}: {e}")
        return False

# --- Logging Functions ---

def log_linkedin_not_found(user_id: str, first_name: str, last_name: str, company_name: str, platform: str):
    sql = """
    INSERT INTO public.linkedin_not_found (user_id, first_name, last_name, company_name, platform)
    VALUES (%s, %s, %s, %s, %s)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, first_name, last_name, company_name, platform))
        logger.info(f"Logged missing LinkedIn for {first_name} {last_name} ({platform})")
    except Exception as e:
        logger.error(f"Error logging missing LinkedIn: {e}")

def log_domain_not_found(user_id: str, first_name: str, last_name: str, company_name: str, linkedin_url: str, platform: str):
    sql = """
    INSERT INTO public.domain_not_found (user_id, first_name, last_name, company_name, linkedin_url, platform)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, first_name, last_name, company_name, linkedin_url, platform))
        logger.info(f"Logged missing domain for {company_name} ({platform})")
    except Exception as e:
        logger.error(f"Error logging missing domain: {e}")

def log_email_not_found(user_id: str, first_name: str, last_name: str, company_name: str, domain: str, linkedin_url: str, platform: str):
    sql = """
    INSERT INTO public.email_not_found (user_id, first_name, last_name, company_name, domain, linkedin_url, platform)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, first_name, last_name, company_name, domain, linkedin_url, platform))
        logger.info(f"Logged missing email for {first_name} {last_name} @ {domain} ({platform})")
    except Exception as e:
        logger.error(f"Error logging missing email: {e}")

def log_email_unverified(user_id: str, first_name: str, last_name: str, company_name: str, domain: str, email: str, linkedin_url: str, verification_status: str, platform: str):
    sql = """
    INSERT INTO public.email_unverified (user_id, first_name, last_name, company_name, domain, email, linkedin_url, verification_status, platform)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, first_name, last_name, company_name, domain, email, linkedin_url, verification_status, platform))
        logger.info(f"Logged unverified email {email} (status: {verification_status}, platform: {platform})")
    except Exception as e:
        logger.error(f"Error logging unverified email: {e}")

# --- Retrieve Logs for UI ---

def get_logs(log_type: str, user_id: str, platform: str = None, page: int = 1, limit: int = 20) -> tuple:
    """
    Retrieves paginated tracking logs for a specific user and platform.
    """
    allowed_types = ["linkedin_not_found", "domain_not_found", "email_not_found", "email_unverified"]
    if log_type not in allowed_types:
        raise ValueError(f"Invalid log type: {log_type}")

    offset = (page - 1) * limit
    
    # Build query
    query_parts = [f"SELECT * FROM public.{log_type} WHERE user_id = %s"]
    count_parts = [f"SELECT COUNT(*) FROM public.{log_type} WHERE user_id = %s"]
    params = [user_id]

    if platform:
        query_parts.append("AND platform = %s")
        count_parts.append("AND platform = %s")
        params.append(platform)

    # Order and paginate
    query_parts.append("ORDER BY created_at DESC LIMIT %s OFFSET %s")
    query_params = params + [limit, offset]
    count_params = params

    try:
        with get_db_cursor() as cur:
            # Get total count
            cur.execute(" ".join(count_parts), tuple(count_params))
            total = cur.fetchone()["count"]

            # Get logs
            cur.execute(" ".join(query_parts), tuple(query_params))
            rows = cur.fetchall()

            # Format rows
            for row in rows:
                row["created_at"] = row["created_at"].isoformat()
                if "user_id" in row:
                    row["user_id"] = str(row["user_id"])

            return rows, total
    except Exception as e:
        logger.error(f"Error fetching logs for {log_type}: {e}")
        return [], 0
