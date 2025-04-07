from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
DB_FILE = os.getenv('DB_FILE')  # Use environment variable with fallback
teacher_secret_key = os.getenv('TEACHER_SECRET_KEY')

# Function to create and connect to the database
def create_connection():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create user table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )''')

    # Create sets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT ''
        )''')

    # Create cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY,
            set_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES sets(id)
        )''')

    # Create quizzes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT ''
        )''')

    # Create questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option1 TEXT NOT NULL,
            option2 TEXT NOT NULL,
            option3 TEXT NOT NULL,
            option4 TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
        )''')

    conn.commit()
    return conn

# Function to create a new user
def create(username, password, role):
    query = "INSERT INTO user VALUES (?, ?, ?)"
    conn = create_connection()
    cur = conn.cursor()
    # Hash the password before storing
    hashed_password = generate_password_hash(password)
    cur.execute(query, (username, hashed_password, role))
    conn.commit()
    conn.close()

# Function to find a user by username
def find_by_username(username):
    query = "SELECT username, password, role FROM user WHERE username = ?"
    conn = create_connection()
    cur = conn.cursor()
    cur.execute(query, (username,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {'username': row[0], 'password': row[1], 'role': row[2]}
    else:
        return None

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def is_strong_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    has_upper = has_special = has_lower = has_digit = False
    special_characters = set("!@#$%^&*(),.?\":{}|<>")

    for char in password:
        if char.isupper():
            has_upper = True
        elif char.islower():
            has_lower = True
        elif char.isdigit():
            has_digit = True
        elif char in special_characters:
            has_special = True

    if not has_upper:
        return False, "Password must contain at least one uppercase letter"
    if not has_lower:
        return False, "Password must contain at least one lowercase letter"
    if not has_digit:
        return False, "Password must contain at least one digit"
    if not has_special:
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

@app.route('/')
def index():
    return render_template('index.html')

# Login route and logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"Received login request with username: {username}")

        user = find_by_username(username)

        if user:
            print(f"User found in database: {user}")
            # Check the hashed password
            if check_password_hash(user['password'], password):
                session['username'] = username
                session['role'] = user['role']
                print("Login successful!")
                return redirect(url_for('main_page'))
            else:
                print("Incorrect password")
        else:
            print("User not found")

        error_message = 'Invalid username or password'
        return render_template('login.html', error_message=error_message)
    else:
        return render_template('login.html')

# User creation route and logic
@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        teacher_pass = request.form.get('teacher_pass')

        if find_by_username(username):
            error_message = 'Username already exists'
            return render_template('create_user.html', error_message=error_message)
        
        checkpassword,error_message=is_strong_password(password)
        if not checkpassword:
            return render_template('create_user.html', error_message=error_message)
        
        if role=='teacher':
            if teacher_pass!=teacher_secret_key:
                error_message = 'Incorrect Teacher Code'
                return render_template('create_user.html', error_message=error_message)
        
        create(username, password, role)
        return redirect(url_for('login'))
    return render_template('create_user.html')

@app.route('/main_page')
def main_page():
    return render_template('main_page.html')

# Flashcard main page route and logic
@app.route('/flashcard_main')
def flashcard_main():
    conn = get_db_connection()
    sets = conn.execute('SELECT * FROM sets').fetchall()
    conn.close()

    username = session.get('username')
    user = find_by_username(username)

    if user and user['role'] == 'teacher':
        can_create_set = True
    else:
        can_create_set = False

    return render_template('flashcard_main.html', sets=sets, can_create_set=can_create_set)

# Route to create a new flashcard set
@app.route('/create_set', methods=('GET', 'POST'))
def create_set():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sets (name, description) VALUES (?, ?)', (name, description))
        set_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return redirect(url_for('add_card_initial', set_id=set_id))
    
    return render_template('create_set.html')

# Route to add an initial card to a set
@app.route('/add_card_initial/<int:set_id>', methods=('GET', 'POST'))
def add_card_initial(set_id):
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO cards (set_id, question, answer) VALUES (?, ?, ?)', (set_id, question, answer))
        conn.commit()
        conn.close()
        
        if 'add_another' in request.form:
            return redirect(url_for('add_card_initial', set_id=set_id))
        else:
            return redirect(url_for('all_sets', set_id=set_id))
    
    return render_template('add_card_initial.html', set_id=set_id)

# Route to display all questions in a set
@app.route('/all_sets/<int:set_id>')
def all_sets(set_id):
    conn = get_db_connection()
    print(set_id)
    set_data = conn.execute('SELECT name, description FROM sets WHERE id = ?', (set_id,)).fetchone()
    cards = conn.execute('SELECT * FROM cards WHERE set_id = ? ORDER BY id', (set_id,)).fetchall()
    print(cards[0])
    conn.close()

    return render_template('all_sets.html', set_name=set_data[0], set_description=set_data[1], cards=cards)

#Route to delete a set
@app.route('/delete_set')
def delete_set():
    conn = get_db_connection()
    sets = conn.execute('SELECT * FROM sets').fetchall()
    conn.close()
    return render_template('delete_set.html', sets=sets)

#logic to delete a set
@app.route('/del_set/<int:set_id>')
def del_set(set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cards WHERE set_id = ?', (set_id,))
    cursor.execute('DELETE FROM sets WHERE id = ?', (set_id,))
    conn.commit()
    conn.close()
    print("deleted set and associated cards")
    return redirect(url_for('flashcard_main'))

@app.route('/edit_set', methods=['GET','POST'])
def edit_set():
    conn = get_db_connection()
    sets = conn.execute('SELECT id, name FROM sets').fetchall()
    conn.close()

    if request.method == 'POST':
        op = request.form['operation']
        set_id = request.form['set_id']

        if (op == 'add'):
            return redirect(url_for('add_card_initial', set_id=set_id))
        elif (op == 'delete'):
            return redirect(url_for('del_card', set_id=set_id))
    
    return render_template('edit_set.html', sets=sets)

@app.route('/del_card/<int:set_id>', methods=('GET', 'POST'))
def del_card(set_id):
    conn = get_db_connection()
    set_name = conn.execute('SELECT name FROM sets WHERE id = ?', (set_id,)).fetchone()['name']
    cards = conn.execute('SELECT * FROM cards WHERE set_id = ?', (set_id,)).fetchall()
    print(set_id)
    print(cards[0]['question'])
    conn.close()

    if request.method == 'POST':
        question_id = request.form['card_id']

        conn = get_db_connection()
        conn.execute('DELETE FROM cards WHERE id = ?', (question_id,))
        conn.commit()
        conn.close()

    return render_template('del_card.html', set_name=set_name, cards=cards)

# Route to view a set of flashcards
@app.route('/view_set/<int:set_id>')
def view_set(set_id):
    conn = get_db_connection()
    set_data = conn.execute('SELECT name, description FROM sets WHERE id = ?', (set_id,)).fetchone()
    cards = conn.execute('SELECT * FROM cards WHERE set_id = ? ORDER BY id', (set_id,)).fetchall()
    conn.close()

    session['current_card'] = 0
    session['review_done'] = False
    session['show_answer'] = False 
    session['set_name'] = set_data['name']
    session['set_description'] = set_data['description']

    if len(cards) > 0:
        first_card = cards[0]
        return render_template('view_set.html', set_name=set_data['name'], set_description=set_data['description'], set_id=set_id, card=first_card)
    else:
        flash('No cards found in this set.')
        return redirect(url_for('flashcard_main'))

# Route to handle next card action
@app.route('/next_card/<int:set_id>', methods=['POST'])
def next_card(set_id):
    if 'current_card' in session:
        current_card = session['current_card']
    else:
        current_card = 0
    
    action = request.form['action']
    conn = get_db_connection()
    cards = conn.execute('SELECT * FROM cards WHERE set_id = ? ORDER BY id', (set_id,)).fetchall()
    conn.close()

    if action == 'show_answer':
        session['show_answer'] = True
    elif action == 'next_card':
        current_card = (current_card + 1)
        session['current_card'] = current_card
        session['show_answer'] = False
    if current_card == len(cards):
        session['review_done'] = True
        print("Review done: True")
    else:
        print(f"Current card: {current_card}, Total cards: {len(cards)}")

    if session['review_done']:
        return redirect(url_for('revision_done'))
    else:
        return render_template('view_set.html', set_id=set_id, set_name=session['set_name'], set_description=session['set_description'], card=cards[current_card], show_answer=session['show_answer'])

@app.route('/revision_done')
def revision_done():
    if 'review_done' in session and session['review_done']:
        flash('Revision Done!')
        return render_template('revision_done.html')
    else:
        return redirect(url_for('flashcard_main'))

# Quiz main page route and logic
@app.route('/quiz_main')
def quiz_main():
    conn = get_db_connection()
    quizzes = conn.execute('SELECT * FROM quizzes').fetchall()
    conn.close()

    username = session.get('username')
    user = find_by_username(username)
    print(user)
    if user and user['role'] == 'teacher':
        can_create_quiz = True
    else:
        can_create_quiz = False

    return render_template('quiz_main.html', quizzes=quizzes, can_create_quiz=can_create_quiz)

# Route to create a new quiz
@app.route('/create_quiz', methods=('GET', 'POST'))
def create_quiz():
    if request.method == 'POST':
        quiz_name = request.form['quiz_name']
        quiz_description = request.form['quiz_description']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO quizzes (name, description) VALUES (?, ?)', (quiz_name, quiz_description))
        quiz_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return redirect(url_for('add_question', quiz_id=quiz_id))
    
    return render_template('create_quiz.html')

# Route to add a question to a quiz
@app.route('/add_question/<int:quiz_id>', methods=('GET', 'POST'))
def add_question(quiz_id):
    if request.method == 'POST':
        question = request.form['question']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        correct_option = request.form['correct_option']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO questions (quiz_id, question, option1, option2, option3, option4, correct_option) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (quiz_id, question, option1, option2, option3, option4, correct_option))
        conn.commit()
        conn.close()
        
        if 'add_another' in request.form:
            return redirect(url_for('add_question', quiz_id=quiz_id))
        else:
            return redirect(url_for('all_questions', quiz_id=quiz_id))
    
    return render_template('add_question.html', quiz_id=quiz_id)

# Route to display all questions in a quiz
@app.route('/all_questions/<int:quiz_id>')
def all_questions(quiz_id):
    conn = get_db_connection()
    quiz_name = conn.execute('SELECT name FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()['name']
    quiz_description = conn.execute('SELECT description FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()['description']
    questions = conn.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz_id,)).fetchall()
    conn.close()

    return render_template('all_questions.html', quiz_name=quiz_name, quiz_description=quiz_description, questions=questions)

#Route to delete a quiz
@app.route('/delete_quiz')
def delete_quiz():
    conn = get_db_connection()
    quizzes = conn.execute('SELECT * FROM quizzes').fetchall()
    conn.close()
    return render_template('delete_quiz.html', quizzes=quizzes)

#Logic to delete a quiz
@app.route('/del_quiz/<int:quiz_id>')
def del_quiz(quiz_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM questions WHERE quiz_id = ?', (quiz_id,))
    cursor.execute('DELETE FROM quizzes WHERE id = ?', (quiz_id,))
    conn.commit()
    conn.close()
    print("deleted quiz and associated questions")
    return redirect(url_for('quiz_main'))

@app.route('/edit_quiz', methods=['GET','POST'])
def edit_quiz():
    conn = get_db_connection()
    quizzes = conn.execute('SELECT id, name FROM quizzes').fetchall()
    conn.close()

    if request.method == 'POST':
        op = request.form['operation']
        quiz_id = request.form['quiz_id']

        if (op == 'add'):
            return redirect(url_for('add_question', quiz_id=quiz_id))
        elif (op == 'delete'):
            return redirect(url_for('del_question', quiz_id=quiz_id))
    
    return render_template('quiz_edit.html', quizzes=quizzes)

@app.route('/del_question/<int:quiz_id>', methods=('GET', 'POST'))
def del_question(quiz_id):
    conn = get_db_connection()
    quiz_name = conn.execute('SELECT name FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()['name']
    questions = conn.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz_id,)).fetchall()
    conn.close()

    if request.method == 'POST':
        question_id = request.form['question_id']

        conn = get_db_connection()
        conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        conn.commit()
        conn.close()

    return render_template('del_question.html', quiz_name=quiz_name, questions=questions)

# Route to start a quiz
@app.route('/quiz/<int:quiz_id>')
def quiz(quiz_id):
    conn = get_db_connection()
    quiz = conn.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()
    questions = conn.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz_id,)).fetchall()
    conn.close()

    session['quiz'] = {'name': quiz[1],'description':quiz[2]}
    session['quiz_id'] = quiz_id
    session['current_question'] = 0
    session['score'] = 0
    session['questions'] = [dict(q) for q in questions]

    return render_template('quiz.html', quiz=quiz, question=session['questions'][0])

# Route to handle the next question in a quiz
@app.route('/next_question', methods=['POST'])
def next_question():
    selected_option = request.form.get('option')
    current_question = session.get('current_question')
    questions = session.get('questions')

    if selected_option == questions[current_question]['correct_option']:
        print('Correct')
        session['score'] += 1
    session['current_question'] += 1
    
    if session['current_question'] >= len(questions):
        return redirect(url_for('quiz_result', quiz_id=session['quiz_id']))

    return render_template('quiz.html', quiz=session['quiz'], question=session['questions'][session['current_question']])

# Route to display quiz result
@app.route('/quiz_result/<int:quiz_id>')
def quiz_result(quiz_id):
    score = session.get('score')
    total_questions = len(session.get('questions'))

    session.pop('quiz_id', None)
    session.pop('current_question', None)
    session.pop('score', None)
    session.pop('questions', None)

    return render_template('quiz_result.html', quiz_id=quiz_id, score=score, total_questions=total_questions)

if __name__ == '__main__':
    app.run(debug=True)
