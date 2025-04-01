import os
import unittest
os.environ['DB_FILE'] = 'test_knowitall.db'

from app import app, create, create_connection

class FlaskTestCase(unittest.TestCase):

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
