import csv
from sqlalchemy import create_engine, MetaData, Table

# connects to engine given database URI
engine = create_engine('sqlite:///instance/lottery.db')
connection = engine.connect()
# Used to see what tables are in the database
metadata = MetaData()
metadata.reflect(engine)
print(metadata.tables.keys())
# Selects desired table by name and stores it into the variable
table = Table('users', metadata, autoload=True, autoload_with=engine)

query = connection.execute(table.select())
rows = query.fetchall()
with open('table.csv', 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    # Write header
    csv_writer.writerow([column.name for column in table.columns])
    # Write rows
    csv_writer.writerows(rows)
connection.close()
