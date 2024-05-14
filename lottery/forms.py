from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import InputRequired, ValidationError, DataRequired


class DrawForm(FlaskForm):
    number1 = IntegerField(id='no1')
    number2 = IntegerField(id='no2')
    number3 = IntegerField(id='no3')
    number4 = IntegerField(id='no4')
    number5 = IntegerField(id='no5')
    number6 = IntegerField(id='no6')
    submit = SubmitField("Submit Draw")

    # Override of validate function to check for 6 unique numbers submitted
    def validate(self, **kwargs):
        standard_validators = FlaskForm.validate(self)
        if standard_validators:
            fields = set()
            fields.add(self.number1._value())
            fields.add(self.number2._value())
            fields.add(self.number3._value())
            fields.add(self.number4._value())
            fields.add(self.number5._value())
            fields.add(self.number6._value())
            if len(fields) == 6:
                return True
        return False
