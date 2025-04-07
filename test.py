import os
os.environ['DB_FILE'] = 'test_knowitall.db'

import unittest
import sqlite3
from app import is_strong_password, create, find_by_username, create_connection, get_db_connection, app


class UnitTests(unittest.TestCase):
    def setUp(self):
        if os.path.exists('test_knowitall.db'):
            os.remove('test_knowitall.db')
        self.conn = create_connection()
        
    def tearDown(self):
        self.conn.close()
        if os.path.exists('test_knowitall.db'):
            os.remove('test_knowitall.db')
            
    def test_create_user(self):

        create('testuser', 'Test123!@#', 'student')
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT username, role FROM user WHERE username = ?', ('testuser',))
        result = cursor.fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'testuser')
        self.assertEqual(result[1], 'student')
        
    def test_find_by_username_existing(self):
        create('finduser', 'Test123!@#', 'teacher')
        
        user = find_by_username('finduser')
        
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'finduser')
        self.assertEqual(user['role'], 'teacher')
        
    def test_find_by_username_nonexistent(self):
        user = find_by_username('nonexistentuser')
        self.assertIsNone(user)
        
    def test_database_connection(self):
        conn = get_db_connection()
        self.assertIsInstance(conn, sqlite3.Connection)
        self.assertEqual(conn.row_factory, sqlite3.Row)
        conn.close()

    def test_valid_strong_password(self):
        password = "Test123!@#"
        is_valid, message = is_strong_password(password)
        self.assertTrue(is_valid)
        self.assertEqual(message, "Password is strong")

    def test_password_too_short(self):
        password = "Test123"
        is_valid, message = is_strong_password(password)
        self.assertFalse(is_valid)
        self.assertEqual(message, "Password must be at least 8 characters long")

    def test_password_no_uppercase(self):
        password = "test123!@#"
        is_valid, message = is_strong_password(password)
        self.assertFalse(is_valid)
        self.assertEqual(message, "Password must contain at least one uppercase letter")

    def test_password_no_lowercase(self):
        password = "TEST123!@#"
        is_valid, message = is_strong_password(password)
        self.assertFalse(is_valid)
        self.assertEqual(message, "Password must contain at least one lowercase letter")

    def test_password_no_digit(self):
        password = "TestTest!@#"
        is_valid, message = is_strong_password(password)
        self.assertFalse(is_valid)
        self.assertEqual(message, "Password must contain at least one digit")

    def test_password_no_special_char(self):
        password = "TestTest123"
        is_valid, message = is_strong_password(password)
        self.assertFalse(is_valid)
        self.assertEqual(message, "Password must contain at least one special character")


class IntegrationTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        with app.app_context():
            conn = create_connection()
            conn.execute('DELETE FROM user') 
            conn.commit()
            conn.close()

    def test_successful_registration(self):
        response = self.app.post('/create_user', data=dict(
            username='testuser',
            password='StrongPass1!',
            role='student'
        ), follow_redirects=True)
        self.assertIn(b'Login', response.data)

    def test_registration_existing_username(self):
        # First, create a user
        create('existinguser', 'StrongPass1!', 'student')
        # Try to register the same user again
        response = self.app.post('/create_user', data=dict(
            username='existinguser',
            password='StrongPass1!',
            role='student'
        ), follow_redirects=True)
        self.assertIn(b'Username already exists', response.data)

    def test_successful_login(self):
        # First, create a user
        create('loginuser', 'StrongPass1!', 'student')
        # Attempt to login
        response = self.app.post('/login', data=dict(
            username='loginuser',
            password='StrongPass1!'
        ), follow_redirects=True)
        self.assertIn(b'Welcome to KnowItAll!', response.data)

    def test_login_non_existent_user(self):
        response = self.app.post('/login', data=dict(
            username='nonexistentuser',
            password='StrongPass1!'
        ), follow_redirects=True)
        self.assertIn(b'Invalid username or password', response.data)

if __name__ == '__main__':
    unittest.main()
