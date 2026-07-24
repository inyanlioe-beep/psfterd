#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PeopleSoft Database Schema Extractor
This script runs on a PeopleSoft database server to extract table structures 
(metadata from PSRECDEFN, PSRECFIELD, and PSDBFIELD) into a JSON file, 
which can then be uploaded to the PeopleSoft ERD Explorer.
"""

import os
import sys
import json
import datetime

# Helper to print colored text in CLI (ansi color codes)
def print_success(msg):
    print(f"\033[92m[SUCCESS] {msg}\033[0m")

def print_info(msg):
    print(f"\033[94m[INFO] {msg}\033[0m")

def print_warning(msg):
    print(f"\033[93m[WARNING] {msg}\033[0m")

def print_error(msg):
    print(f"\033[91m[ERROR] {msg}\033[0m", file=sys.stderr)

# Initialize standard inputs for terminal compatibility
try:
    import readline  # improves command-line input history/editing on unix
except ImportError:
    pass

class PSExtractor:
    def __init__(self):
        self.conn = None
        self.dialect = None
        self.cursor = None

    def connect_sqlite(self, db_path):
        import sqlite3
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database mock SQLite tidak ditemukan di: {db_path}")
        self.conn = sqlite3.connect(db_path)
        self.dialect = 'sqlite'
        self.cursor = self.conn.cursor()
        print_success(f"Terhubung ke mock database SQLite: {db_path}")

    def connect_oracle(self, host, port, service_name, username, password):
        try:
            import oracledb
            # Enable thin mode explicitly
            oracledb.init_oracle_client()
        except Exception:
            pass # fallback to thin mode default in newer versions or use cx_Oracle

        try:
            import oracledb as db_driver
        except ImportError:
            try:
                import cx_Oracle as db_driver
            except ImportError:
                raise ImportError("Driver Oracle ('oracledb' atau 'cx_Oracle') tidak terpasang. Jalankan: pip install oracledb")

        dsn = db_driver.makedsn(host, port, service_name=service_name)
        self.conn = db_driver.connect(user=username, password=password, dsn=dsn)
        self.dialect = 'oracle'
        self.cursor = self.conn.cursor()
        print_success(f"Terhubung ke Oracle Database di {host}:{port}/{service_name}")

    def connect_mssql(self, host, port, db_name, username, password):
        try:
            import pyodbc
        except ImportError:
            raise ImportError("Driver MSSQL 'pyodbc' tidak terpasang. Jalankan: pip install pyodbc")
        
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={host},{port};DATABASE={db_name};UID={username};PWD={password}"
        self.conn = pyodbc.connect(conn_str)
        self.dialect = 'mssql'
        self.cursor = self.conn.cursor()
        print_success(f"Terhubung ke MS SQL Server di {host}:{port}/{db_name}")

    def connect_postgres(self, host, port, db_name, username, password):
        try:
            import psycopg2
        except ImportError:
            raise ImportError("Driver PostgreSQL 'psycopg2' tidak terpasang. Jalankan: pip install psycopg2-binary")

        self.conn = psycopg2.connect(host=host, port=port, database=db_name, user=username, password=password)
        self.dialect = 'postgresql'
        self.cursor = self.conn.cursor()
        print_success(f"Terhubung ke PostgreSQL di {host}:{port}/{db_name}")

    def execute_query(self, sql, params=None):
        """Execute database queries in a cross-platform safe way."""
        if not self.cursor:
            raise ValueError("Koneksi database belum diinisialisasi.")

        # Adapt named parameters (:param) for different dialects if needed
        # SQLite, Oracle use :name. PostgreSQL uses %s or %(name)s. MSSQL uses ? or :name.
        if self.dialect == 'postgresql':
            # Convert :name to %(name)s
            import re
            sql_postgres = re.sub(r':([a-zA-Z0-9_]+)', r'%(\1)s', sql)
            self.cursor.execute(sql_postgres, params or {})
        else:
            self.cursor.execute(sql, params or {})
        
        return self.cursor.fetchall()

    def search_records(self, search_pattern):
        """Search matching PeopleSoft records from PSRECDEFN."""
        search_pattern = search_pattern.upper().strip()
        # Clean wildcards
        if not search_pattern.startswith('%') and not search_pattern.endswith('%'):
            search_pattern = f"%{search_pattern}%"

        # Query to fetch record names
        # RECTYPE = 0 means SQL Tables
        sql = """
            SELECT RECNAME, RECDESCR, PARENTRECNAME, RECTYPE 
            FROM PSRECDEFN 
            WHERE RECTYPE = 0 AND RECNAME LIKE :search 
            ORDER BY RECNAME ASC
        """
        
        # SQLite doesn't strictly require UPPER with LIKE, but PeopleSoft is typically case-insensitive or stored UPPER
        try:
            rows = self.execute_query(sql, {'search': search_pattern})
            return [
                {
                    'recname': r[0].strip() if r[0] else '',
                    'recdesc': r[1].strip() if r[1] else '',
                    'parentrecord': r[2].strip() if r[2] else '',
                    'rectype': r[3]
                }
                for r in rows
            ]
        except Exception as e:
            print_error(f"Gagal mencari record: {str(e)}")
            return []

    def get_record_fields(self, recname):
        """Fetch columns/fields for a specific PeopleSoft record."""
        recname = recname.upper().strip()
        sql = """
            SELECT A.RECNAME, A.FIELDNAME, A.FIELDNUM, A.USEEDIT, A.EDITTABLE, 
                   B.FIELDTYPE, B.LENGTH, B.DECIMALPOS
            FROM PSRECFIELD A
            LEFT JOIN PSDBFIELD B ON A.FIELDNAME = B.FIELDNAME
            WHERE A.RECNAME = :recname
            ORDER BY A.FIELDNUM
        """
        
        try:
            rows = self.execute_query(sql, {'recname': recname})
            fields = []
            
            ftype_map = {
                0: 'Char', 1: 'Long Char', 2: 'Number', 3: 'Signed Number',
                4: 'Date', 5: 'Time', 6: 'DateTime', 8: 'Image', 9: 'ImageRef'
            }
            
            for row in rows:
                useedit = row[3] or 0
                is_key = (useedit & 1) != 0 or (useedit & 2) != 0
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
            return fields
        except Exception as e:
            print_error(f"Gagal mengambil field untuk {recname}: {str(e)}")
            return []

    def close(self):
        if self.conn:
            self.conn.close()

def main():
    print("=" * 60)
    print("      PEOPLESOFT DATABASE SCHEMA EXTRACTOR FOR ERD VISUALIZER")
    print("=" * 60)
    print()

    extractor = PSExtractor()
    
    # 1. Connection Wizard
    print("Langkah 1: Hubungkan ke Database PeopleSoft")
    print("-" * 45)
    print("1. Oracle Database (Standard PeopleSoft)")
    print("2. Microsoft SQL Server")
    print("3. PostgreSQL")
    print("4. SQLite Mock Database (Untuk Pengujian Lokal)")
    print()
    
    db_choice = input("Pilih tipe database [1-4]: ").strip()
    
    try:
        if db_choice == '4':
            # Local testing mock db
            # Detect mock db path
            default_mock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'peoplesoft_mock.db')
            mock_path = input(f"Masukkan path file SQLite [{default_mock_path}]: ").strip() or default_mock_path
            extractor.connect_sqlite(mock_path)
            
        elif db_choice in ('1', '2', '3'):
            host = input("Host / IP Address [localhost]: ").strip() or 'localhost'
            
            # Default ports
            default_port = '1521' if db_choice == '1' else ('1433' if db_choice == '2' else '5432')
            port = input(f"Port [{default_port}]: ").strip() or default_port
            
            db_label = "Service Name / SID" if db_choice == '1' else "Nama Database"
            db_name = input(f"{db_label}: ").strip()
            if not db_name:
                print_error("Nama database/service name wajib diisi.")
                return
                
            username = input("Username [SYSADM]: ").strip() or 'SYSADM'
            password = input("Password: ").strip()
            
            if db_choice == '1':
                extractor.connect_oracle(host, int(port), db_name, username, password)
            elif db_choice == '2':
                extractor.connect_mssql(host, int(port), db_name, username, password)
            elif db_choice == '3':
                extractor.connect_postgres(host, int(port), db_name, username, password)
        else:
            print_error("Pilihan tidak valid. Keluar.")
            return
            
    except Exception as e:
        print_error(f"Koneksi gagal: {str(e)}")
        return

    # Verify connection works and metadata table is present
    try:
        extractor.execute_query("SELECT COUNT(*) FROM PSRECDEFN")
    except Exception as e:
        print_warning("Koneksi berhasil tetapi tabel 'PSRECDEFN' tidak ditemukan.")
        print_warning("Apakah Anda yakin ini adalah schema database PeopleSoft yang valid?")
        cont = input("Tetap lanjutkan pencarian? (y/n): ").strip().lower()
        if cont != 'y':
            extractor.close()
            return

    # 2. Interactive Selection Loop
    print("\nLangkah 2: Cari dan Pilih Record / Tabel yang Ingin Diekstrak")
    print("-" * 60)
    
    selected_records = {}  # dict of recname -> record_meta

    while True:
        search_query = input("\nMasukkan kata kunci pencarian (contoh: JOB, PERSONAL, NAMES) atau enter untuk selesai: ").strip()
        
        if not search_query:
            if not selected_records:
                print_warning("Belum ada tabel yang dipilih.")
                cont = input("Apakah Anda ingin keluar tanpa mengekstrak data? (y/n): ").strip().lower()
                if cont == 'y':
                    extractor.close()
                    return
                continue
            else:
                # User finished searching and selecting
                break
                
        # Search DB
        print_info(f"Mencari tabel dengan kata kunci '{search_query.upper()}'...")
        results = extractor.search_records(search_query)
        
        if not results:
            print_warning(f"Tidak ada tabel yang cocok dengan '{search_query.upper()}'.")
            continue
            
        # Display results
        print("\nHasil Pencarian:")
        print(f"{'No.':<5} | {'Nama Record':<25} | {'Deskripsi':<30}")
        print("-" * 70)
        for idx, rec in enumerate(results, start=1):
            desc = rec['recdesc'] if rec['recdesc'] else "(Tidak ada deskripsi)"
            # Truncate desc if too long for screen
            if len(desc) > 35:
                desc = desc[:32] + "..."
            print(f"{idx:<5} | {rec['recname']:<25} | {desc:<30}")
            
        print("-" * 70)
        print("Petunjuk Pemilihan:")
        print(" - Masukkan angka indeks dipisah koma (contoh: 1, 3, 5)")
        print(" - Masukkan rentang indeks (contoh: 1-5)")
        print(" - Ketik 'all' untuk memilih seluruh hasil pencarian")
        print(" - Tekan ENTER langsung tanpa mengisi untuk membatalkan dan mencari kata kunci lain")
        
        selection_input = input("\nPilihan Anda: ").strip()
        if not selection_input:
            continue
            
        chosen_indices = []
        if selection_input.lower() == 'all':
            chosen_indices = list(range(1, len(results) + 1))
        elif '-' in selection_input:
            try:
                start_str, end_str = selection_input.split('-')
                start = int(start_str.strip())
                end = int(end_str.strip())
                chosen_indices = list(range(start, end + 1))
            except ValueError:
                print_error("Format rentang tidak valid (contoh yang benar: 1-5).")
                continue
        else:
            # Comma separated
            try:
                chosen_indices = [int(x.strip()) for x in selection_input.split(',') if x.strip()]
            except ValueError:
                print_error("Format pemilihan tidak valid (contoh yang benar: 1, 3, 5).")
                continue
                
        # Add to selected dictionary
        added_count = 0
        for idx in chosen_indices:
            if 1 <= idx <= len(results):
                rec = results[idx - 1]
                rec_name = rec['recname']
                if rec_name not in selected_records:
                    selected_records[rec_name] = rec
                    added_count += 1
                    
        print_success(f"Berhasil menambahkan {added_count} tabel ke dalam daftar ekstraksi.")
        print(f"Total tabel terpilih saat ini: {len(selected_records)} tabel.")
        print("Daftar tabel saat ini:", ", ".join(selected_records.keys()))

    # 3. Fetching Column Details
    print(f"\nLangkah 3: Mengekstrak detail kolom untuk {len(selected_records)} tabel...")
    print("-" * 60)
    
    extracted_data = {
        'source': 'PeopleSoft Database Extractor',
        'extracted_at': datetime.datetime.now().isoformat(),
        'db_dialect': extractor.dialect,
        'records': []
    }
    
    for i, (recname, meta) in enumerate(selected_records.items(), start=1):
        print(f"[{i}/{len(selected_records)}] Mengekstrak metadata untuk {recname}...")
        fields = extractor.get_record_fields(recname)
        
        record_entry = {
            'recname': recname,
            'recdesc': meta['recdesc'],
            'parentrecord': meta['parentrecord'],
            'fields': fields
        }
        extracted_data['records'].append(record_entry)

    # 4. Save JSON to File
    print("\nLangkah 4: Simpan Hasil Ekstraksi ke File JSON")
    print("-" * 60)
    
    default_filename = "peoplesoft_schema.json"
    filename = input(f"Masukkan nama file output [{default_filename}]: ").strip() or default_filename
    if not filename.endswith('.json'):
        filename += '.json'
        
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        print_success(f"Ekstraksi selesai! Data berhasil disimpan di: {os.path.abspath(filename)}")
        print_info("Silakan unggah file ini ke aplikasi PeopleSoft ERD Explorer Anda.")
    except Exception as e:
        print_error(f"Gagal menulis file: {str(e)}")
        
    extractor.close()
    print("\nTerima kasih telah menggunakan PeopleSoft Schema Extractor CLI!")

if __name__ == '__main__':
    # Enable terminal ANSI color support on Windows
    if sys.platform == 'win32':
        os.system('color')
    main()
