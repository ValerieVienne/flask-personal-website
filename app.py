from flask import Flask, render_template, redirect, url_for, flash, request, session
from forms import ContactForm
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from dotenv import load_dotenv
from flask_session import Session
import os
import secrets
#print(secrets.token_hex(32))

#venv\Scripts\activate
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')

load_dotenv(dotenv_path)

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # change if not Gmail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # your email
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # your app password
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or app.config['MAIL_USERNAME']
#print("MAIL_USERNAME:", os.getenv("MAIL_USERNAME"))


# Session config
app.config['SESSION_TYPE'] = 'filesystem'  # Use server-side storage
app.config['SESSION_PERMANENT'] = False    # Sessions expire when browser closes
app.config['SESSION_FILE_DIR'] = './flask_session_data'  # Optional: where to store

# Init the session
Session(app)

mail = Mail(app)

csrf = CSRFProtect(app)

@app.route("/login", methods=["POST"])
def login():
    session["user_id"] = 42  # This is now saved on the server
    return redirect("/")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/projects')
def projects():
    my_projects = [
        {"title": "Chatbot with GPT", "description": "Built with OpenAI API."},
        {"title": "Weather App", "description": "Uses Flask and OpenWeatherMap API."},
    ]
    return render_template('projects.html', projects=my_projects)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    print("Request method:", request.method)
    print("Form submitted:", form.validate_on_submit())
    print("Form errors:", form.errors)
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message_body = form.message.data

        msg = Message(f"New Contact Form Message from {name}",
                      recipients=[app.config['MAIL_USERNAME']])
        msg.body = f"From: {name} <{email}>\n\nMessage:\n{message_body}"
        
        try:
            mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            print(f"Error sending email: {e}")
            flash('There was an error sending your message. Please try again later.', 'danger')
        print("Form submitted:", form.validate_on_submit())
        print(form.errors)
        return redirect(url_for('contact'))
    return render_template('contact.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)

# app password ojar bftp jlky bolr
