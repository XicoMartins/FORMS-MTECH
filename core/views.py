from django.shortcuts import render
from django.contrib import messages
from .forms import RegistroProducaoForm


def registrar_producao(request):
    if request.method == "POST":
        form = RegistroProducaoForm(request.POST)
        if form.is_valid():
            # Aqui você poderia salvar no banco de dados.
            # Por enquanto, vamos só mostrar uma mensagem de sucesso.
            messages.success(request, "Registro de produção salvo (ainda só em memória).")

            # Se quiser olhar os dados enviados:
            # print(form.cleaned_data)

            form = RegistroProducaoForm()
    else:
        form = RegistroProducaoForm()

    return render(request, "core/registrar_producao.html", {"form": form})