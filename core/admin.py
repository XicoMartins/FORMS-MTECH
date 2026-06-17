from django.contrib import admin
from .models import (
    DisplayMachineProcessRule,
    DisplayType,
    Machine,
    Process,
    ProductionEntry,
    ProductionRecord,
)


@admin.register(DisplayType)
class DisplayTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome')
    search_fields = ('nome',)


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome')
    search_fields = ('nome',)


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome')
    search_fields = ('nome',)


@admin.register(DisplayMachineProcessRule)
class DisplayMachineProcessRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'display', 'machine', 'process')
    list_filter = ('display', 'machine', 'process')
    search_fields = ('display__nome', 'machine__nome', 'process__nome')


@admin.register(ProductionRecord)
class ProductionRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'display', 'machine', 'process', 'quantidade', 'data_hora')
    list_filter = ('display', 'machine', 'process')
    search_fields = ('display__nome', 'machine__nome', 'process__nome')


@admin.register(ProductionEntry)
class ProductionEntryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'timestamp',
        'cliente',
        'display',
        'maquinario',
        'processo',
        'quantidade',
        'quantidade_total',
    )
    list_filter = ('cliente', 'maquinario', 'processo', 'schema_version')
    search_fields = (
        'cliente',
        'display',
        'numero_display',
        'maquinario',
        'processo',
        'operadores',
    )
    ordering = ('-timestamp', '-id')
