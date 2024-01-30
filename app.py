from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import os
from datetime import datetime, timedelta
import json

path_to_data = r'patient_data'
credentials_file = r'config\credentials.json'
file_path = ''
patient = {}

current_path = os.getcwd()
os.makedirs(os.path.join(current_path, path_to_data), exist_ok=True)

app = Flask(__name__)
app.secret_key = '47c27afab0bd14cdec75933666c92a587038f57c11c2a68a59d3b9800fb1d755'

users = {}

# Initialize 'credentials.json' file
if not os.path.exists(credentials_file):
    with open(credentials_file, 'w') as cred_file:
        json.dump(users, cred_file)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']

        with open(credentials_file, 'r') as cred_file:
            users = json.load(cred_file)

        if new_username in users:
            return "Username already exists. Please choose another username."

        users[new_username] = new_password

        with open(credentials_file, 'w') as cred_file:
            json.dump(users, cred_file)

        return redirect(url_for('login'))

    return render_template('signup.html')


def generate_unique_id():
    config_folder_path = 'config'
    os.makedirs(config_folder_path, exist_ok=True)

    used_ids_file_path = os.path.join(config_folder_path, 'used_ids.json')
    used_ids = []

    if os.path.exists(used_ids_file_path):
        try:
            with open(used_ids_file_path, 'r') as file:
                used_ids = json.load(file)
        except json.decoder.JSONDecodeError:
            pass

    last_used_id = used_ids[-1] if used_ids else 0
    new_id = last_used_id + 1
    formatted_id = f'FC{new_id:04d}'
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
    return render_template('index.html', username=username)


@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        sex = request.form['sex']
        age = request.form['age']
        contact_number = request.form['contact_number']
        diagnosis = request.form['diagnosis']
        complaints_history = request.form['complaints_history']
        prescription = request.form['prescription']

        patient_id = generate_unique_id()

        os.makedirs('patient_data', exist_ok=True)

        file_name = f'{patient_id}_{contact_number}.txt'
        file_path = os.path.join(path_to_data, file_name)

        with open(file_path, 'w') as file:
            file.write(f'UID: {patient_id}\n')
            file.write(f"Date: {datetime.today().strftime('%Y-%m-%d')}\n")
            file.write(f'Name: {name.title()}\n')
            file.write(f'Sex: {sex.upper()}\n')
            file.write(f'Age: {age}\n')
            file.write(f'Contact Number: {contact_number}\n')
            if '\n' in diagnosis:
                new_dea = diagnosis.split('\n')
                file.write(f'Diagnosis: {new_dea}\n')
            else:
                file.write(f'Diagnosis: {diagnosis}\n')

            if '\n' in complaints_history:
                new_comp = complaints_history.split('\n')
                file.write(f'Complaints & History: {new_comp}\n')
            else:
                file.write(f'Complaints & History: {complaints_history}\n')

            if '\n' in prescription:
                new_pre = prescription.split('\n')
                file.write(f'Prescription: {new_pre}\n')
            else:
                file.write(f'Prescription: {prescription}\n')

        return redirect(url_for('follow_up', patient_id=patient_id))

    return render_template('add_patient.html')


@app.route('/follow_up/<string:patient_id>', methods=['GET', 'POST'])
def follow_up(patient_id):
    global file_path
    if request.method == 'POST':
        follow_up_required = request.form['follow_up_required']
        follow_up_days_str = request.form.get('follow_up_days')

        if follow_up_days_str and follow_up_days_str.isdigit():
            follow_up_days = int(follow_up_days_str)
        else:
            follow_up_days = 0

        for patient_file in os.listdir(path_to_data):
            if patient_id in patient_file:
                file_path = os.path.join(path_to_data, patient_file)
                break

        if not os.path.exists(file_path):
            return "Patient not found"

        with open(file_path, 'a') as file:
            if follow_up_required == 'Yes' and follow_up_days:
                today = datetime.today()
                next_follow_up_date = today + timedelta(days=follow_up_days)
                next_follow_up_date_str = next_follow_up_date.strftime('%Y-%m-%d')
                file.write(f"Medicine days from {datetime.today().strftime('%Y-%m-%d')}: {follow_up_days}\n")
                file.write(f'Next Follow-up Date: {next_follow_up_date_str}\n')

        with open(file_path, 'r') as file:
            patient_data = file.readlines()

        patient = {}
        for line in patient_data:
            key, value = line.strip().split(': ')
            if 'Diagnosis' or 'Complaints & History' or 'Prescription' in key:
                value = value.strip('[]').replace(r'\r', '').split(', ')
                value = '\n'.join(value)
            patient[key] = value

        return render_template('view_patient.html', patient=patient)

    return render_template('follow_up.html', patient_id=patient_id)


@app.route('/add_follow_up/<string:patient_id>', methods=['GET', 'POST'])
def add_follow_up(patient_id):
    global file_path

    for patient_file in os.listdir(path_to_data):
        if patient_id in patient_file:
            file_path = os.path.join(path_to_data, patient_file)
            break

    if not os.path.exists(file_path):
        return "Patient not found"

    if request.method == 'POST':
        diagnosis = request.form['diagnosis']
        prescription = request.form['prescription']

        add_follow_up_to_file(file_path, diagnosis, prescription)

        return redirect(url_for('follow_up', patient_id=patient_id))

    with open(file_path, 'r') as file:
        patient_data = file.readlines()

    patient = {}
    for line in patient_data:
        key, value = line.strip().split(': ')
        if 'Diagnosis' or 'Complaints & History' or 'Prescription' in key:
            value = value.strip('[]').replace(r'\r', '').split(', ')
            value = '\n'.join(value)
        patient[key] = value

    return render_template('add_follow_up.html', patient=patient, patient_id=patient_id)


@app.route('/view_patient')
def view_patient():
    patient_files = os.listdir('patient_data')
    all_patients = []

    for file in patient_files:
        uid = file.split('_')[0]
        contact_number = file.split('_')[1].replace('.txt', '')

        file_path = os.path.join('patient_data', file)
        with open(file_path, 'r') as file_content:
            for line in file_content:
                if line.startswith('Name:'):
                    name = line.split(': ')[1].strip()
                    break
            else:
                name = "Unknown"

        all_patients.append({'uid': uid, 'name': name})

    return render_template('search_patients.html', num_patients=len(patient_files), all_patients=all_patients)


@app.route('/search_patient', methods=['POST'])
def search_patient():
    global file_path, patient
    file_path = ''
    search_input = request.form['search_input'].upper()
    if len(search_input) >= 6:
        for patient_file in os.listdir(path_to_data):
            if search_input.isnumeric() and search_input == patient_file.replace('.txt', '').split('_')[1]:
                file_path = os.path.join(path_to_data, patient_file)
                break
            elif search_input.isalnum() and search_input == patient_file.replace('.txt', '').split('_')[0]:
                file_path = os.path.join(path_to_data, patient_file)
                break
    else:
        return "Patient not found"

    if not os.path.exists(file_path):
        return "Patient not found"

    with open(file_path, 'r') as file:
        patient_data = file.readlines()

    patient = {}
    for line in patient_data:
        key, value = line.strip().split(': ')
        if 'Diagnosis' or 'Complaints & History' or 'Prescription' in key:
            value = value.strip('[]').replace(r'\r', '').split(', ')
            value = '\n'.join(value)
        patient[key] = value

    return render_template('view_patient.html', patient=patient, patient_id=search_input)


@app.route('/open_view_patient/<string:patient_id>')
def open_view_patient(patient_id):
    file_path = ''

    for patient_file in os.listdir(path_to_data):
        if patient_id.isalnum() and patient_id == patient_file.replace('.txt', '').split('_')[0]:
            file_path = os.path.join(path_to_data, patient_file)
            break

    with open(file_path, 'r') as file:
        patient_data = file.readlines()

    patient = {}
    for line in patient_data:
        key, value = line.strip().split(': ')
        if 'Diagnosis' or 'Complaints & History' or 'Prescription' in key:
            value = value.strip('[]').replace(r'\r', '').split(', ')
            value = '\n'.join(value)
        patient[key] = value

    return render_template('view_patient.html', patient=patient, patient_id=patient_id)


@app.route('/scheduled_follow_up')
def upcoming_follow_ups():
    today = datetime.today().strftime('%Y-%m-%d')
    patient_files = os.listdir('patient_data')
    upcoming_follow_ups = []

    for patient_file in patient_files:
        with open(f'patient_data/{patient_file}', 'r') as file:
            patient_data = file.readlines()

        patient = {}
        for line in patient_data:
            key, value = line.strip().split(': ')
            if 'Diagnosis' or 'Complaints & History' or 'Prescription' in key:
                value = value.strip('[]').replace(r'\r', '').split(', ')
                value = '\n'.join(value)
            patient[key] = value

        if 'Next Follow-up Date' in patient:
            follow_up_date = patient['Next Follow-up Date']
            if follow_up_date >= today:
                upcoming_follow_ups.append(patient)

    upcoming_follow_ups.sort(key=lambda x: x.get('Next Follow-up Date'))

    return render_template('scheduled_follow_up.html', upcoming_follow_ups=upcoming_follow_ups)


@app.route('/login', methods=['GET', 'POST'])
def login():
    with open(credentials_file, 'r') as cred_file:
        users = json.load(cred_file)
    print(users)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username] == password:
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
