import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("GATEWAY_PORT", "9000"))
    app.run(host=host, port=port, debug=True)