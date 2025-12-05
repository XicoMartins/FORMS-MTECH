from django import forms
from .excel_utils import (
    get_unique_choices,
    get_process_choices_for_ferramental,
)


class RegistroProducaoForm(forms.Form):
    # Listas suspensas, alimentadas pela planilha
    cliente = forms.ChoiceField(label="Cliente", choices=[])
    acabado = forms.ChoiceField(label="Display (Acabado)", choices=[])
    # removidos: semiacabado e tipo
    ferramental = forms.ChoiceField(label="Ferramental / Máquina", choices=[])
    processo = forms.ChoiceField(label="Processo", choices=[])

    # Campos que o operador realmente preenche
    hora_iniciada = forms.TimeField(
        label="Hora iniciada",
        widget=forms.TimeInput(format="%H:%M"),
        input_formats=["%H:%M"],
    )
    hora_finalizada = forms.TimeField(
        label="Hora finalizada",
        widget=forms.TimeInput(format="%H:%M"),
        input_formats=["%H:%M"],
    )
    quantidade_produzida = forms.IntegerField(label="Quantidade produzida", min_value=0)
    numero_operadores = forms.IntegerField(label="Número de operadores", min_value=1)
    quantidade_total = forms.IntegerField(label="Quantidade total", min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Choices básicos (não dependem de outro campo)
        self.fields["cliente"].choices = get_unique_choices("CLIENTE")
        self.fields["acabado"].choices = get_unique_choices("ACABADO")
        self.fields["ferramental"].choices = get_unique_choices("FERRAMENTAL")

        # Descobrir qual ferramental está selecionado (POST ou GET)
        data = self.data or self.initial
        selected_ferramental = data.get("ferramental")

        # Agora, monta os processos apenas para esse ferramental
        self.fields["processo"].choices = get_process_choices_for_ferramental(
            selected_ferramental
        )