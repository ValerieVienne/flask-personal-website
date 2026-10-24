import json
from urllib import request as http
from urllib.error import URLError
from urllib.parse import urlencode

from flask import current_app
from flask_wtf import FlaskForm, RecaptchaField, Recaptcha
from wtforms import StringField, TextAreaField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Email, Length

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


class SafeRecaptcha(Recaptcha):
    """Recaptcha validator that never crashes the request.

    The stock Flask-WTF validator calls Google without a timeout and without
    catching network/HTTP/JSON errors, so any hiccup turns into a raw
    "Internal Server Error". Here every failure becomes a normal form
    validation error and is written to the server log with its real cause.
    """

    def _validate_recaptcha(self, response, remote_addr):
        private_key = current_app.config.get("RECAPTCHA_PRIVATE_KEY")
        if not private_key:
            current_app.logger.error(
                "RECAPTCHA_SECRET_KEY is not set - cannot verify reCAPTCHA."
            )
            raise ValidationError(
                "The contact form is temporarily unavailable. Please try again later."
            )

        data = urlencode(
            {"secret": private_key, "remoteip": remote_addr, "response": response}
        ).encode("utf-8")

        try:
            with http.urlopen(RECAPTCHA_VERIFY_URL, data, timeout=10) as resp:
                if resp.status != 200:
                    current_app.logger.error(
                        "reCAPTCHA verify returned HTTP %s", resp.status
                    )
                    return False
                result = json.loads(resp.read())
        except (URLError, TimeoutError, ValueError):
            # URLError covers HTTPError; ValueError covers bad JSON.
            current_app.logger.exception("reCAPTCHA verification request failed")
            raise ValidationError(
                "Could not verify the reCAPTCHA right now. Please try again."
            )

        if result.get("success"):
            return True

        current_app.logger.warning(
            "reCAPTCHA rejected the response: %s", result.get("error-codes")
        )
        return False


class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    recaptcha = RecaptchaField(validators=[SafeRecaptcha(message="You're not a robot... are you?")])
    submit = SubmitField('Send')
