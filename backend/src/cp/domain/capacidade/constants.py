"""Constantes do domínio de Capacidade.

Centraliza valores fixos de negócio para evitar magic numbers espalhados.
"""

# Dias úteis da semana: segunda (0) a sexta (4)
DIAS_UTEIS_SEMANA = range(0, 5)

# Capacidade padrão quando nenhum parâmetro está configurado
MINUTOS_DIA_UTIL_DEFAULT = 360    # 6 horas (seg–qui)
MINUTOS_SEXTA_DEFAULT = 240       # 4 horas (sexta)
MINUTOS_EXTRA_MAXIMO_DEFAULT = 600  # 10 horas
