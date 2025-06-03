import json
from main import main


def app(event, context):

    try:
        main()
    except Exception as e:
        print(f"❌ Error en la descarga de las páginas: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "❌ Error en la descarga de las páginas",
            }),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "✅ Se descargaron las páginas",
        }),
    }
