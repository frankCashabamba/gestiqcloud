try:
    with open(".env.local", "rb") as f:
        data = f.read()

    found = False
    for i, byte in enumerate(data):
        if byte == 0xF3:
            found = True
            start = max(0, i - 50)
            end = min(len(data), i + 50)
            print(f"Byte 0xF3 encontrado en posición {i}")
            context = data[start:end].decode("utf-8", errors="replace")
            print(f"Contexto:\n{context}\n")

    if not found:
        print("No se encontró el byte 0xF3 en .env.local")
        print("Verificando .env...")
        with open(".env", "rb") as f:
            data = f.read()

        for i, byte in enumerate(data):
            if byte == 0xF3:
                found = True
                start = max(0, i - 50)
                end = min(len(data), i + 50)
                print(f"Byte 0xF3 encontrado en .env en posición {i}")
                context = data[start:end].decode("utf-8", errors="replace")
                print(f"Contexto:\n{context}\n")

        if not found:
            print("No se encontró el byte 0xF3 en .env tampoco")

except Exception as e:
    print(f"Error: {e}")
