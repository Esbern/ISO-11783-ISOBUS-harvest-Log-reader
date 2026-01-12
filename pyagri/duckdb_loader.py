"""DuckDB loader for TLG point data.

Provides utilities to load all TLG CSV files into DuckDB for unified analysis
without loading everything into memory at once.
"""
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import duckdb
except ImportError:
    duckdb = None


def create_tlg_database(tlg_csv_dir: str, db_path: str = ':memory:', table_name: str = 'tlg_points') -> 'duckdb.DuckDBPyConnection':
    """Create a DuckDB database from all TLG CSV files.
    
    Args:
        tlg_csv_dir: Directory containing TLG CSV files (e.g., 'TASKDATA-TLG0001.csv')
        db_path: Path to DuckDB file (':memory:' for in-memory database)
        table_name: Name of table to create
    
    Returns:
        DuckDB connection object
    
    Example:
        >>> conn = create_tlg_database('data/tlg_csvs', 'data/tlg_points.duckdb')
        >>> df = conn.execute("SELECT * FROM tlg_points WHERE CompositeTLGID = 'TASKDATA/TLG00001' LIMIT 10").df()
    """
    if duckdb is None:
        raise ImportError("duckdb is required. Install with: pip install duckdb")
    
    csv_dir = Path(tlg_csv_dir)
    if not csv_dir.exists():
        raise FileNotFoundError(f"TLG CSV directory not found: {csv_dir}")
    
    # Find all TLG CSV files
    tlg_files = list(csv_dir.glob('*-TLG*.csv'))
    if not tlg_files:
        raise FileNotFoundError(f"No TLG CSV files found in {csv_dir}")
    
    logger.info(f"Found {len(tlg_files)} TLG CSV files")
    
    # Create/connect to database
    conn = duckdb.connect(db_path)
    
    # Create table by reading first file to get schema
    first_file = tlg_files[0]
    logger.info(f"Creating table {table_name} from schema of {first_file.name}")
    
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS 
        SELECT * FROM read_csv_auto('{first_file}')
        WHERE 1=0
    """)
    
    # Insert all CSV files into the table
    logger.info(f"Loading {len(tlg_files)} TLG CSV files into {table_name}...")
    
    for csv_file in tlg_files:
        logger.debug(f"Loading {csv_file.name}")
        conn.execute(f"""
            INSERT INTO {table_name}
            SELECT * FROM read_csv_auto('{csv_file}')
        """)
    
    # Get row count
    count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    logger.info(f"Loaded {count:,} total points into {table_name}")
    
    # Create index on CompositeTLGID for faster joins
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_composite_tlg ON {table_name}(CompositeTLGID)")
    
    return conn


def query_tlg_by_task(conn: 'duckdb.DuckDBPyConnection', 
                      composite_tlg_ids: List[str],
                      table_name: str = 'tlg_points') -> 'pd.DataFrame':
    """Query TLG points for specific tasks.
    
    Args:
        conn: DuckDB connection
        composite_tlg_ids: List of composite TLG IDs (e.g., ['TASKDATA/TLG00001', 'TASKDATA/TLG00002'])
        table_name: Table name
    
    Returns:
        pandas DataFrame with filtered points
    """
    if not composite_tlg_ids:
        raise ValueError("composite_tlg_ids cannot be empty")
    
    # Build IN clause
    ids_str = "', '".join(composite_tlg_ids)
    query = f"""
        SELECT * FROM {table_name}
        WHERE CompositeTLGID IN ('{ids_str}')
    """
    
    return conn.execute(query).df()


def export_filtered_tlg(conn: 'duckdb.DuckDBPyConnection',
                        composite_tlg_ids: List[str],
                        output_path: str,
                        table_name: str = 'tlg_points'):
    """Export filtered TLG points to CSV for kriging analysis.
    
    Args:
        conn: DuckDB connection
        composite_tlg_ids: List of composite TLG IDs to filter
        output_path: Output CSV path
        table_name: Table name
    """
    ids_str = "', '".join(composite_tlg_ids)
    
    conn.execute(f"""
        COPY (
            SELECT * FROM {table_name}
            WHERE CompositeTLGID IN ('{ids_str}')
        ) TO '{output_path}' (HEADER, DELIMITER ',')
    """)
    
    logger.info(f"Exported filtered TLG data to {output_path}")


def get_tlg_summary(conn: 'duckdb.DuckDBPyConnection', table_name: str = 'tlg_points') -> 'pd.DataFrame':
    """Get summary statistics by CompositeTLGID.
    
    Returns DataFrame with count, min/max coordinates, etc. per TLG.
    """
    query = f"""
        SELECT 
            CompositeTLGID,
            COUNT(*) as point_count,
            MIN(time_stamp) as first_point,
            MAX(time_stamp) as last_point
        FROM {table_name}
        GROUP BY CompositeTLGID
        ORDER BY CompositeTLGID
    """
    
    return conn.execute(query).df()
