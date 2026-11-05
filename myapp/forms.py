from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'autocomplete': 'name'}),
    )
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    request = forms.CharField(
        max_length=5000,
        widget=forms.Textarea(attrs={'rows': 5}),
    )


class CheckoutDetailsForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'autocomplete': 'name'}),
    )
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
