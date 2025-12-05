from django.db import models


class DisplayType(models.Model):
    nome = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nome


class Machine(models.Model):
    nome = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nome


class Process(models.Model):
    nome = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nome


class DisplayMachineProcessRule(models.Model):
    """
    Define quais processos são permitidos para cada combinação de Display + Máquina.
    Ex.: Display X + Máquina Y -> pode Processo 1, 2, 3, 4
    """
    display = models.ForeignKey(DisplayType, on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('display', 'machine', 'process')

    def __str__(self):
        return f"{self.display} - {self.machine} - {self.process}"


class ProductionRecord(models.Model):
    """
    Registro de coleta de dados de produção.
    """
    display = models.ForeignKey(DisplayType, on_delete=models.PROTECT)
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT)
    process = models.ForeignKey(Process, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.display} | {self.machine} | {self.process} | {self.quantidade}"
