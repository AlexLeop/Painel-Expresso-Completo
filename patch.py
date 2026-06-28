import sys

with open('config/panel_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_balance = """@panel_api.get("/machine/credits/driver/balance")
def get_machine_driver_balance(request, condutor_id: str):
    return {"saldo": 0}"""

new_balance = """@panel_api.get("/machine/credits/driver/balance")
def get_machine_driver_balance(request, condutor_id: str):
    from finance.models import Wallet
    try:
        w = Wallet.objects.get(driver_id=condutor_id)
        return {"saldo": w.balanceCents / 100.0}
    except Wallet.DoesNotExist:
        return {"saldo": 0.0}"""

if old_balance in content:
    content = content.replace(old_balance, new_balance)
else:
    print('Failed to find balance endpoint')
    sys.exit(1)

old_estimate = """@panel_api.get("/machine/rides/estimate")
def get_machine_rides_estimate(
    request, 
    endereco_partida: str = "", 
    bairro_partida: str = "", 
    cidade_partida: str = "", 
    estado_partida: str = "",
    lat_partida: str = "", 
    lng_partida: str = "", 
    endereco_desejado: str = "", 
    bairro_desejado: str = "", 
    cidade_desejado: str = "", 
    estado_desejado: str = "",
    lat_desejado: str = "", 
    lng_desejado: str = ""
):
    return {
        "response": {
            "distancia": 5.0,
            "valor": 12.0
        }
    }"""

new_estimate = """@panel_api.get("/machine/rides/estimate", auth=auth_bearer)
def get_machine_rides_estimate(
    request, 
    endereco_partida: str = "", 
    bairro_partida: str = "", 
    cidade_partida: str = "", 
    estado_partida: str = "",
    lat_partida: str = "0", 
    lng_partida: str = "0", 
    endereco_desejado: str = "", 
    bairro_desejado: str = "", 
    cidade_desejado: str = "", 
    estado_desejado: str = "",
    lat_desejado: str = "0", 
    lng_desejado: str = "0"
):
    import math
    from finance.models import KmFaixa
    from accounts.models import StaffMember, Operator
    
    try:
        lat1, lon1 = float(lat_partida), float(lng_partida)
        lat2, lon2 = float(lat_desejado), float(lng_desejado)
        R = 6371.0
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distancia = R * c
    except (ValueError, TypeError):
        distancia = 0.0

    # Increase distance by 30% for street routing approximation
    distancia = distancia * 1.3
    
    uid = request.auth.get("sub")
    staff = StaffMember.objects.filter(supabase_uid=uid).first()
    operator_id = staff.operator_id if staff else None

    valor_cents = 1000 # default fallback R$ 10.00
    if operator_id:
        faixa = KmFaixa.objects.filter(operator_id=operator_id, kmStart__lte=distancia, kmEnd__gt=distancia).first()
        if faixa:
            valor_cents = faixa.priceCents
        else:
            faixa_max = KmFaixa.objects.filter(operator_id=operator_id).order_by('-kmEnd').first()
            if faixa_max and distancia >= faixa_max.kmEnd:
                valor_cents = faixa_max.priceCents
            elif KmFaixa.objects.filter(operator_id=operator_id).exists():
                faixa_min = KmFaixa.objects.filter(operator_id=operator_id).order_by('kmStart').first()
                if faixa_min:
                    valor_cents = faixa_min.priceCents

    return {
        "response": {
            "distancia": round(distancia, 2),
            "valor": valor_cents / 100.0
        }
    }"""

if old_estimate in content:
    content = content.replace(old_estimate, new_estimate)
else:
    print('Failed to find estimate endpoint')
    sys.exit(1)

with open('config/panel_api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Successfully updated panel_api.py')
