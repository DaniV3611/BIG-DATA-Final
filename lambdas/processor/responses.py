import json


CLIENT_ERROR_RESPONSE = {
    "statusCode": 500,
    "body": json.dumps({
        "message": "Error al descargar el archivo desde el bucket",
    }),
}

ERROR_RESPONSE = {
    "statusCode": 500,
    "body": json.dumps({
        "message": "Ocurrió un error inesperado:",
    }),
}

ERROR_NOT_FOUND_RESPONSE = {
    "statusCode": 400,
    "body": json.dumps({
        "message": "El archivo no es un HTML",
    }),
}

SUCCESS_RESPONSE = {
    "statusCode": 200,
    "body": json.dumps({
        "message": "Apartaesudios guardados",
    }),
}
