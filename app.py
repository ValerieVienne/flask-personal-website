from flask import Flask, render_template, redirect, url_for, flash, request, session, send_from_directory
from forms import ContactForm
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from dotenv import load_dotenv
from flask_session import Session
import os
import socket
import secrets
import gmail_api
#print(secrets.token_hex(32))

#.venv\Scripts\activate
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

app.config['RECAPTCHA_PUBLIC_KEY'] = os.getenv('RECAPTCHA_SITE_KEY')
app.config['RECAPTCHA_PRIVATE_KEY'] = os.getenv('RECAPTCHA_SECRET_KEY')

# Don't let SMTP (or any other socket) hang forever; a hung worker is killed
# by gunicorn after 30s and the visitor sees an error page.
socket.setdefaulttimeout(15)

# Make missing configuration obvious in the logs at startup.
_required_env = ['SECRET_KEY', 'MAIL_USERNAME',
                 'RECAPTCHA_SITE_KEY', 'RECAPTCHA_SECRET_KEY']
if not gmail_api.is_configured():
    # Without the Gmail API settings the app falls back to SMTP, which needs a
    # password (and is blocked on Render's free tier).
    _required_env.append('MAIL_PASSWORD')
_missing_env = [name for name in _required_env if not os.getenv(name)]
if _missing_env:
    app.logger.warning("Missing environment variables: %s", ", ".join(_missing_env))


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

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', title="Privacy Policy")

@app.route('/projects')
def projects():
    my_projects = [
        {"title": "Chatbot with GPT", "description": "Built with OpenAI API. #WORK IN PROGRESS"},        
    ]
    return render_template('projects.html', projects=my_projects)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    submitted = False
    #recaptcha= form.recaptcha.data
#    print("Request method:", request.method)
#    print("Form submitted:", form.validate_on_submit())
#    print("Form errors:", form.errors)
    #print(recaptcha)
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message_body = form.message.data
        #recaptcha= form.recaptcha.data

        subject = f"New Contact Form Message from {name}"
        body = f"From: {name} <{email}>\n\nMessage:\n{message_body}"

        try:
            if gmail_api.is_configured():
                # HTTPS - works on Render's free tier
                gmail_api.send_email(
                    to=app.config['MAIL_USERNAME'],
                    subject=subject,
                    body=body,
                    reply_to=email,
                )
            else:
                # SMTP fallback (fine locally; blocked on Render's free tier)
                msg = Message(subject, recipients=[app.config['MAIL_USERNAME']])
                msg.body = body
                mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
            submitted = True
        except Exception:
            # Log the real cause (SMTP auth, blocked port, timeout...) so it
            # shows up in the hosting provider's logs instead of vanishing.
            app.logger.exception("Contact form: sending email failed")
            flash('There was an error sending your message. Please try again later.', 'danger')
#        print("Form submitted:", form.validate_on_submit())
#        print(form.errors)
        return redirect(url_for('contact'))
    # Optional: show flash only on POST failure
    #elif request.method == 'POST':
    #    flash('Please fix the errors in the form before submitting.', 'danger')

#        print("Form errors:", form.errors)

  #      flash('reCAPTCHA verification failed. Please try again.', 'danger')   
    return render_template('contact.html', form=form)

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')

#@app.before_request
#def redirect_to_www():
#    if request.host == "valerie-vienne.com":
#        return redirect(request.url.replace("valerie-vienne.com", "www.valerie-vienne.com"), code=301)


if __name__ == '__main__':
    app.run(debug=True)

