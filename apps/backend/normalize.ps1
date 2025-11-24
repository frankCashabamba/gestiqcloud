# Rename empresa to company
Write-Host "Renaming empresa folder to company..."
Rename-Item -Path "app\models\empresa" -NewName "company" -Force

Write-Host "Renaming venta.py to sale.py..."
Rename-Item -Path "app\models\sales\venta.py" -NewName "sale.py" -Force

Write-Host "Renaming compra.py to purchase.py..."
Rename-Item -Path "app\models\purchases\compra.py" -NewName "purchase.py" -Force

Write-Host "Done!"
