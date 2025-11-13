#!/bin/bash
# Bash script to setup .env file for development

ENV_FILE=".env"
ENV_EXAMPLE_FILE=".env.example"

echo "🔧 GestiQCloud Environment Setup"
echo ""

if [ -f "$ENV_FILE" ]; then
    echo "⚠️  El archivo .env ya existe."
    read -p "¿Deseas sobrescribirlo? (y/N): " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelado."
        exit 0
    fi
fi

if [ ! -f "$ENV_EXAMPLE_FILE" ]; then
    echo "❌ Error: No se encuentra $ENV_EXAMPLE_FILE"
    exit 1
fi

echo "📋 Copiando $ENV_EXAMPLE_FILE a $ENV_FILE..."
cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"

echo ""
echo "✅ Archivo .env creado exitosamente!"
echo ""
echo "⚠️  IMPORTANTE: Edita el archivo .env y configura:"
echo "   - EMAIL_HOST_PASSWORD (tu password de Mailtrap)"
echo "   - JWT_SECRET_KEY (para producción usa uno seguro)"
echo ""
echo "📝 Para editar: nano .env  o  code .env"
echo ""
echo "🚀 Luego ejecuta: docker compose up --build tenant admin backend"
echo ""
