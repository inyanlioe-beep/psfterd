import os
import sqlite3
import json
from flask import Flask, jsonify, request, render_template, session
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Path for mock SQLite database
MOCK_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'peoplesoft_mock.db')

# Global database connection pool reference
db_connection_info = {
    'connected': False,
    'engine': None,
    'dialect': 'sqlite',  # 'sqlite' (mock), 'oracle', 'mssql', 'postgresql'
    'schema': None
}

def init_mock_db():
    """Initializes a local SQLite database that simulates PeopleSoft system tables and schemas."""
    if os.path.exists(MOCK_DB_PATH):
        return

    print("Initializing Peoplesoft Mock Database...")
    conn = sqlite3.connect(MOCK_DB_PATH)
    cursor = conn.cursor()

    # Create Peoplesoft metadata tables
    cursor.execute("""
    CREATE TABLE PSRECDEFN (
        RECNAME TEXT PRIMARY KEY,
        RECDESC TEXT,
        PARENTRECORD TEXT,
        RECTYPE INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE PSRECFIELD (
        RECNAME TEXT,
        FIELDNAME TEXT,
        FIELDNUM INTEGER,
        USEEDIT INTEGER,
        EDITTABLE TEXT,
        PRIMARY KEY (RECNAME, FIELDNAME)
    )
    """)

    cursor.execute("""
    CREATE TABLE PSDBFIELD (
        FIELDNAME TEXT PRIMARY KEY,
        FIELDTYPE INTEGER,
        LENGTH INTEGER,
        DECIMALPOS INTEGER
    )
    """)

    # Populate Metadata for records (Tables)
    # RECTYPE: 0 = SQL Table, 1 = SQL View
    records = [
        ('PERSONAL_DATA', 'Personal Data Table', '', 0),
        ('NAMES', 'Person Names Table', 'PERSONAL_DATA', 0),
        ('ADDRESSES', 'Person Address Table', 'PERSONAL_DATA', 0),
        ('JOB', 'Employee Job History Table', 'PERSONAL_DATA', 0),
        ('DEPT_TBL', 'Department Master Table', '', 0),
        ('JOBCODE_TBL', 'Job Code Master Table', '', 0),
        ('LOCATION_TBL', 'Location Master Table', '', 0),
        ('COUNTRY_TBL', 'Country Master Table', '', 0),
        ('STATE_TBL', 'State/Province Master Table', '', 0)
    ]
    cursor.executemany("INSERT INTO PSRECDEFN VALUES (?, ?, ?, ?)", records)

    # Populate Field details
    # FIELDTYPE: 0=Char, 1=Long Char, 2=Number, 3=Signed Number, 4=Date, 5=Time, 6=DateTime
    fields = [
        ('EMPLID', 0, 11, 0),
        ('NAME', 0, 50, 0),
        ('SEX', 0, 1, 0),
        ('BIRTHDATE', 4, 10, 0),
        ('MAR_STATUS', 0, 1, 0),
        ('NAME_TYPE', 0, 3, 0),
        ('EFFDT', 4, 10, 0),
        ('EFF_STATUS', 0, 1, 0),
        ('FIRST_NAME', 0, 30, 0),
        ('LAST_NAME', 0, 30, 0),
        ('ADDRESS_TYPE', 0, 3, 0),
        ('COUNTRY', 0, 3, 0),
        ('ADDRESS1', 0, 55, 0),
        ('CITY', 0, 30, 0),
        ('STATE', 0, 6, 0),
        ('EMPL_RCD', 2, 3, 0),
        ('EFFSEQ', 2, 3, 0),
        ('DEPTID', 0, 10, 0),
        ('JOBCODE', 0, 6, 0),
        ('LOCATION', 0, 10, 0),
        ('SUPERVISOR_ID', 0, 11, 0),
        ('HR_STATUS', 0, 1, 0),
        ('ACTION', 0, 3, 0),
        ('SETID', 0, 5, 0),
        ('DESCR', 0, 30, 0),
        ('COMPANY', 0, 3, 0)
    ]
    cursor.executemany("INSERT INTO PSDBFIELD VALUES (?, ?, ?, ?)", fields)

    # Link fields to records
    # USEEDIT: 1=Primary Key, 0=Non-Key. (Simplified representation of PeopleTools bitmask)
    # EDITTABLE: Defines prompt relationship
    rec_fields = [
        # PERSONAL_DATA
        ('PERSONAL_DATA', 'EMPLID', 1, 1, ''),
        ('PERSONAL_DATA', 'NAME', 2, 0, ''),
        ('PERSONAL_DATA', 'SEX', 3, 0, ''),
        ('PERSONAL_DATA', 'BIRTHDATE', 4, 0, ''),
        ('PERSONAL_DATA', 'MAR_STATUS', 5, 0, ''),
        
        # NAMES (Parent: PERSONAL_DATA)
        ('NAMES', 'EMPLID', 1, 1, ''),
        ('NAMES', 'NAME_TYPE', 2, 1, ''),
        ('NAMES', 'EFFDT', 3, 1, ''),
        ('NAMES', 'EFF_STATUS', 4, 0, ''),
        ('NAMES', 'FIRST_NAME', 5, 0, ''),
        ('NAMES', 'LAST_NAME', 6, 0, ''),
        
        # ADDRESSES (Parent: PERSONAL_DATA)
        ('ADDRESSES', 'EMPLID', 1, 1, ''),
        ('ADDRESSES', 'ADDRESS_TYPE', 2, 1, ''),
        ('ADDRESSES', 'EFFDT', 3, 1, ''),
        ('ADDRESSES', 'EFF_STATUS', 4, 0, ''),
        ('ADDRESSES', 'COUNTRY', 5, 0, 'COUNTRY_TBL'),
        ('ADDRESSES', 'ADDRESS1', 6, 0, ''),
        ('ADDRESSES', 'CITY', 7, 0, ''),
        ('ADDRESSES', 'STATE', 8, 0, 'STATE_TBL'),
        
        # JOB (Parent: PERSONAL_DATA)
        ('JOB', 'EMPLID', 1, 1, ''),
        ('JOB', 'EMPL_RCD', 2, 1, ''),
        ('JOB', 'EFFDT', 3, 1, ''),
        ('JOB', 'EFFSEQ', 4, 1, ''),
        ('JOB', 'DEPTID', 5, 0, 'DEPT_TBL'),
        ('JOB', 'JOBCODE', 6, 0, 'JOBCODE_TBL'),
        ('JOB', 'LOCATION', 7, 0, 'LOCATION_TBL'),
        ('JOB', 'SUPERVISOR_ID', 8, 0, 'PERSONAL_DATA'),
        ('JOB', 'HR_STATUS', 9, 0, ''),
        ('JOB', 'ACTION', 10, 0, ''),
        
        # DEPT_TBL
        ('DEPT_TBL', 'SETID', 1, 1, ''),
        ('DEPT_TBL', 'DEPTID', 2, 1, ''),
        ('DEPT_TBL', 'EFFDT', 3, 1, ''),
        ('DEPT_TBL', 'EFF_STATUS', 4, 0, ''),
        ('DEPT_TBL', 'DESCR', 5, 0, ''),
        ('DEPT_TBL', 'COMPANY', 6, 0, ''),
        
        # JOBCODE_TBL
        ('JOBCODE_TBL', 'SETID', 1, 1, ''),
        ('JOBCODE_TBL', 'JOBCODE', 2, 1, ''),
        ('JOBCODE_TBL', 'EFFDT', 3, 1, ''),
        ('JOBCODE_TBL', 'EFF_STATUS', 4, 0, ''),
        ('JOBCODE_TBL', 'DESCR', 5, 0, ''),
        
        # LOCATION_TBL
        ('LOCATION_TBL', 'SETID', 1, 1, ''),
        ('LOCATION_TBL', 'LOCATION', 2, 1, ''),
        ('LOCATION_TBL', 'EFFDT', 3, 1, ''),
        ('LOCATION_TBL', 'EFF_STATUS', 4, 0, ''),
        ('LOCATION_TBL', 'DESCR', 5, 0, ''),
        
        # COUNTRY_TBL
        ('COUNTRY_TBL', 'COUNTRY', 1, 1, ''),
        ('COUNTRY_TBL', 'DESCR', 2, 0, ''),
        
        # STATE_TBL
        ('STATE_TBL', 'COUNTRY', 1, 1, 'COUNTRY_TBL'),
        ('STATE_TBL', 'STATE', 2, 1, ''),
        ('STATE_TBL', 'DESCR', 3, 0, '')
    ]
    cursor.executemany("INSERT INTO PSRECFIELD VALUES (?, ?, ?, ?, ?)", rec_fields)

    conn.commit()
    conn.close()
    print("Mock Database initialized successfully.")

def get_db_connection():
    """Gets the active database engine. Falls back to mock SQLite if none configured."""
    if db_connection_info['connected'] and db_connection_info['engine']:
        return db_connection_info['engine']
    
    # Fallback to local SQLite mock DB
    init_mock_db()
    sqlite_uri = f"sqlite:///{MOCK_DB_PATH}"
    db_connection_info['engine'] = create_engine(sqlite_uri)
    db_connection_info['dialect'] = 'sqlite'
    db_connection_info['connected'] = True
    return db_connection_info['engine']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        'connected': db_connection_info['connected'],
        'dialect': db_connection_info['dialect'],
        'schema': db_connection_info['schema']
    })

@app.route('/api/connect', methods=['POST'])
def connect_db():
    data = request.json
    db_type = data.get('db_type')  # 'oracle', 'mssql', 'postgresql', 'sqlite_mock'
    
    if db_type == 'sqlite_mock':
        db_connection_info['connected'] = False
        db_connection_info['engine'] = None
        db_connection_info['dialect'] = 'sqlite'
        db_connection_info['schema'] = None
        get_db_connection()
        return jsonify({'status': 'success', 'message': 'Switched to SQLite Mock Database.'})

    try:
        # Build connection string based on dialect
        if db_type == 'oracle':
            # Support connection string or parameters
            conn_str = data.get('conn_string')
            if not conn_str:
                user = data.get('username')
                pwd = data.get('password')
                host = data.get('host')
                port = data.get('port', 1521)
                service = data.get('dbname')
                # Python oracledb thin mode dialect
                conn_str = f"oracle+oracledb://{user}:{pwd}@{host}:{port}/?service_name={service}"
            engine = create_engine(conn_str)
            
        elif db_type == 'mssql':
            conn_str = data.get('conn_string')
            if not conn_str:
                user = data.get('username')
                pwd = data.get('password')
                host = data.get('host')
                port = data.get('port', 1433)
                dbname = data.get('dbname')
                driver = data.get('driver', 'ODBC Driver 17 for SQL Server')
                # Escape spaces in driver name
                driver_escaped = driver.replace(" ", "+")
                conn_str = f"mssql+pyodbc://{user}:{pwd}@{host}:{port}/{dbname}?driver={driver_escaped}"
            engine = create_engine(conn_str)
            
        elif db_type == 'postgresql':
            conn_str = data.get('conn_string')
            if not conn_str:
                user = data.get('username')
                pwd = data.get('password')
                host = data.get('host')
                port = data.get('port', 5432)
                dbname = data.get('dbname')
                conn_str = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}"
            engine = create_engine(conn_str)
        else:
            return jsonify({'status': 'error', 'message': f'Unsupported database dialect: {db_type}'}), 400

        # Verify connection by executing a simple query
        with engine.connect() as conn:
            # Check if PSRECDEFN exists to verify it's a PeopleSoft database
            try:
                conn.execute(text("SELECT COUNT(*) FROM PSRECDEFN")).fetchone()
            except Exception:
                return jsonify({
                    'status': 'warning',
                    'message': 'Connected to database, but PSRECDEFN table was not found. Are you sure this is a PeopleSoft database?'
                })

        db_connection_info['engine'] = engine
        db_connection_info['dialect'] = db_type
        db_connection_info['connected'] = True
        db_connection_info['schema'] = data.get('schema') or None
        
        return jsonify({'status': 'success', 'message': f'Successfully connected to {db_type} database.'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Connection failed: {str(e)}'}), 500

@app.route('/api/records', methods=['GET'])
def list_records():
    search = request.args.get('search', '').upper()
    engine = get_db_connection()
    
    # Query PSRECDEFN for matching SQL tables (RECTYPE = 0)
    query_str = """
        SELECT RECNAME, RECDESC, PARENTRECORD, RECTYPE 
        FROM PSRECDEFN 
        WHERE RECTYPE = 0 
    """
    params = {}
    if search:
        query_str += " AND RECNAME LIKE :search"
        params['search'] = f"%{search}%"
    
    query_str += " ORDER BY RECNAME ASC LIMIT 100" if db_connection_info['dialect'] == 'sqlite' else " ORDER BY RECNAME ASC"
    
    # Adapt query for Oracle / SQL Server if not using sqlite limits
    if db_connection_info['dialect'] == 'oracle' and search:
        query_str = """
            SELECT RECNAME, RECDESC, PARENTRECORD, RECTYPE 
            FROM PSRECDEFN 
            WHERE RECTYPE = 0 AND RECNAME LIKE :search AND ROWNUM <= 100
            ORDER BY RECNAME ASC
        """
    elif db_connection_info['dialect'] == 'mssql' and search:
        query_str = """
            SELECT TOP 100 RECNAME, RECDESC, PARENTRECORD, RECTYPE 
            FROM PSRECDEFN 
            WHERE RECTYPE = 0 AND RECNAME LIKE :search
            ORDER BY RECNAME ASC
        """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query_str), params)
            records = []
            for row in result:
                records.append({
                    'recname': row[0].strip() if row[0] else '',
                    'recdesc': row[1].strip() if row[1] else '',
                    'parentrecord': row[2].strip() if row[2] else '',
                    'rectype': row[3]
                })
            return jsonify(records)
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/record/<recname>', methods=['GET'])
def get_record_details(recname):
    recname = recname.upper().strip()
    engine = get_db_connection()

    # Query details of fields in the record
    # PeopleSoft field flags: Key flags inside USEEDIT. Typically USEEDIT & 1 or USEEDIT & 2 indicate keys.
    query_str = """
        SELECT A.RECNAME, A.FIELDNAME, A.FIELDNUM, A.USEEDIT, A.EDITTABLE, 
               B.FIELDTYPE, B.LENGTH, B.DECIMALPOS
        FROM PSRECFIELD A
        LEFT JOIN PSDBFIELD B ON A.FIELDNAME = B.FIELDNAME
        WHERE A.RECNAME = :recname
        ORDER BY A.FIELDNUM
    """
    
    try:
        with engine.connect() as conn:
            # Fetch record metadata description
            rec_desc_query = text("SELECT RECDESC, PARENTRECORD FROM PSRECDEFN WHERE RECNAME = :recname")
            desc_res = conn.execute(rec_desc_query, {'recname': recname}).fetchone()
            recdesc = desc_res[0].strip() if desc_res and desc_res[0] else ''
            parentrecord = desc_res[1].strip() if desc_res and desc_res[1] else ''

            result = conn.execute(text(query_str), {'recname': recname})
            fields = []
            for row in result:
                useedit = row[3] or 0
                # In PeopleSoft, key fields are represented by USEEDIT bits:
                # 1 = Key, 2 = Duplicate Key. So (useedit & 1) != 0 or (useedit & 2) != 0 is a key.
                is_key = (useedit & 1) != 0 or (useedit & 2) != 0
                
                # Decode Field Types
                ftype_map = {
                    0: 'Char', 1: 'Long Char', 2: 'Number', 3: 'Signed Number',
                    4: 'Date', 5: 'Time', 6: 'DateTime', 8: 'Image', 9: 'ImageRef'
                }
                ftype_code = row[5]
                field_type_str = ftype_map.get(ftype_code, f'Type {ftype_code}')

                fields.append({
                    'fieldname': row[1].strip() if row[1] else '',
                    'fieldnum': row[2],
                    'is_key': bool(is_key),
                    'useedit': useedit,
                    'edittable': row[4].strip() if row[4] else '',
                    'fieldtype': field_type_str,
                    'length': row[6],
                    'decimalpos': row[7]
                })
            
            return jsonify({
                'recname': recname,
                'recdesc': recdesc,
                'parentrecord': parentrecord,
                'fields': fields
            })
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/relationships', methods=['POST'])
def get_relationships():
    """Finds parent-child and prompt table relationships between a set of given records."""
    data = request.json
    selected_records = [r.upper().strip() for r in data.get('records', [])]
    if not selected_records:
        return jsonify([])

    engine = get_db_connection()
    relationships = []

    # Prepare SQL queries to find links
    # 1. Parent-child links in PSRECDEFN
    parent_child_query = """
        SELECT RECNAME, PARENTRECORD 
        FROM PSRECDEFN 
        WHERE RECNAME IN (:records) AND PARENTRECORD IN (:records) AND PARENTRECORD <> ' ' AND PARENTRECORD IS NOT NULL
    """
    
    # 2. Prompt table edits in PSRECFIELD
    prompt_query = """
        SELECT RECNAME, FIELDNAME, EDITTABLE 
        FROM PSRECFIELD 
        WHERE RECNAME IN (:records) AND EDITTABLE IN (:records) AND EDITTABLE <> ' ' AND EDITTABLE IS NOT NULL
    """

    # For SQL execution with list parameters, SQLAlchemy handles IN bindings differently depending on syntax.
    # We will format the parameters into explicit bind parameters dynamically or handle formatting safely.
    records_tuple = tuple(selected_records)
    
    try:
        with engine.connect() as conn:
            # Fetch parent-child relations
            # If records_tuple is single-element, python tuple formatting is (val,), we need to avoid SQL syntax errors.
            pc_list = []
            for rec in selected_records:
                res = conn.execute(
                    text("SELECT RECNAME, PARENTRECORD FROM PSRECDEFN WHERE RECNAME = :rec AND PARENTRECORD IS NOT NULL AND PARENTRECORD <> ' '"),
                    {'rec': rec}
                ).fetchone()
                if res:
                    child, parent = res[0].strip(), res[1].strip()
                    if parent in selected_records:
                        pc_list.append((child, parent))

            for child, parent in pc_list:
                relationships.append({
                    'source': parent,      # Parent table
                    'target': child,       # Child table
                    'type': 'parent-child',
                    'label': 'Parent-Child',
                    'source_field': 'EMPLID',  # In Peoplesoft, parent keys match child keys
                    'target_field': 'EMPLID'
                })

            # Fetch Prompt table relations
            prompt_list = []
            for rec in selected_records:
                res = conn.execute(
                    text("SELECT RECNAME, FIELDNAME, EDITTABLE FROM PSRECFIELD WHERE RECNAME = :rec AND EDITTABLE IS NOT NULL AND EDITTABLE <> ' '"),
                    {'rec': rec}
                ).fetchall()
                for row in res:
                    source_rec, fieldname, edittable = row[0].strip(), row[1].strip(), row[2].strip()
                    if edittable in selected_records:
                        prompt_list.append((source_rec, fieldname, edittable))

            for source_rec, fieldname, edittable in prompt_list:
                # Relationship direction: the referencing table points to the Prompt table
                # or Prompt table points to Referencing (let's direct it from referencing -> prompt)
                relationships.append({
                    'source': source_rec,
                    'target': edittable,
                    'type': 'prompt-table',
                    'label': f'Prompts on {fieldname}',
                    'source_field': fieldname,
                    'target_field': 'KEY' # Join is on target primary key
                })

            # 3. Share-Key relationships (Logical Joins)
            # Find fields that match between selected tables that are marked as keys
            # (only define this if no explicit parent-child or prompt relation exists between the two tables)
            key_fields_by_table = {}
            for rec in selected_records:
                res = conn.execute(text("""
                    SELECT FIELDNAME FROM PSRECFIELD 
                    WHERE RECNAME = :rec AND (USEEDIT & 1 != 0 OR USEEDIT & 2 != 0)
                """), {'rec': rec}).fetchall()
                key_fields_by_table[rec] = set([row[0].strip() for row in res])

            # Compare tables pairwise for matching keys
            for i in range(len(selected_records)):
                for j in range(i + 1, len(selected_records)):
                    rec1 = selected_records[i]
                    rec2 = selected_records[j]
                    
                    # Skip if parent-child or prompt relationship already exists between these two tables
                    already_linked = False
                    for r in relationships:
                        if (r['source'] == rec1 and r['target'] == rec2) or (r['source'] == rec2 and r['target'] == rec1):
                            already_linked = True
                            break
                    if already_linked:
                        continue

                    common_keys = key_fields_by_table.get(rec1, set()).intersection(key_fields_by_table.get(rec2, set()))
                    # If they share keys, draw a logical key join relationship
                    if common_keys:
                        # Grab one of the matching keys to label the relationship
                        match_field = list(common_keys)[0]
                        relationships.append({
                            'source': rec1,
                            'target': rec2,
                            'type': 'key-join',
                            'label': f'Key Join ({match_field})',
                            'source_field': match_field,
                            'target_field': match_field
                        })

            return jsonify(relationships)
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-sql', methods=['POST'])
def export_sql():
    """Generates standard SQL DDL scripts for selected PeopleSoft records."""
    data = request.json
    selected_records = [r.upper().strip() for r in data.get('records', [])]
    if not selected_records:
        return jsonify({'sql': ''})

    engine = get_db_connection()
    ddl_statements = []

    try:
        with engine.connect() as conn:
            for recname in selected_records:
                # Fetch fields
                query = text("""
                    SELECT A.FIELDNAME, B.FIELDTYPE, B.LENGTH, B.DECIMALPOS, A.USEEDIT
                    FROM PSRECFIELD A
                    LEFT JOIN PSDBFIELD B ON A.FIELDNAME = B.FIELDNAME
                    WHERE A.RECNAME = :recname
                    ORDER BY A.FIELDNUM
                """)
                fields_res = conn.execute(query, {'recname': recname}).fetchall()
                if not fields_res:
                    continue

                field_lines = []
                primary_keys = []
                
                for row in fields_res:
                    fname, ftype_code, flength, fdec, useedit = row[0].strip(), row[1], row[2], row[3], row[4]
                    is_key = (useedit & 1) != 0 or (useedit & 2) != 0
                    
                    # Convert Peoplesoft type to generic SQL type
                    # 0=Char, 1=Long Char, 2=Number, 3=Signed Number, 4=Date, 5=Time, 6=DateTime
                    if ftype_code == 0:
                        sql_type = f"VARCHAR({flength})"
                    elif ftype_code == 1:
                        sql_type = "TEXT"
                    elif ftype_code in (2, 3):
                        if fdec > 0:
                            sql_type = f"DECIMAL({flength}, {fdec})"
                        else:
                            sql_type = f"INT" if flength < 10 else f"BIGINT"
                    elif ftype_code == 4:
                        sql_type = "DATE"
                    elif ftype_code == 5:
                        sql_type = "TIME"
                    elif ftype_code == 6:
                        sql_type = "TIMESTAMP"
                    else:
                        sql_type = "VARCHAR(255)"

                    field_def = f"    {fname} {sql_type}"
                    if is_key:
                        field_def += " NOT NULL"
                        primary_keys.append(fname)
                    
                    field_lines.append(field_def)

                # Add Primary Key constraint
                if primary_keys:
                    field_lines.append(f"    CONSTRAINT PK_PS_{recname} PRIMARY KEY ({', '.join(primary_keys)})")

                ddl = f"CREATE TABLE PS_{recname} (\n" + ",\n".join(field_lines) + "\n);"
                ddl_statements.append(ddl)

            return jsonify({'sql': "\n\n".join(ddl_statements)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize mock db right away
    init_mock_db()
    app.run(host='127.0.0.1', port=5000, debug=True)
