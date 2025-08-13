from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from database import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('auth/login.html')
        
        user_data = db.get_user_by_email(email)
        
        if user_data:
            user = User(user_data)
            if user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all required fields', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/register.html')
        
        # Check if user already exists
        existing = db.get_user_by_email(email)
        if existing:
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        try:
            password_hash = User.set_password(password)
            user_data = db.create_user(
                username=username,
                email=email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name
            )
            
            if user_data:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                print('Registration insert returned no data')
                flash('Registration failed (no data returned). Please try again.', 'error')
        except Exception as e:
            # Log server-side for diagnosis and show concise message to user
            print(f"Registration error: {e}")
            flash(f'Registration failed: {str(e)}', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        try:
            updates = {
                'first_name': first_name,
                'last_name': last_name
            }
            updated_user = db.update_user(current_user.id, updates)
            if updated_user:
                flash('Profile updated successfully', 'success')
            else:
                flash('Failed to update profile', 'error')
        except Exception as e:
            flash('Failed to update profile', 'error')
    
    return render_template('profile.html')


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change password via JSON body: {current_password, new_password}. Returns JSON."""
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    if not current_password or not new_password:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400

    # Verify current password
    try:
        user_data = db.get_user_by_id(current_user.id)
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        user = User(user_data)
        if not user.check_password(current_password):
            return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400

        # Update password
        new_hash = User.set_password(new_password)
        updated = db.update_user(current_user.id, {'password_hash': new_hash})
        if not updated:
            return jsonify({'success': False, 'error': 'Failed to update password'}), 500
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
