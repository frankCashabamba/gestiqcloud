#!/usr/bin/env python3
"""
Script de testing para sistema de notificaciones
"""

import sys
from uuid import uuid4

import requests

BASE_URL = "http://localhost:8000/api/v1/notifications"

# Headers (ajustar según autenticación)
HEADERS = {
    "Content-Type": "application/json",
    # "Authorization": "Bearer YOUR_TOKEN",
    # "X-Tenant-ID": "tenant-uuid"
}


def test_create_email_channel():
    """Test 1: Crear canal de email"""
    print("\n🧪 Test 1: Crear canal Email (Gmail)")

    payload = {
        "tipo": "email",
        "nombre": "SMTP Gmail Principal",
        "descripcion": "Canal de email para alertas y facturas",
        "config": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "test@gmail.com",
            "smtp_password": "app_password_here",
            "from_email": "GestiQCloud <test@gmail.com>",
            "use_tls": True,
            "default_recipient": "admin@empresa.com",
        },
        "activo": True,
        "use_for_alerts": True,
        "use_for_invoices": True,
        "use_for_marketing": False,
    }

    response = requests.post(f"{BASE_URL}/channels", headers=HEADERS, json=payload)

    if response.status_code == 201:
        data = response.json()
        print(f"✅ Canal creado: {data['id']}")
        print(f"   Nombre: {data['nombre']}")
        print(f"   Tipo: {data['tipo']}")
        return data["id"]
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None


def test_create_whatsapp_channel():
    """Test 2: Crear canal WhatsApp (Twilio)"""
    print("\n🧪 Test 2: Crear canal WhatsApp (Twilio)")

    payload = {
        "tipo": "whatsapp",
        "nombre": "WhatsApp Twilio",
        "config": {
            "provider": "twilio",
            "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "auth_token": "your_auth_token_here",
            "from_number": "+14155238886",
            "default_recipient": "+593987654321",
        },
        "activo": True,
        "use_for_alerts": True,
    }

    response = requests.post(f"{BASE_URL}/channels", headers=HEADERS, json=payload)

    if response.status_code == 201:
        data = response.json()
        print(f"✅ Canal creado: {data['id']}")
        return data["id"]
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None


def test_create_telegram_channel():
    """Test 3: Crear canal Telegram"""
    print("\n🧪 Test 3: Crear canal Telegram")

    payload = {
        "tipo": "telegram",
        "nombre": "Bot Telegram Alertas",
        "config": {
            "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "parse_mode": "HTML",
            "default_recipient": "123456789",
        },
        "activo": True,
        "use_for_alerts": True,
    }

    response = requests.post(f"{BASE_URL}/channels", headers=HEADERS, json=payload)

    if response.status_code == 201:
        data = response.json()
        print(f"✅ Canal creado: {data['id']}")
        return data["id"]
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None


def test_list_channels():
    """Test 4: Listar canales"""
    print("\n🧪 Test 4: Listar todos los canales")

    response = requests.get(f"{BASE_URL}/channels", headers=HEADERS)

    if response.status_code == 200:
        channels = response.json()
        print(f"✅ {len(channels)} canales encontrados:")
        for ch in channels:
            print(f"   - {ch['nombre']} ({ch['tipo']}) - Activo: {ch['activo']}")
        return channels
    else:
        print(f"❌ Error: {response.status_code}")
        return []


def test_send_notification(channel_id):
    """Test 5: Enviar notificación de prueba"""
    if not channel_id:
        print("\n⚠️  Saltando Test 5: No hay channel_id")
        return

    print("\n🧪 Test 5: Enviar notificación de prueba")

    payload = {
        "channel_id": str(channel_id),
        "destinatario": "test@example.com",  # Cambiar según tipo
    }

    response = requests.post(f"{BASE_URL}/test", headers=HEADERS, json=payload)

    if response.status_code == 202:
        data = response.json()
        print("✅ Notificación encolada")
        print(f"   Task ID: {data.get('task_id')}")
        print(f"   Mensaje: {data.get('message')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def test_view_logs():
    """Test 6: Ver logs de notificaciones"""
    print("\n🧪 Test 6: Ver logs de notificaciones (últimos 7 días)")

    response = requests.get(f"{BASE_URL}/log?days=7&limit=10", headers=HEADERS)

    if response.status_code == 200:
        logs = response.json()
        print(f"✅ {len(logs)} logs encontrados:")
        for log in logs[:5]:  # Mostrar solo primeros 5
            print(f"   - {log['tipo']} → {log['destinatario']} - {log['estado']}")
            if log.get("error_message"):
                print(f"     Error: {log['error_message']}")
    else:
        print(f"❌ Error: {response.status_code}")


def test_log_stats():
    """Test 7: Estadísticas de logs"""
    print("\n🧪 Test 7: Estadísticas de notificaciones (últimos 30 días)")

    response = requests.get(f"{BASE_URL}/log/stats?days=30", headers=HEADERS)

    if response.status_code == 200:
        stats = response.json()
        print("✅ Estadísticas:")
        print(f"   Total enviadas: {stats['total']}")
        print(f"   Por estado: {stats['by_status']}")
        print(f"   Por tipo: {stats['by_tipo']}")
    else:
        print(f"❌ Error: {response.status_code}")


def test_stock_alerts():
    """Test 8: Ver alertas de stock"""
    print("\n🧪 Test 8: Ver alertas de stock bajo")

    response = requests.get(
        f"{BASE_URL}/alerts?estado=active&limit=10", headers=HEADERS
    )

    if response.status_code == 200:
        alerts = response.json()
        print(f"✅ {len(alerts)} alertas activas:")
        for alert in alerts[:5]:
            print(f"   - Producto: {alert['product_id']}")
            print(
                f"     Nivel: {alert['nivel_actual']}/{alert['nivel_minimo']} (diff: {alert['diferencia']})"
            )
    else:
        print(f"❌ Error: {response.status_code}")


def test_update_channel(channel_id):
    """Test 9: Actualizar canal"""
    if not channel_id:
        print("\n⚠️  Saltando Test 9: No hay channel_id")
        return

    print("\n🧪 Test 9: Actualizar canal")

    payload = {"activo": False, "descripcion": "Canal desactivado temporalmente"}

    response = requests.put(
        f"{BASE_URL}/channels/{channel_id}", headers=HEADERS, json=payload
    )

    if response.status_code == 200:
        data = response.json()
        print("✅ Canal actualizado")
        print(f"   Activo: {data['activo']}")
        print(f"   Descripción: {data['descripcion']}")
    else:
        print(f"❌ Error: {response.status_code}")


def test_manual_send():
    """Test 10: Envío manual con config override"""
    print("\n🧪 Test 10: Envío manual con configuración custom")

    payload = {
        "tipo": "email",
        "destinatario": "test@example.com",
        "asunto": "Test Manual desde API",
        "mensaje": "<h1>Hola Mundo</h1><p>Este es un test manual.</p>",
        "config_override": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "test@gmail.com",
            "smtp_password": "app_password",
            "from_email": "test@gmail.com",
            "use_tls": True,
        },
        "ref_type": "test",
        "ref_id": str(uuid4()),
    }

    response = requests.post(f"{BASE_URL}/send", headers=HEADERS, json=payload)

    if response.status_code == 202:
        data = response.json()
        print("✅ Notificación encolada")
        print(f"   Task ID: {data.get('task_id')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def main():
    """Ejecutar todos los tests"""
    print("=" * 70)
    print("🚀 Testing Sistema de Notificaciones - GestiQCloud")
    print("=" * 70)

    try:
        # Crear canales
        email_channel_id = test_create_email_channel()
        whatsapp_channel_id = test_create_whatsapp_channel()
        telegram_channel_id = test_create_telegram_channel()

        # Listar canales
        test_list_channels()

        # Enviar prueba
        test_send_notification(email_channel_id)

        # Ver logs
        test_view_logs()
        test_log_stats()

        # Alertas
        test_stock_alerts()

        # Actualizar
        test_update_channel(email_channel_id)

        # Envío manual
        test_manual_send()

        print("\n" + "=" * 70)
        print("✅ Tests completados")
        print("=" * 70)

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se pudo conectar al servidor")
        print("   Asegúrate de que el backend esté corriendo en http://localhost:8000")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
