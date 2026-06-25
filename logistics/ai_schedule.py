from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.db import transaction

from accounts.models import Operator
from logistics.models import Driver, Store, Order, ScheduleEntry, Turno

class WeekendScheduleAI:
    """
    Heurística de Escalas: Auto-Schedule.
    Ranqueia os motoristas baseando-se no volume de entregas bem sucedidas (COMPLETED)
    na última semana e preenche as escalas vagas de final de semana (Sábado e Domingo)
    automaticamente para as lojas (Stores) que possuem turnos definidos.
    """
    
    @staticmethod
    def suggest_weekend_schedules(operator: Operator):
        today = timezone.localdate()
        # Descobrir a data do próximo Sábado e Domingo
        days_ahead = 5 - today.weekday() # 5 = Sábado
        if days_ahead <= 0: # Já passou o Sábado desta semana, agenda pra próxima
            days_ahead += 7
            
        next_saturday = today + timedelta(days=days_ahead)
        next_sunday = next_saturday + timedelta(days=1)
        
        # Histórico: últimos 7 dias de produção
        history_start = today - timedelta(days=7)
        
        # 1. Ranquear os motoristas pela performance real (número de entregas concluídas)
        top_drivers = list(Driver.objects.filter(
            operator=operator,
            active=True
        ).annotate(
            completed_orders=Count('order', filter=Q(
                order__status=Order.OrderStatus.COMPLETED,
                order__businessDate__gte=history_start,
                order__businessDate__lte=today
            ))
        ).order_by('-completed_orders'))
        
        if not top_drivers:
            return "Nenhum motorista ativo para gerar escalas."
            
        # 2. Pegar todas as lojas que precisam de motoboys
        stores = Store.objects.filter(operator=operator)
        schedules_created = 0
        
        with transaction.atomic():
            for store in stores:
                # Pegar turnos de final de semana desta loja
                # Simulando que Turno tenha flag is_weekend ou pegamos todos e filtramos
                turnos = list(Turno.objects.filter(operator=operator, store=store))
                
                if not turnos:
                    continue
                
                # Para cada loja, precisamos alocar N motoristas (ex: 2 motoristas por turno de final de semana)
                needed_drivers = 2
                
                # Filtramos os top drivers que ainda não foram escalados na loja
                available_drivers = [d for d in top_drivers][:needed_drivers]
                
                for date in [next_saturday, next_sunday]:
                    for turno in turnos:
                        for driver in available_drivers:
                            # Verifica se já não existe
                            exists = ScheduleEntry.objects.filter(
                                operator=operator,
                                store=store,
                                driver=driver,
                                date=date,
                                turno=turno
                            ).exists()
                            
                            if not exists:
                                ScheduleEntry.objects.create(
                                    operator=operator,
                                    store=store,
                                    driver=driver,
                                    date=date,
                                    turno=turno
                                )
                                schedules_created += 1
                                
        return f"Escalas geradas com sucesso: {schedules_created} novos plantões para o final de semana."
