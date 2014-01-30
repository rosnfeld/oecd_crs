"""
For building PostgreSQL database tables to house CRS data for the web app.
"""

import psycopg2
import os
import pandas as pd
import StringIO

# somewhat different than what is in models.py
CODE_TABLES = ['donor', 'agency', 'recipient', 'region', 'incomegroup', 'flow', 'purpose', 'sector', 'channel']

# list of (column name, postgres type) tuples for the columns in the CRS data
CRS_COLUMN_SPEC = [
    ('Year', 'integer'),
    ('donorcode', 'integer'),
    ('agencycode', 'integer'),
    ('crsid', 'varchar (63)'),
    ('projectnumber', 'varchar (63)'),
    ('initialreport', 'integer'),
    ('recipientcode', 'integer'),
    ('regioncode', 'integer'),
    ('incomegroupcode', 'integer'),
    ('flowcode', 'integer'),
    ('bi_multi', 'integer'),
    ('category', 'integer'),
    ('finance_t', 'integer'),
    ('aid_t', 'varchar (63)'),
    ('usd_commitment', 'double precision'),
    ('usd_disbursement', 'double precision'),
    ('usd_received', 'double precision'),
    ('usd_commitment_defl', 'double precision'),
    ('usd_disbursement_defl', 'double precision'),
    ('usd_received_defl', 'double precision'),
    ('usd_adjustment', 'double precision'),
    ('usd_adjustment_defl', 'double precision'),
    ('usd_amountuntied', 'double precision'),
    ('usd_amountpartialtied', 'double precision'),
    ('usd_amounttied', 'double precision'),
    ('usd_amountuntied_defl', 'double precision'),
    ('usd_amountpartialtied_defl', 'double precision'),
    ('usd_amounttied_defl', 'double precision'),
    ('usd_IRTC', 'double precision'),
    ('usd_expert_commitment', 'double precision'),
    ('usd_expert_extended', 'double precision'),
    ('usd_export_credit', 'double precision'),
    ('currencycode', 'integer'),
    ('commitment_national', 'double precision'),
    ('disbursement_national', 'double precision'),
    ('shortdescription', 'text'),
    ('projecttitle', 'text'),
    ('purposecode', 'integer'),
    ('sectorcode', 'integer'),
    ('channelcode', 'double precision'),
    ('channelreportedname', 'text'),
    ('geography', 'text'),
    ('expectedstartdate', 'varchar (63)'),
    ('completiondate', 'varchar (63)'),
    ('longdescription', 'text'),
    ('gender', 'double precision'),
    ('trade', 'double precision'),
    ('FTC', 'double precision'),
    ('PBA', 'double precision')
]


def get_db_connection(host, database, user, password):
    return psycopg2.connect(host=host, database=database, user=user, password=password)


# duplicated with query_processor.py
def get_all_name_code_pairs(dataframe, filter_type):
    """
    Returns a dataframe containing ___code/___name pairs.
    """
    code_column = filter_type + 'code'
    name_column = filter_type + 'name'

    rows = dataframe[[code_column, name_column]].drop_duplicates()

    # filter out missing codes (can happen for channel), and missing values will mean that pandas will have
    # interpreted code column as float (so that it can use NaN), need to set as int
    rows = rows.dropna()
    rows[code_column] = rows[code_column].astype(int)

    rows = rows.sort(name_column)

    return rows.rename(columns={code_column: 'code', name_column: 'name'})


def build_code_tables(cursor, dataframe):
    for filter_type in CODE_TABLES:
        table_name = filter_type
        rows = get_all_name_code_pairs(dataframe, filter_type)

        # these are the database table names, not the pandas dataframe column names
        code_column = filter_type + 'code'
        name_column = filter_type + 'name'

        # create table and populate it
        create_template = 'CREATE TABLE {table_name} ({code_column} integer primary key, {name_column} varchar(127));'
        create_sql = create_template.format(table_name=table_name, code_column=code_column, name_column=name_column)

        cursor.execute(create_sql)

        for i, row in rows.iterrows():
            insert_sql = "INSERT INTO {table_name} VALUES (%(code)s, %(name)s);".format(table_name=table_name)
            cursor.execute(insert_sql, {'code': row['code'], 'name': row['name']})


def create_crs_table(cursor):
    sql = 'CREATE TABLE crs ('
    column_spec_list = [column_name + ' ' + column_type for column_name, column_type in CRS_COLUMN_SPEC]
    sql += ','.join(column_spec_list)
    sql += ');'
    cursor.execute(sql)


def populate_crs_table(cursor, dataframe):
    byte_buffer = StringIO.StringIO()
    columns_of_interest = [column_name for column_name, column_type in CRS_COLUMN_SPEC]
    dataframe[columns_of_interest].to_csv(byte_buffer, header=False, index=False)
    byte_buffer.seek(0)  # rewind to beginning of the buffer
    cursor.copy_expert("COPY crs FROM STDIN WITH CSV", byte_buffer)


if __name__ == "__main__":
    host = os.environ['POSTGRES_HOST']
    database = os.environ['POSTGRES_DB']
    user = os.environ['POSTGRES_USER']
    password = os.environ['POSTGRES_PASSWORD']

    connection = get_db_connection(host, database, user, password)
    cursor = connection.cursor()

    # dataframe = pd.read_pickle('/home/andrew/oecd/crs/processed/2014-01-30/all_data.pkl')
    dataframe = pd.read_pickle('/home/andrew/oecd/crs/processed/2014-01-30/filtered.pkl')

    # build_code_tables(cursor, dataframe)

    create_crs_table(cursor)
    populate_crs_table(cursor, dataframe)

    connection.commit()
    cursor.close()
    connection.close()
