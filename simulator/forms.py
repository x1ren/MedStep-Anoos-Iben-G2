from django import forms

from accounts.forms import BootstrapFormMixin

from .models import GramStainScenario, SimulationAttempt


class GramStainScenarioForm(BootstrapFormMixin, forms.ModelForm):
    """Lab Admin form for creating / editing a Gram stain scenario.

    `created_by` and `created_at` are set by the server, never by the form.
    """

    class Meta:
        model = GramStainScenario
        fields = (
            'title', 'specimen_name', 'gram_type', 'cell_shape', 'difficulty',
            'description',
            'crystal_violet_seconds', 'iodine_seconds', 'decolorizer_seconds',
            'safranin_seconds',
            'is_active',
        )
        labels = {
            'specimen_name': 'Specimen (organism)',
            'gram_type': 'Gram reaction',
            'crystal_violet_seconds': 'Crystal violet (s)',
            'iodine_seconds': "Gram's iodine (s)",
            'decolorizer_seconds': 'Decolorizer (s)',
            'safranin_seconds': 'Safranin (s)',
            'is_active': 'Active — visible to learners in the playground',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Practice #3: Pseudomonas aeruginosa'}),
            'specimen_name': forms.TextInput(attrs={'placeholder': 'e.g. Pseudomonas aeruginosa'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        clash = GramStainScenario.objects.filter(title__iexact=title).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError('A scenario with this title already exists.')
        return title

    def clean_specimen_name(self):
        return self.cleaned_data['specimen_name'].strip()

    def clean_description(self):
        return self.cleaned_data['description'].strip()


class LabNotesForm(BootstrapFormMixin, forms.ModelForm):
    """Learner's own observations on one of their attempts (the only editable field)."""

    lab_notes = forms.CharField(
        required=False,
        max_length=2000,
        label='Lab notes & observations',
        help_text='Private to you. Up to 2,000 characters.',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'e.g. Cells turned pink after 35 s of decolorizer — stop at ~15 s next time.',
        }),
    )

    class Meta:
        model = SimulationAttempt
        fields = ('lab_notes',)
