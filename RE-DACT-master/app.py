from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import re  # Make sure this is imported once at the top
import uuid
import datetime
import glob
import json
import nltk
from nltk import word_tokenize, pos_tag, ne_chunk
from models import db, User, File
from config import Config
from Redactor001 import Redactor
# nltk.download('punkt')
# nltk.download('punkt_tab')
# nltk.download('wordnet')
# nltk.download('omw-1.4')
# nltk.download('averaged_perceptron_tagger')
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    files = File.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', files=files)

# filepath: /Users/yashpardeshi/Desktop/RE-DACT/RE-DACT-master/app.py
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('dashboard'))
    
    if file:
        try:
            # Create uploads directory if it doesn't exist
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            # Save original file with a timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            original_filename = secure_filename(file.filename)
            base_name, file_extension = os.path.splitext(original_filename)
            
            # Create a readable filename with timestamp
            readable_filename = f"{base_name}_{timestamp}{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], readable_filename)
            file.save(file_path)
            
            # CHANGED: Use custom method instead of gradation as default
            method = "custom"  # Changed from "gradation" to "custom"
            
            # CHANGED: Use NNP and NNPS tags by default
            pos_tags = ["NNP", "NNPS"]  # Proper nouns and plural proper nouns
            
            # Process the file using custom method with proper noun tags
            processed_file_path, processed_filename, analysis_filename = process_file(
                file_path, 
                method,
                pos_tags=pos_tags  # Pass the pos_tags instead of gradation_level
            )
            
            # Save file info to database
            new_file = File(
                filename=processed_filename,
                original_filename=original_filename,
                user_id=current_user.id
            )
            db.session.add(new_file)
            db.session.commit()
            
            flash('File uploaded and processed successfully')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error uploading file: {str(e)}')
            return redirect(url_for('dashboard'))

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    file = File.query.filter_by(filename=filename, user_id=current_user.id).first_or_404()
    
    # Check the PROCESSED_FOLDER first (where redacted files are stored)
    if os.path.exists(os.path.join(app.config['PROCESSED_FOLDER'], filename)):
        return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)
    
    # If not found in PROCESSED_FOLDER, try the UPLOAD_FOLDER
    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    
    # If file doesn't exist in either folder
    flash(f'File {filename} not found in server storage')
    return redirect(url_for('dashboard'))

# @app.route('/redact')
# @login_required
# def redact():
#     return render_template('redact.html')
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Directory to store uploaded files
app.config['PROCESSED_FOLDER'] = 'processed/'  # Directory to store processed files

# Ensure upload and processed folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

def process_file(file_path, method, gradation_level=None, pos_tags=None):
    """
    Process the uploaded file using the redaction model.
    :param file_path: Path to the uploaded file.
    :param method: Redaction method ('gradation' or 'custom')
    :param gradation_level: Custom obfuscation or gradation level.
    :param pos_tags: List of POS tags to redact in custom mode
    :return: Path to the processed file and processed filename.
    """
    # Initialize the Redactor class
    redactor = Redactor()

    # Extract the file extension and base name
    file_name = os.path.basename(file_path)
    base_name, file_extension = os.path.splitext(file_name)
    
    # Create timestamps
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_short = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Extract text from the file
    doc_text = redactor.extract_text(file_path, file_extension)
    if not doc_text:
        raise ValueError("Unable to extract text from the file.")
    
    # Count total words
    total_words = len(re.findall(r'\b\w+\b', doc_text))

    # Obfuscate text based on the selected method
    if method == "gradation":
        target_words = redactor.obfuscate_words(doc_text, "gradation", {"gradation": int(gradation_level)})
    else:
        target_words = redactor.obfuscate_words(doc_text, "custom", {"custom": pos_tags})
    
    if not target_words:
        raise ValueError("No target words found for obfuscation.")
    
    # Count obfuscated words
    obfuscated_count = len(target_words)
    obfuscation_percentage = round((obfuscated_count / total_words) * 100, 2) if total_words > 0 else 0

    # Reconstruct the file with redacted content
    if file_extension.lower() == ".txt":
        redactor._Redactor__obfuscate_reconstruct_txt(file_path, target_words)
    elif file_extension.lower() == ".pdf":
        redactor._Redactor__obfuscate_reconstruct_pdf(file_path, target_words)
    elif file_extension.lower() == ".docx":
        redactor._Redactor__obfuscate_reconstruct_docx(file_path, target_words)
    else:
        raise ValueError("Unsupported file type for redaction.")

    # SIMPLIFIED READABLE NAMING APPROACH:
    
    # Parse any existing timestamp from the filename
    if "_" in base_name:
        # Try to preserve the timestamp if it already exists
        match = re.search(r'_(\d{8}_\d{6})$', base_name)
        if match:
            timestamp_short = match.group(1)
            # Remove the timestamp from base_name to avoid duplication
            base_name = base_name.rsplit('_', 1)[0]
    
    # 1. Create human-readable names with method and level info
    if method == "gradation":
        processed_filename = f"{base_name}_G{gradation_level}_{timestamp_short}{file_extension}"
    else:
        # For custom method, add a C prefix
        processed_filename = f"{base_name}_C_{timestamp_short}{file_extension}"
    
    processed_file_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
    
    # 2. Move the processed file to the processed folder with the new name
    os.rename(file_path, processed_file_path)
    
    # 3. Create analysis JSON with MATCHING name pattern
    analysis_filename = f"{base_name}_analysis_{timestamp_short}.json"
    analysis_file_path = os.path.join(app.config['PROCESSED_FOLDER'], analysis_filename)
    
    # 4. Save analysis with same timestamp so they can be linked
    analysis_data = {
        "file_name": file_name,
        "processed_file": processed_filename,
        "file_type": file_extension,
        "timestamp": timestamp,
        "redaction_method": method,
        "gradation_level": gradation_level if method == "gradation" else None,
        "pos_tags": pos_tags if method == "custom" else None,
        "total_words": total_words,
        "obfuscated_count": obfuscated_count,
        "obfuscation_percentage": obfuscation_percentage,
        "target_words": list(target_words) if isinstance(target_words, set) else target_words,
        "replacement_word": "[ REDACTED ]"
    }
    
    try:
        with open(analysis_file_path, 'w') as f:
            import json
            json.dump(analysis_data, f, indent=4)
    except Exception as e:
        print(f"Error writing analysis file: {e}")
        # Try an alternative location
        alternative_path = os.path.join(os.path.dirname(processed_file_path), analysis_filename)
        with open(alternative_path, 'w') as f:
            import json
            json.dump(analysis_data, f, indent=4)
        analysis_file_path = alternative_path

    return processed_file_path, processed_filename, analysis_filename  # Return analysis filename too


@app.route('/redact', methods=['GET', 'POST'])
@login_required
def redact():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
            
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file:
            # Get the method and parameters
            method = request.form.get('method', 'gradation')
            
            # Save the file - use original filename directly
            original_filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            file.save(file_path)
            
            try:
                if method == 'gradation':
                    gradation_level = request.form.get('gradation_level', '1')
                    processed_file_path, processed_filename, analysis_filename = process_file(
                        file_path, 
                        method, 
                        gradation_level=gradation_level
                    )
                else:  # custom
                    pos_tags = request.form.getlist('pos_tags')
                    processed_file_path, processed_filename, analysis_filename = process_file(
                        file_path, 
                        method, 
                        pos_tags=pos_tags
                    )
                
                # Save file info to database with analysis filename
                new_file = File(
                    filename=processed_filename,
                    original_filename=original_filename,
                    # Add analysis_filename if you have that field in your model
                    # analysis_filename=analysis_filename,  
                    user_id=current_user.id
                )
                db.session.add(new_file)
                db.session.commit()
                
                flash('File successfully redacted')
                return render_template('redact.html', 
                                      processed_file_path=processed_file_path,
                                      processed_filename=processed_filename,
                                      analysis_filename=analysis_filename)
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}')
                return redirect(request.url)

    return render_template('redact.html')


@app.route('/download_processed/<filename>')
@login_required
def download_processed(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)
    

@app.route('/process_redaction', methods=['POST'])
@login_required
def process_redaction():
    try:
        data = request.json
        text = data.get('text')
        method = data.get('method')
        
        if not text:
            return jsonify({"success": False, "error": "No text provided"})
        
        redactor = Redactor()
        
        if method == 'gradation':
            gradation_level = data.get('gradation_level', 1)
            target_words = redactor.obfuscate_words(text, "gradation", {"gradation": gradation_level})
        else:
            pos_tags = data.get('pos_tags', [])
            if not pos_tags:
                return jsonify({"success": False, "error": "No POS tags selected"})
            target_words = redactor.obfuscate_words(text, "custom", {"custom": pos_tags})
        
        # Use the internal method to reconstruct text with redactions
        redacted_text = text
        for word in target_words:
            # Replace exact word occurrences with [REDACTED]
            pattern = r'\b' + re.escape(word) + r'\b'
            redacted_text = re.sub(pattern, '[ REDACTED ]', redacted_text)
            
        return jsonify({"success": True, "redacted_text": redacted_text})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
@app.route('/view_analysis/<filename>')
@login_required
def view_analysis(filename):
    # Extract the base name without extension
    base_name, ext = os.path.splitext(filename)
    
    # Look for analysis files with various patterns
    processed_folder = app.config['PROCESSED_FOLDER']
    uploads_folder = app.config['UPLOAD_FOLDER']
    
    # Extract the timestamp if present in the filename
    timestamp = None
    match = re.search(r'_(G\d+|C)_(\d{8}_\d{6})', base_name)
    if match:
        timestamp = match.group(2)
        base_name_parts = base_name.split(f"_{match.group(1)}_{timestamp}")
        base_name = base_name_parts[0]
    
    # Several patterns to try
    patterns = [
        f"{base_name}_analysis_{timestamp}.json" if timestamp else None,
        f"{base_name}_analysis_*.json",  # wildcard for timestamp
        f"{base_name}*analysis*.json"    # very loose pattern
    ]
    
    # Remove None entries
    patterns = [p for p in patterns if p]
    
    # Try to find matching files in both folders
    analysis_path = None
    
    for pattern in patterns:
        if '*' in pattern:
            # Use glob for wildcard patterns
            import glob
            matches = glob.glob(os.path.join(processed_folder, pattern))
            if matches:
                analysis_path = matches[0]
                break
                
            matches = glob.glob(os.path.join(uploads_folder, pattern))
            if matches:
                analysis_path = matches[0]
                break
        else:
            # Direct file check for exact patterns
            path = os.path.join(processed_folder, pattern)
            if os.path.exists(path):
                analysis_path = path
                break
                
            path = os.path.join(uploads_folder, pattern)
            if os.path.exists(path):
                analysis_path = path
                break
    
    if analysis_path:
        try:
            with open(analysis_path, 'r') as f:
                import json
                analysis_data = json.load(f)
            return render_template('analysis.html', analysis=analysis_data)
        except Exception as e:
            flash(f'Error reading analysis file: {str(e)}')
    else:
        # Debug information
        flash(f'Analysis file not found for: {filename}')
        flash(f'We tried patterns: {", ".join(patterns)}')
        
        # List JSON files in both folders
        import glob
        processed_jsons = glob.glob(os.path.join(processed_folder, "*.json"))
        uploads_jsons = glob.glob(os.path.join(uploads_folder, "*.json"))
        
        if processed_jsons:
            flash(f'JSON files in processed folder: {", ".join([os.path.basename(f) for f in processed_jsons[:5]])}{"..." if len(processed_jsons) > 5 else ""}')
        if uploads_jsons:
            flash(f'JSON files in uploads folder: {", ".join([os.path.basename(f) for f in uploads_jsons[:5]])}{"..." if len(uploads_jsons) > 5 else ""}')
    
    return redirect(url_for('dashboard'))

@app.route('/delete/<filename>', methods=['POST'])
@login_required
def delete_file(filename):
    # Find the file in the database
    file = File.query.filter_by(filename=filename, user_id=current_user.id).first_or_404()
    
    try:
        # Delete the physical file from the processed folder
        if os.path.exists(os.path.join(app.config['PROCESSED_FOLDER'], filename)):
            os.remove(os.path.join(app.config['PROCESSED_FOLDER'], filename))
        
        # Look for and delete the analysis file if it exists
        base_name, ext = os.path.splitext(filename)
        
        # Try common analysis file patterns
        analysis_patterns = [
            f"{base_name}_analysis*.json",
            f"{base_name.split('_G')[0]}_analysis*.json" if '_G' in base_name else None,
            f"{base_name.split('_C_')[0]}_analysis*.json" if '_C_' in base_name else None
        ]
        
        for pattern in [p for p in analysis_patterns if p]:
            for analysis_file in glob.glob(os.path.join(app.config['PROCESSED_FOLDER'], pattern)):
                try:
                    os.remove(analysis_file)
                except:
                    pass
        
        # Delete the record from the database
        db.session.delete(file)
        db.session.commit()
        
        flash('File deleted successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting file: {str(e)}')
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
