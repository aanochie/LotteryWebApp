import csv
from sqlalchemy import create_engine, MetaData, Table
#from app import db

engine = create_engine('sqlite:///lottery.db')
connection = engine.connect()

# for this to work pip install sqlalchemy==1.4.4
# metadata = MetaData(bind=engine)
metadata = MetaData()
metadata.reflect(bind=engine)
print(metadata.tables.keys())
table = Table('users', metadata, autoload_with=engine)

query = connection.execute(table.select())
rows = query.fetchall()

with open('table.csv', 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    # Write header
    csv_writer.writerow([column.name for column in table.columns])
    # Write rows
    csv_writer.writerows(rows)
connection.close()
