from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import os
from datetime import datetime, timedelta
import json

file_path = ''
patient = {}

current_path = os.path.dirname(os.path.realpath(__file__))
path_to_data = os.path.join(current_path, 'patient_data')

os.makedirs(path_to_data, exist_ok=True)

credentials_file_path = os.path.join(current_path, 'config')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

users = {}

# Initialize 'credentials.json' file
if not os.path.exists(credentials_file_path):
    os.makedirs(credentials_file_path, exist_ok=True)
    with open(os.path.join(credentials_file_path, 'credentials.json'), 'w') as cred_file:
        json.dump(users, cred_file)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        new_username = request.form['username'].lower()
        new_password = request.form['password']
        new_email = request.form['email']
        new_phone = request.form['phone']

        # Load existing users from the credentials file
        with open(os.path.join(credentials_file_path, 'credentials.json'), 'r') as cred_file:
            users = json.load(cred_file)

        # Check if the username already exists
        if new_username in users:
            return "Username already exists. Please choose another username."

        # Add the new user with their email and phone to the credentials file
        users[new_username] = {
            "password": new_password,
            "email": new_email,
            "phone": new_phone
        }

        with open(os.path.join(credentials_file_path, 'credentials.json'), 'w') as cred_file:
            json.dump(users, cred_file)

        # Create a folder for the new doctor to store their patient files
        doctor_folder = os.path.join(path_to_data, new_username)
        os.makedirs(doctor_folder, exist_ok=True)

        return redirect(url_for('login'))

    return render_template('signup.html')


def process_patient_data(patient_data):
    """Processes patient data by cleaning up newlines and splitting multi-line text."""
    processed_data = {}

    for line in patient_data:
        key, value = line.strip().split(': ', 1)
        if 'Diagnosis' in key or 'Complaints & History' in key or 'Prescription' in key:
            value = value.strip('[]').replace(r'\r', '').split(', ')
            value = '\n'.join(value)
        processed_data[key] = value

    return processed_data


def get_patient_data(file_path):
    """Reads patient data from the given file path."""
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as file:
        patient_data = file.readlines()

    return process_patient_data(patient_data)


def generate_unique_id(doctor_name):
    config_folder_path = os.path.join(current_path, 'config')
    os.makedirs(config_folder_path, exist_ok=True)

    used_ids_file_path = os.path.join(config_folder_path, f'{doctor_name}_used_ids.json')
    used_ids = []

    if os.path.exists(used_ids_file_path):
        try:
            with open(used_ids_file_path, 'r') as file:
                used_ids = json.load(file)
        except json.decoder.JSONDecodeError:
            pass

    last_used_id = used_ids[-1] if used_ids else 0
    new_id = last_used_id + 1
    formatted_id = f'{doctor_name}_FC{new_id:04d}'
    used_ids.append(new_id)

    with open(used_ids_file_path, 'w') as file:
        json.dump(used_ids, file)

    return formatted_id


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return wrapper


def add_follow_up_to_file(file_path, diagnosis, prescription):
    with open(file_path, 'a') as file:
        file.write(f"Follow-up Date: {datetime.today().strftime('%Y-%m-%d')}\n")
        if '\n' in diagnosis:
            new_diag = diagnosis.split('\n')
            file.write(f"Follow-up Diagnosis on {datetime.today().strftime('%Y-%m-%d')}: {new_diag}\n")
        else:
            file.write(f"Follow-up Diagnosis on {datetime.today().strftime('%Y-%m-%d')}: {diagnosis}\n")

        if '\n' in prescription:
            new_pre = prescription.split('\n')
            file.write(f"Follow-up Prescription on {datetime.today().strftime('%Y-%m-%d')}: {new_pre}\n")
        else:
            file.write(f"Follow-up Prescription on {datetime.today().strftime('%Y-%m-%d')}: {prescription}\n")


@app.route('/')
@login_required
def index():
    username = session['username']
    return render_template('index.html', username=username.capitalize())


@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        sex = request.form['sex']
        age = request.form['age']
        contact_number = request.form['contact_number']
        diagnosis = request.form['diagnosis']
        complaints_history = request.form['complaints_history']
        prescription = request.form['prescription']

        doctor_name = session['username']
        patient_id = generate_unique_id(doctor_name)

        # Create the doctor’s folder if it doesn’t exist
        doctor_folder = os.path.join(path_to_data, doctor_name)
        os.makedirs(doctor_folder, exist_ok=True)

        # Generate the file name with doctor's name and unique ID
        file_name = f'{patient_id}_{contact_number}.txt'
        file_path = os.path.join(doctor_folder, file_name)

        # Save patient data to the file
        with open(file_path, 'w') as file:
            file.write(f'UID: {patient_id}\n')
            file.write(f"Date: {datetime.today().strftime('%Y-%m-%d')}\n")
            file.write(f'Name: {name.title()}\n')
            file.write(f'Sex: {sex.upper()}\n')
            file.write(f'Age: {age}\n')
            file.write(f'Contact Number: {contact_number}\n')

            if '\n' in diagnosis:
                new_diag = diagnosis.split('\n')
                file.write(f'Diagnosis: {new_diag}\n')
            else:
                file.write(f'Diagnosis: {diagnosis}\n')

            if '\n' in complaints_history:
                new_comp = complaints_history.split('\n')
                file.write(f'Complaints & History: {new_comp}\n')
            else:
                file.write(f'Complaints & History: {complaints_history}\n')

            if '\n' in prescription:
                new_pres = prescription.split('\n')
                file.write(f'Prescription: {new_pres}\n')
            else:
                file.write(f'Prescription: {prescription}\n')

        return redirect(url_for('follow_up', patient_id=patient_id))

    return render_template('add_patient.html')


@app.route('/follow_up/<string:patient_id>', methods=['GET', 'POST'])
@login_required
def follow_up(patient_id):
    doctor_name = session['username']
    doctor_folder = os.path.join(path_to_data, doctor_name)

    # Locate the patient file
    file_path = ''
    for patient_file in os.listdir(doctor_folder):
        if patient_id in patient_file:
            file_path = os.path.join(doctor_folder, patient_file)
            break

    if not file_path or not os.path.exists(file_path):
        return "Patient not found"

    if request.method == 'POST':
        # Get form data from the follow-up form
        follow_up_required = request.form['follow_up_required']
        follow_up_days_str = request.form.get('follow_up_days')
        new_diagnosis = request.form.get('diagnosis')
        new_prescription = request.form.get('prescription')

        # Determine the next follow-up date
        if follow_up_days_str and follow_up_days_str.isdigit():
            follow_up_days = int(follow_up_days_str)
        else:
            follow_up_days = 0

        # Append the new follow-up information to the patient's file
        with open(file_path, 'a') as file:
            if follow_up_required == 'Yes' and follow_up_days:
                today = datetime.today()
                next_follow_up_date = today + timedelta(days=follow_up_days)
                next_follow_up_date_str = next_follow_up_date.strftime('%Y-%m-%d')
                file.write(f"Medicine days from {datetime.today().strftime('%Y-%m-%d')}: {follow_up_days}\n")
                file.write(f'Next Follow-up Date: {next_follow_up_date_str}\n')

        # Retrieve existing patient data and follow-up history
        patient = get_patient_data(file_path)
        if not patient:
            return "Error reading patient data"
        return render_template('view_patient.html', patient=patient)

    return render_template('follow_up.html', patient_id=patient_id)



@app.route('/add_follow_up/<string:patient_id>', methods=['GET', 'POST'])
@login_required
def add_follow_up(patient_id):
    doctor_name = session['username']
    doctor_folder = os.path.join(path_to_data, doctor_name)

    file_path = ''
    for patient_file in os.listdir(doctor_folder):
        if patient_id in patient_file:
            file_path = os.path.join(doctor_folder, patient_file)
            break

    if not file_path or not os.path.exists(file_path):
        return "Patient not found"

    if request.method == 'POST':
        diagnosis = request.form['diagnosis']
        prescription = request.form['prescription']

        add_follow_up_to_file(file_path, diagnosis, prescription)

        return redirect(url_for('follow_up', patient_id=patient_id))

    # Reuse the get_patient_data function to fetch and process patient data
    patient = get_patient_data(file_path)
    if not patient:
        return "Error reading patient data"

    return render_template('add_follow_up.html', patient=patient, patient_id=patient_id)


@app.route('/view_patient')
@login_required
def view_patients():
    doctor_name = session['username']
    doctor_folder = os.path.join(path_to_data, doctor_name)

    if not os.path.exists(doctor_folder):
        return "No patients found for this doctor."

    # Get the list of patient files
    patient_files = os.listdir(doctor_folder)

    # Function to extract the FCXXXX number from the filename
    def extract_serial_number(file_name):
        # Assuming file format is: doctorname_FCXXXX_phonenumber.txt
        serial_number_part = file_name.split('_')[1]  # Extract 'FCXXXX'
        return int(serial_number_part[2:])  # Extract XXXX and convert to int for sorting

    # Sort the files based on the FCXXXX part of the filename
    sorted_patient_files = sorted(patient_files, key=extract_serial_number)

    all_patients = []

    for file in sorted_patient_files:
        uid = file.split('_')[1]
        contact_number = file.split('_')[2].replace('.txt', '')

        file_path = os.path.join(doctor_folder, file)
        patient = get_patient_data(file_path)
        if not patient:
            continue

        all_patients.append({'uid': uid, 'name': patient.get('Name', 'Unknown'), 'contact': contact_number})

    return render_template('search_patients.html', num_patients=len(patient_files), all_patients=all_patients)



@app.route('/search_patient', methods=['POST'])
@login_required
def search_patient():
    doctor_name = session['username']
    doctor_folder = os.path.join(path_to_data, doctor_name)

    search_input = request.form['search_input'].upper()

    file_path = ''
    if len(search_input) >= 6:
        for patient_file in os.listdir(doctor_folder):
            if search_input.isnumeric() and search_input == patient_file.replace('.txt', '').split('_')[2]:
                file_path = os.path.join(doctor_folder, patient_file)
                break
            elif search_input.isalnum() and search_input == patient_file.replace('.txt', '').split('_')[1]:
                file_path = os.path.join(doctor_folder, patient_file)
                break

    if not file_path or not os.path.exists(file_path):
        return "Patient not found"

    # Reuse the get_patient_data function
    patient = get_patient_data(file_path)
    if not patient:
        return "Error reading patient data"

    return render_template('view_patient.html', patient=patient, patient_id=search_input)


@app.route('/open_view_patient/<string:patient_id>')
@login_required
def open_view_patient(patient_id):
    doctor_name = session['username']
    doctor_folder = os.path.join(path_to_data, doctor_name)

    file_path = ''
    for patient_file in os.listdir(doctor_folder):
        if patient_id.isalnum() and patient_id == patient_file.replace('.txt', '').split('_')[1]:
            file_path = os.path.join(doctor_folder, patient_file)
            break

    if not file_path or not os.path.exists(file_path):
        return "Patient not found"

    # Reuse the get_patient_data function
    patient = get_patient_data(file_path)
    if not patient:
        return "Error reading patient data"

    return render_template('view_patient.html', patient=patient, patient_id=patient_id)


@app.route('/scheduled_follow_up')
@login_required
def upcoming_follow_ups():
    today = datetime.today()
    doctor_name = session['username']
    doctor_folder = os.path.join(path_to_data, doctor_name)

    upcoming_follow_ups = []

    for patient_file in os.listdir(doctor_folder):
        file_path = os.path.join(doctor_folder, patient_file)
        patient = get_patient_data(file_path)
        if not patient:
            continue

        if 'Next Follow-up Date' in patient:
            follow_up_date = datetime.strptime(patient['Next Follow-up Date'], '%Y-%m-%d')
            if follow_up_date >= today:
                remaining_days = (follow_up_date - today).days
                patient['Remaining Days'] = f'{remaining_days} days' if remaining_days > 0 else 'Today'
                upcoming_follow_ups.append(patient)

    upcoming_follow_ups.sort(key=lambda x: x.get('Next Follow-up Date'))

    return render_template('scheduled_follow_up.html', upcoming_follow_ups=upcoming_follow_ups)


@app.route('/login', methods=['GET', 'POST'])
def login():
    with open(os.path.join(credentials_file_path, 'credentials.json'), 'r') as cred_file:
        users = json.load(cred_file)

    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']

        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('index'))

        return "Invalid credentials. Please try again."

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
