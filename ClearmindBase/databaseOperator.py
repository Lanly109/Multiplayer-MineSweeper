import os
from random import randint
import sqlite3
import threading
from .config import DATABASE
from typing import Dict, Optional, List, Any

thread_local = threading.local()

class sqlOperator:
    def __init__(self, database=DATABASE):
        self.__database = database
        if not os.path.exists(self.__database):
            self.__initialize_database()
    
    def __initialize_database(self):
        """首次创建数据库时执行建表语句"""
        try:
            self.active()
            self.__cursor.executescript('''
                CREATE TABLE invitation(
                    userID TEXT PRIMARY KEY,
                    invitationCode TEXT UNIQUE,
                    ifUsed INTEGER DEFAULT 0
                );
                
                CREATE TABLE userInfo(
                    userID TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    passwd TEXT,
                    ifOnline INTEGER DEFAULT 0,
                    clearCount INTEGER DEFAULT 0,
                    boomCount INTEGER DEFAULT 0
                );
            ''')
            self.__connection.commit()
        finally:
            self.inactive()
    
    def active(self):
        # Create connection per thread
        if not hasattr(thread_local, "connection"):
            thread_local.connection = sqlite3.connect(self.__database, check_same_thread=False)
            thread_local.connection.row_factory = sqlite3.Row
            thread_local.cursor = thread_local.connection.cursor()
            thread_local.cursor.execute('PRAGMA foreign_keys = ON')
        self.__connection = thread_local.connection
        self.__cursor = thread_local.cursor

    def inactive(self):
        # Don't close connection immediately, let thread-local handle it
        pass
    

    def select_invitation_userID(self, invitationCode) -> Optional[dict]:
        sql = 'SELECT userID FROM invitation WHERE invitationCode = ?'
        self.__cursor.execute(sql, (invitationCode,))
        ret = self.__cursor.fetchone()
        return dict(ret) if ret else None

    def select_invitation_ifUsed(self, invitationCode) -> int:
        sql = 'SELECT ifUsed FROM invitation WHERE invitationCode = ?'
        self.__cursor.execute(sql, (invitationCode,))
        ret = self.__cursor.fetchone()
        return ret['ifUsed'] if ret else -1

    def update_invitation_ifUsed(self, invitationCode, ifUsed) -> int:
        sql = 'UPDATE invitation SET ifUsed = ? WHERE invitationCode = ?'
        self.__cursor.execute(sql, (ifUsed, invitationCode))
        self.__connection.commit()
        return self.__cursor.rowcount

    def select_userInfo_uAp(self, userID) -> Optional[dict]:
        sql = 'SELECT username,passwd FROM userInfo WHERE userID = ?'
        self.__cursor.execute(sql, (userID,))
        ret = self.__cursor.fetchone()
        return dict(ret) if ret else None

    def update_userInfo_uAp(self, userID, dir) -> int:
        sql = '''UPDATE userInfo 
                SET username = ?, passwd = ? 
                WHERE userID = ?'''
        params = (dir['username'], dir['passwd'], userID)
        self.__cursor.execute(sql, params)
        self.__connection.commit()
        return self.__cursor.rowcount

    def insert_serInfo_uAp(self, dir) -> int:
        sql = '''INSERT INTO userInfo 
                (userID, username, passwd, ifOnline, clearCount, boomCount) 
                VALUES (?, ?, ?, 0, 0, 0)'''
        params = (dir['userID'], dir['username'], dir['passwd'])
        self.__cursor.execute(sql, params)
        self.__connection.commit()
        return self.__cursor.rowcount

    def select_userInfo_ifOnline(self, username) -> int:
        sql = 'SELECT ifOnline FROM userInfo WHERE username = ?'
        self.__cursor.execute(sql, (username,))
        ret = self.__cursor.fetchone()
        return ret['ifOnline'] if ret else -4

    def update_userInfo_ifOnline(self, username, ifOnline) -> int:
        sql = 'UPDATE userInfo SET ifOnline = ? WHERE username = ?'
        self.__cursor.execute(sql, (ifOnline, username))
        self.__connection.commit()
        return self.__cursor.rowcount

    def select_userInfo_clearCount(self, username) -> int:
        sql = 'SELECT clearCount FROM userInfo WHERE username = ?'
        self.__cursor.execute(sql, (username,))
        ret = self.__cursor.fetchone()
        return ret['clearCount'] if ret else -4

    def update_userInfo_clearCount(self, username, clearCount) -> int:
        sql = 'UPDATE userInfo SET clearCount = ? WHERE username = ?'
        self.__cursor.execute(sql, (clearCount, username))
        self.__connection.commit()
        return self.__cursor.rowcount

    def select_userInfo_boomCount(self, username) -> int:
        sql = 'SELECT boomCount FROM userInfo WHERE username = ?'
        self.__cursor.execute(sql, (username,))
        ret = self.__cursor.fetchone()
        return ret['boomCount'] if ret else -4

    def update_userInfo_boomCount(self, username, boomCount):
        sql = 'UPDATE userInfo SET boomCount = ? WHERE username = ?'
        self.__cursor.execute(sql, (boomCount, username))
        self.__connection.commit()
        return self.__cursor.rowcount

    def add_invite_code(self, number: int) -> None:
        sql = 'SELECT MAX(rowid) FROM invitation'
        self.__cursor.execute(sql)
        max_id = self.__cursor.fetchone()[0] or 0

        for _ in range(number):
            max_id += 1
            code = f"{max_id:05d}-{randint(10000,99999)}"
            sql = 'INSERT INTO invitation VALUES (?, ?, 0)'
            self.__cursor.execute(sql, (max_id, code))
        self.__connection.commit()

    def get_invite_code(self) -> list:
        sql = 'SELECT invitationCode AS code FROM invitation WHERE ifUsed = 0'
        self.__cursor.execute(sql)
        return [dict(row) for row in self.__cursor.fetchall()]

    def select_by_user(self, username: str) -> Optional[dict]:
        sql = 'SELECT * FROM userInfo WHERE username = ?'
        self.__cursor.execute(sql, (username,))
        ret = self.__cursor.fetchone()
        return dict(ret) if ret else None

    def register(self, invitecode: str, username: str, password: str) -> bool:
        if self.select_by_user(username):
            return False

        sql = '''SELECT userID, ifUsed FROM invitation 
                WHERE invitationCode = ?'''
        self.__cursor.execute(sql, (invitecode,))
        data = self.__cursor.fetchone()
        
        if not data or data['ifUsed'] != 0:
            return False

        try:
            sql = '''INSERT INTO userInfo 
                    (userID, username, passwd, ifOnline, clearCount, boomCount) 
                    VALUES (?, ?, ?, 0, 0, 0)'''
            self.__cursor.execute(sql, (data['userID'], username, password))
            self.update_invitation_ifUsed(invitecode, 1)
            return True
        except sqlite3.IntegrityError:
            return False

    def get_totalRank_data(self) -> List[dict]:
        sql = 'SELECT username, clearCount, boomCount FROM userInfo'
        self.__cursor.execute(sql)
        return [dict(row) for row in self.__cursor.fetchall()]

    def test_select(self) -> list:
        sql = 'SELECT userID AS uid, invitationCode AS code FROM invitation'
        self.__cursor.execute(sql)
        return [dict(row) for row in self.__cursor.fetchall()]