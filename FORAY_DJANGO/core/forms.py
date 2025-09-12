# core/forms.py
from django import forms

class ReviewForm(forms.Form):
    validated_name = forms.CharField(label="Validated Name", required=False)
    reviewer_name = forms.CharField(label="Your Name", required=True)

    STATUS_CHOICES = [
        ('REVIEWED', 'Reviewed'),
        ('PENDING',  'Pending'),
        ('SKIPPED',  'Skipped'),
    ]
    status = forms.ChoiceField(choices=STATUS_CHOICES, initial='REVIEWED', required=False)
