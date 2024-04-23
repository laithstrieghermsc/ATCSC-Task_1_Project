import sqlite3
import os

class Database:
    sqliteConnection = None

    def __init__(self, name):
        self.name = name
        if not os.path.exists(f"{name}.db"):
            self._init_database()

    def _init_database(self):
        sqliteConnection = sqlite3.connect(self.name)
        sqliteConnection.execute(str("CREATE TABLE orders ("+
                                     "id INTEGER PRIMARY KEY AUTOINCREMENT,"+
                                     "orderData TEXT NOT NULL,"+
                                     "order_fee REAL DEFAULT 0,"+
                                     "delivery_cost REAL DEFAULT 0,"+
                                     "customerID INTEGER DEFAULT 0,"+
                                     "order_time_epoch INTEGER DEFAULT 0"+
                                     ");"))
        sqliteConnection.execute(str("CREATE TABLE customers (" +
                                     "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                                     "customerID INTEGER DEFAULT 0," +
                                     "name TEXT NOT NULL," +
                                     "email TEXT NOT NULL," +
                                     "phone TEXT NOT NULL," +
                                     "loyalty_level INTEGER DEFAULT 1" +
                                     ");"))

class order:
    statement



if __name__ == "__main__":
    # Initiate sqllite.db
    Database("sqllite.db")