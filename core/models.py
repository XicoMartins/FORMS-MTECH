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


class ProductionEntry(models.Model):
    import_key = models.CharField(max_length=500, null=True, blank=True, unique=True)
    source_hash = models.CharField(max_length=64, editable=False, db_index=True)
    schema_version = models.CharField(max_length=20, blank=True, default="")
    timestamp = models.DateTimeField(db_index=True, null=True, blank=True)
    cliente = models.CharField(max_length=255)
    display = models.CharField(max_length=255)
    numero_display = models.CharField(max_length=100, blank=True, default="")
    maquinario = models.CharField(max_length=255)
    processo = models.CharField(max_length=255)
    data_producao = models.CharField(max_length=20, blank=True, default="")
    operadores = models.TextField(blank=True, default="")
    numero_operadores = models.PositiveIntegerField(null=True, blank=True)
    hora_inicio = models.CharField(max_length=10, blank=True, default="")
    hora_fim = models.CharField(max_length=10, blank=True, default="")
    quantidade = models.PositiveIntegerField(default=0)
    pecas_mortas = models.PositiveIntegerField(default=0)
    quantidade_total = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-timestamp", "-id")
        verbose_name = "Registro de producao"
        verbose_name_plural = "Registros de producao"

    def __str__(self):
        timestamp_display = (
            self.timestamp.strftime("%d/%m/%Y %H:%M")
            if self.timestamp
            else "sem timestamp"
        )
        return (
            f"{timestamp_display} | {self.cliente} | {self.display} | {self.processo}"
        )
