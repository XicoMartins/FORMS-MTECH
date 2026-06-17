import csv
import re
from datetime import datetime

OUTPUT_FIELDS = [
    "ID",
    "Timestamp",
    "Cliente",
    "Display",
    "Maquinário",
    "Processo",
    "Data",
    "Operadores",
    "Numero Operadores",
    "Hora Início",
    "Hora Fim",
    "Quantidade",
    "Peças Mortas",
    "Quantidade Total",
]


def contar_operadores(texto):
    if not texto:
        return "0"
    partes = [p.strip() for p in re.split(r"[;|,]", texto) if p.strip()]
    return str(len(partes)) if partes else "0"

def converter_data_antiga(data_str):
    """Converte data do formato antigo para DD/MM/YY"""
    if not data_str or data_str.strip() == '':
        return ''
    
    try:
        # Tenta vários formatos possíveis
        formatos = ['%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y']
        for fmt in formatos:
            try:
                data_obj = datetime.strptime(data_str.strip(), fmt)
                return data_obj.strftime('%d/%m/%y')
            except:
                continue
        return data_str
    except:
        return data_str

def processar_linha_antiga(linha):
    """Converte uma linha do formato antigo para o novo formato"""
    try:
        # Linha antiga tem muitos campos separados por ;
        # Vamos extrair os campos importantes
        
        # Campos importantes (baseado na análise):
        # [6]: DATA DA PRODUÇÃO
        # [7]: HORÁRIO DE INICIO
        # [8]: HORÁRIO DE TÉRMINO
        # [9]: DISPLAY PRODUZIDO
        # [10]: MAQUINÁRIO
        # [12]: PROCESSO REALIZADO
        # [14]: OPERADOR
        # [15]: QUANTIDADE PRODUZIDA
        # [16]: QUANTIDADE TOTAL
        # [18]: RESPONSAVEL PELO PREENCHIMENTO
        # [19]: PEÇAS MORTAS
        
        if len(linha) < 20:
            return None
            
        # Extrair cliente e display do campo 9
        display_completo = linha[9].strip() if len(linha) > 9 else ''
        
        # Tentar extrair cliente e display
        # Formato: "CLIENTE - LOTE XXX" ou similar
        if ' - ' in display_completo:
            partes = display_completo.split(' - ')
            cliente = partes[0].strip()
            display = ' - '.join(partes[1:]).strip() if len(partes) > 1 else display_completo
        else:
            cliente = display_completo
            display = display_completo
        
        # Se o cliente estiver vazio, tentar usar o último campo (DE PARA)
        if not cliente and len(linha) > 20:
            de_para = linha[20].strip()
            if de_para:
                partes_de_para = de_para.split()
                if len(partes_de_para) > 0:
                    cliente = partes_de_para[0]
        
        # Padronizar cliente
        if 'PILAO' in cliente.upper() or 'PILÃO' in cliente.upper():
            cliente = 'JDE COFFEE'
            display = 'DISPLAY ARAMADO P PILÃO'
        elif 'NEXCARE' in cliente.upper():
            cliente = 'ARAMADO NEXCARE'
        elif 'SIMPLE LIFE' in cliente.upper():
            cliente = 'SIMPLE LIFE'
        elif 'NIVEA' in cliente.upper():
            cliente = 'NIVEA'
        elif 'RACK' in cliente.upper() and 'CRYSTAL' in cliente.upper():
            cliente = 'RACK SLIM CRYSTAL'
        
        # Extrair outros campos
        data_producao = converter_data_antiga(linha[6].strip() if len(linha) > 6 else '')
        hora_inicio = linha[7].strip() if len(linha) > 7 else '00:00'
        hora_fim = linha[8].strip() if len(linha) > 8 else '00:00'
        maquinario = linha[10].strip() if len(linha) > 10 else ''
        processo = linha[12].strip() if len(linha) > 12 else ''
        
        # Limpar operadores (remover ; extras)
        operadores_raw = linha[14].strip() if len(linha) > 14 else ''
        operadores = operadores_raw.replace(';', '').strip()
        numero_operadores = contar_operadores(operadores)
        
        # Quantidade
        try:
            quantidade = int(linha[15].strip()) if len(linha) > 15 and linha[15].strip() else 0
        except:
            quantidade = 0
        
        # Peças mortas
        try:
            pecas_mortas_str = linha[19].strip() if len(linha) > 19 else '0'
            # Extrair apenas números
            pecas_mortas = int(re.sub(r'[^0-9]', '', pecas_mortas_str)) if pecas_mortas_str else 0
        except:
            pecas_mortas = 0
        
        # Quantidade total
        try:
            qtd_total = int(linha[16].strip()) if len(linha) > 16 and linha[16].strip() else quantidade
        except:
            qtd_total = quantidade
        
        # Criar timestamp (usar data atual como fallback)
        timestamp = datetime.now().isoformat()
        
        # Montar linha no novo formato
        nova_linha = [
            '1.0',  # ID
            timestamp,
            cliente,
            display,
            maquinario,
            processo,
            data_producao,
            operadores,
            numero_operadores,
            hora_inicio,
            hora_fim,
            str(quantidade),
            str(pecas_mortas),
            str(qtd_total),
        ]
        
        return nova_linha
        
    except Exception as e:
        print(f"Erro ao processar linha: {e}")
        return None

def padronizar_csv():
    """Padroniza o arquivo registros.csv"""
    arquivo_entrada = 'output/registros.csv'
    arquivo_saida = 'output/registros_padronizado.csv'
    
    linhas_novas = []
    linhas_antigas = []
    
    print("Lendo arquivo original...")
    
    total_linhas = 0
    # Processar cada linha do arquivo
    with open(arquivo_entrada, 'r', encoding='utf-8', errors='replace', newline='') as f:
        for i, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue

            total_linhas += 1

            # Detecta delimitador por linha (mistura de formatos)
            if line.count(',') >= 10:
                delimiter = ','
            elif ';' in line:
                delimiter = ';'
            else:
                continue

            row = next(csv.reader([line], delimiter=delimiter))
            if not row:
                continue

            # Pular cabecalho
            if str(row[0]).strip().upper() == "ID":
                continue

            if delimiter == ',':
                # Linha ja esta no formato novo (com ou sem Numero Operadores)
                if len(row) == len(OUTPUT_FIELDS) - 1:
                    operadores = row[7] if len(row) > 7 else ''
                    numero_operadores = contar_operadores(operadores)
                    row = row[:8] + [numero_operadores] + row[8:]
                elif len(row) < len(OUTPUT_FIELDS):
                    while len(row) < len(OUTPUT_FIELDS):
                        row.append('')
                elif len(row) > len(OUTPUT_FIELDS):
                    row = row[:len(OUTPUT_FIELDS)]

                linhas_novas.append(row)
            else:
                # Linha no formato antigo - converter
                nova_linha = processar_linha_antiga(row)

                if nova_linha:
                    linhas_novas.append(nova_linha)
                    linhas_antigas.append(i)
    
    print(f"Total de linhas lidas: {total_linhas}")
    print(f"Linhas convertidas: {len(linhas_antigas)}")
    print(f"Total de linhas no novo formato: {len(linhas_novas)}")
    
    # Escrever arquivo padronizado
    print("Escrevendo arquivo padronizado...")
    with open(arquivo_saida, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(OUTPUT_FIELDS)
        writer.writerows(linhas_novas)
    
    print(f"Arquivo padronizado salvo em: {arquivo_saida}")
    print(f"Linhas antigas convertidas: {linhas_antigas[:10]}... (primeiras 10)")

if __name__ == '__main__':
    padronizar_csv()
