from flask_wtf import FlaskForm, RecaptchaField, Recaptcha
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    recaptcha = RecaptchaField(validators=[Recaptcha(message="You're not a robot... are you?")])
    submit = SubmitField('Send')