from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
import io

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==================== DATABASE MODELS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'student'
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='student', uselist=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(50), nullable=False)

class Marks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    total_marks = db.Column(db.Float, nullable=False, default=100)
    semester = db.Column(db.Integer, nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = db.relationship('Student', backref='marks')
    subject = db.relationship('Subject', backref='marks')

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    total_marks_obtained = db.Column(db.Float, nullable=False)
    total_maximum_marks = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    gpa = db.Column(db.Float, nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(2), nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', backref='results')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== HELPER FUNCTIONS ====================

def calculate_grade(marks, total):
    percentage = (marks / total) * 100
    if percentage >= 90:
        return 'A', 4.0
    elif percentage >= 80:
        return 'B', 3.0
    elif percentage >= 70:
        return 'C', 2.0
    elif percentage >= 60:
        return 'D', 1.0
    else:
        return 'F', 0.0

def calculate_gpa(marks_list):
    if not marks_list:
        return 0.0
    total_grade_points = 0
    total_credits = 0
    for mark in marks_list:
        grade, grade_point = calculate_grade(mark.marks_obtained, mark.total_marks)
        subject = mark.subject
        if subject:
            total_grade_points += grade_point * subject.credits
            total_credits += subject.credits
    if total_credits == 0:
        return 0.0
    return round(total_grade_points / total_credits, 2)

def calculate_cgpa(student_id):
    results = Result.query.filter_by(student_id=student_id).all()
    if not results:
        return 0.0
    total_gpa = sum(result.gpa for result in results)
    return round(total_gpa / len(results), 2)

# ==================== ROUTES ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        roll_number = request.form.get('roll_number')
        name = request.form.get('name')
        email = request.form.get('email')
        semester = request.form.get('semester')
        department = request.form.get('department')
        academic_year = request.form.get('academic_year')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered', 'error')
            return redirect(url_for('register'))
        
        # Create student
        student = Student(
            roll_number=roll_number,
            name=name,
            email=email,
            semester=int(semester),
            department=department,
            academic_year=academic_year
        )
        db.session.add(student)
        db.session.commit()
        
        # Create user
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='student',
            student_id=student.id
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    total_students = Student.query.count()
    total_subjects = Subject.query.count()
    total_results = Result.query.count()
    published_results = Result.query.filter_by(is_published=True).count()
    
    return render_template('admin/dashboard.html', 
                         total_students=total_students,
                         total_subjects=total_subjects,
                         total_results=total_results,
                         published_results=published_results)

@app.route('/admin/students')
@login_required
def manage_students():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    students = Student.query.all()
    return render_template('admin/manage_students.html', students=students)

@app.route('/admin/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        roll_number = request.form.get('roll_number')
        name = request.form.get('name')
        email = request.form.get('email')
        semester = request.form.get('semester')
        department = request.form.get('department')
        academic_year = request.form.get('academic_year')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already exists', 'error')
            return redirect(url_for('add_student'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('add_student'))
        
        student = Student(
            roll_number=roll_number,
            name=name,
            email=email,
            semester=int(semester),
            department=department,
            academic_year=academic_year
        )
        db.session.add(student)
        db.session.commit()
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='student',
            student_id=student.id
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Student added successfully!', 'success')
        return redirect(url_for('manage_students'))
    
    return render_template('admin/add_student.html')

@app.route('/admin/student/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    student = Student.query.get_or_404(student_id)
    
    if request.method == 'POST':
        student.name = request.form.get('name')
        student.email = request.form.get('email')
        student.semester = int(request.form.get('semester'))
        student.department = request.form.get('department')
        student.academic_year = request.form.get('academic_year')
        
        db.session.commit()
        flash('Student updated successfully!', 'success')
        return redirect(url_for('manage_students'))
    
    return render_template('admin/add_student.html', student=student, edit=True)

@app.route('/admin/student/delete/<int:student_id>')
@login_required
def delete_student(student_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    student = Student.query.get_or_404(student_id)
    user = User.query.filter_by(student_id=student_id).first()
    
    if user:
        db.session.delete(user)
    db.session.delete(student)
    db.session.commit()
    
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('manage_students'))

@app.route('/admin/subjects')
@login_required
def manage_subjects():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    subjects = Subject.query.all()
    return render_template('admin/manage_subjects.html', subjects=subjects)

@app.route('/admin/subject/add', methods=['GET', 'POST'])
@login_required
def add_subject():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        name = request.form.get('name')
        credits = request.form.get('credits')
        semester = request.form.get('semester')
        department = request.form.get('department')
        
        if Subject.query.filter_by(code=code).first():
            flash('Subject code already exists', 'error')
            return redirect(url_for('add_subject'))
        
        subject = Subject(
            code=code,
            name=name,
            credits=int(credits),
            semester=int(semester),
            department=department
        )
        db.session.add(subject)
        db.session.commit()
        
        flash('Subject added successfully!', 'success')
        return redirect(url_for('manage_subjects'))
    
    return render_template('admin/add_subject.html')

@app.route('/admin/subject/delete/<int:subject_id>')
@login_required
def delete_subject(subject_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/admin/marks')
@login_required
def manage_marks():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    marks = Marks.query.all()
    return render_template('admin/manage_marks.html', marks=marks)

@app.route('/admin/marks/enter', methods=['GET', 'POST'])
@login_required
def enter_marks():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    students = Student.query.all()
    subjects = Subject.query.all()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        subject_id = request.form.get('subject_id')
        marks_obtained = request.form.get('marks_obtained')
        total_marks = request.form.get('total_marks', 100)
        semester = request.form.get('semester')
        
        # Check if marks already exist
        existing_marks = Marks.query.filter_by(
            student_id=int(student_id),
            subject_id=int(subject_id),
            semester=int(semester)
        ).first()
        
        if existing_marks:
            existing_marks.marks_obtained = float(marks_obtained)
            existing_marks.total_marks = float(total_marks)
            existing_marks.updated_at = datetime.utcnow()
        else:
            marks = Marks(
                student_id=int(student_id),
                subject_id=int(subject_id),
                marks_obtained=float(marks_obtained),
                total_marks=float(total_marks),
                semester=int(semester)
            )
            db.session.add(marks)
        
        db.session.commit()
        flash('Marks entered successfully!', 'success')
        return redirect(url_for('manage_marks'))
    
    return render_template('admin/enter_marks.html', students=students, subjects=subjects)

@app.route('/admin/marks/delete/<int:marks_id>')
@login_required
def delete_marks(marks_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    marks = Marks.query.get_or_404(marks_id)
    db.session.delete(marks)
    db.session.commit()
    
    flash('Marks deleted successfully!', 'success')
    return redirect(url_for('manage_marks'))

@app.route('/admin/results/generate', methods=['GET', 'POST'])
@login_required
def generate_results():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        semester = request.form.get('semester')
        
        students = Student.query.filter_by(semester=int(semester)).all()
        
        for student in students:
            # Get all marks for this student in this semester
            marks_list = Marks.query.filter_by(
                student_id=student.id,
                semester=int(semester)
            ).all()
            
            if marks_list:
                total_obtained = sum(m.marks_obtained for m in marks_list)
                total_maximum = sum(m.total_marks for m in marks_list)
                percentage = (total_obtained / total_maximum) * 100 if total_maximum > 0 else 0
                gpa = calculate_gpa(marks_list)
                grade, _ = calculate_grade(total_obtained, total_maximum)
                cgpa = calculate_cgpa(student.id)
                
                # Check if result already exists
                existing_result = Result.query.filter_by(
                    student_id=student.id,
                    semester=int(semester)
                ).first()
                
                if existing_result:
                    existing_result.total_marks_obtained = total_obtained
                    existing_result.total_maximum_marks = total_maximum
                    existing_result.percentage = percentage
                    existing_result.gpa = gpa
                    existing_result.cgpa = cgpa
                    existing_result.grade = grade
                else:
                    result = Result(
                        student_id=student.id,
                        semester=int(semester),
                        total_marks_obtained=total_obtained,
                        total_maximum_marks=total_maximum,
                        percentage=percentage,
                        gpa=gpa,
                        cgpa=cgpa,
                        grade=grade
                    )
                    db.session.add(result)
        
        db.session.commit()
        flash(f'Results generated for Semester {semester}!', 'success')
        return redirect(url_for('manage_results'))
    
    return render_template('admin/generate_results.html')

@app.route('/admin/results')
@login_required
def manage_results():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    results = Result.query.all()
    return render_template('admin/manage_results.html', results=results)

@app.route('/admin/results/publish/<int:result_id>')
@login_required
def publish_result(result_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    result = Result.query.get_or_404(result_id)
    result.is_published = True
    
    # Also publish all related marks
    marks = Marks.query.filter_by(
        student_id=result.student_id,
        semester=result.semester
    ).all()
    for mark in marks:
        mark.is_published = True
    
    db.session.commit()
    flash('Result published successfully!', 'success')
    return redirect(url_for('manage_results'))

@app.route('/admin/results/unpublish/<int:result_id>')
@login_required
def unpublish_result(result_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    result = Result.query.get_or_404(result_id)
    result.is_published = False
    
    marks = Marks.query.filter_by(
        student_id=result.student_id,
        semester=result.semester
    ).all()
    for mark in marks:
        mark.is_published = False
    
    db.session.commit()
    flash('Result unpublished successfully!', 'success')
    return redirect(url_for('manage_results'))

# ==================== REPORTING ROUTES ====================

@app.route('/admin/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    return render_template('admin/reports.html')

@app.route('/admin/reports/class-performance')
@login_required
def class_performance():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    semester = request.args.get('semester', 1)
    department = request.args.get('department', '')
    
    query = Result.query.filter_by(semester=int(semester))
    if department:
        students = Student.query.filter_by(department=department).all()
        student_ids = [s.id for s in students]
        query = query.filter(Result.student_id.in_(student_ids))
    
    results = query.all()
    
    return render_template('admin/class_performance.html', 
                         results=results, 
                         semester=semester,
                         department=department)

@app.route('/admin/reports/subject-analysis')
@login_required
def subject_analysis():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    subject_id = request.args.get('subject_id')
    
    if subject_id:
        marks = Marks.query.filter_by(subject_id=int(subject_id)).all()
        subject = Subject.query.get(subject_id)
    else:
        marks = []
        subject = None
    
    subjects = Subject.query.all()
    
    return render_template('admin/subject_analysis.html',
                         marks=marks,
                         subject=subject,
                         subjects=subjects)

@app.route('/admin/reports/toppers')
@login_required
def toppers_list():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    semester = request.args.get('semester', 1)
    
    results = Result.query.filter_by(semester=int(semester), is_published=True)\
                          .order_by(Result.percentage.desc())\
                          .limit(10)\
                          .all()
    
    return render_template('admin/toppers.html', results=results, semester=semester)

# ==================== STUDENT ROUTES ====================

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    student = current_user.student
    results = Result.query.filter_by(student_id=student.id, is_published=True).all()
    
    return render_template('student/dashboard.html', student=student, results=results)

@app.route('/student/results')
@login_required
def view_results():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    student = current_user.student
    semester = request.args.get('semester')
    
    query = Result.query.filter_by(student_id=student.id, is_published=True)
    if semester:
        query = query.filter_by(semester=int(semester))
    
    results = query.all()
    
    return render_template('student/view_results.html', student=student, results=results, semester=semester)

@app.route('/student/marks')
@login_required
def view_marks():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    student = current_user.student
    semester = request.args.get('semester')
    
    query = Marks.query.filter_by(student_id=student.id, is_published=True)
    if semester:
        query = query.filter_by(semester=int(semester))
    
    marks = query.all()
    
    return render_template('student/view_marks.html', student=student, marks=marks, semester=semester)

@app.route('/student/download/<int:result_id>')
@login_required
def download_result(result_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    student = current_user.student
    result = Result.query.get_or_404(result_id)
    
    if result.student_id != student.id:
        flash('Access denied', 'error')
        return redirect(url_for('view_results'))
    
    # Generate PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    p.setFillColor(colors.darkblue)
    p.rect(0, height - 100, width, 100, fill=True, stroke=False)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(200, height - 60, "Result Management System")
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, height - 140, "Student Result Report")
    
    # Student Details
    p.setFont("Helvetica", 12)
    y = height - 200
    p.drawString(50, y, f"Name: {student.name}")
    p.drawString(50, y - 25, f"Roll Number: {student.roll_number}")
    p.drawString(50, y - 50, f"Department: {student.department}")
    p.drawString(50, y - 75, f"Semester: {result.semester}")
    p.drawString(50, y - 100, f"Academic Year: {student.academic_year}")
    
    # Result Summary
    y -= 150
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Result Summary")
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Total Marks Obtained: {result.total_marks_obtained}")
    p.drawString(50, y - 25, f"Total Maximum Marks: {result.total_maximum_marks}")
    p.drawString(50, y - 50, f"Percentage: {result.percentage:.2f}%")
    p.drawString(50, y - 75, f"GPA: {result.gpa:.2f}")
    p.drawString(50, y - 100, f"CGPA: {result.cgpa:.2f}")
    p.drawString(50, y - 125, f"Grade: {result.grade}")
    
    # Subject-wise Marks
    marks = Marks.query.filter_by(
        student_id=student.id,
        semester=result.semester,
        is_published=True
    ).all()
    
    y -= 170
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Subject-wise Marks")
    y -= 30
    
    # Table header
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Subject")
    p.drawString(250, y, "Marks Obtained")
    p.drawString(400, y, "Total Marks")
    p.drawString(500, y, "Grade")
    
    y -= 25
    p.setFont("Helvetica", 10)
    for mark in marks:
        grade, _ = calculate_grade(mark.marks_obtained, mark.total_marks)
        p.drawString(50, y, mark.subject.name[:30])
        p.drawString(250, y, str(mark.marks_obtained))
        p.drawString(400, y, str(mark.total_marks))
        p.drawString(500, y, grade)
        y -= 20
    
    # Footer
    p.setFont("Helvetica-Italic", 8)
    p.drawString(50, 50, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    p.save()
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=result_{student.roll_number}_sem{result.semester}.pdf'
    
    return response

# ==================== CREATE ADMIN USER ====================

def create_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists!")

# ==================== INITIALIZE DATABASE ====================

def init_db():
    with app.app_context():
        db.create_all()
        create_admin()
        
        # Add sample subjects
        if Subject.query.count() == 0:
            subjects = [
                Subject(code='CS101', name='Introduction to Programming', credits=4, semester=1, department='Computer Science'),
                Subject(code='CS102', name='Mathematics for Computing', credits=3, semester=1, department='Computer Science'),
                Subject(code='CS103', name='Digital Logic Design', credits=3, semester=1, department='Computer Science'),
                Subject(code='CS201', name='Data Structures', credits=4, semester=2, department='Computer Science'),
                Subject(code='CS202', name='Computer Organization', credits=3, semester=2, department='Computer Science'),
                Subject(code='CS203', name='Database Management', credits=4, semester=2, department='Computer Science'),
            ]
            for subject in subjects:
                db.session.add(subject)
            db.session.commit()
            print("Sample subjects added!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
