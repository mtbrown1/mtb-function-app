from azure.communication.email import EmailClient
from jsonschema import validate, ValidationError, SchemaError
import azure.functions as func
import logging, json, os


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

send_email_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1
        },
        "company": {
            "type": "string"
        },
        "email": {
            "type": "string",
            "pattern": "^[a-z0-9_.±]+@[a-z0-9.-]+(\.[a-z]{2,})+$",
            "message": "Boop"
        },
        "message": {
            "type": "string",
            "minLength": 1
        }
    },
    "required": ["name", "email", "message"]
}

@app.route(route="emailMe")
def emailMe(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processing the emailMe request.')
    req_body = req.get_json()

    try:
        validate(req_body, send_email_schema)

        connection_string = os.environ["EMAIL_SERVICE_CONNECTION_STRING"]
        client = EmailClient.from_connection_string(connection_string)

        person = req_body['name']
        if req_body['company']:
            person += " from " + req_body['company']

        subject = "Contact Request: " + person
        plaintext = f'{req_body}'

        html = f"""
            <html>
                <body>
                    <div>{person} wants to reach out to you!</div>
                    <div>Message: </div>
                    <div>{req_body["message"]}</div>
                    <div>Reach out to {req_body['name']} at {req_body["email"]}
                </body>
            </html>
        """

        message = {
            "senderAddress": "ContactMe@mattbrownsoftware.dev",
            "recipients": {
                "to": [{"address": os.environ["CONTACT_EMAIL_ADDRESS"]}]
            },
            "content": {
                "subject": subject,
                "plainText": plaintext,
                "html": html
            },
        }
        poller = client.begin_send(message)
        result = poller.result()
        logging.info(f"Message sent: {result}")

    except ValidationError as ve:
        logging.info(f"Failure due to invalid params: {ve}")
        message = ve.message
        print(ve.validator, ve.validator_value, ve.json_path)
        print(ve.__dict__)
        if "email" in ve.json_path:
            message = f"{ve.instance} is not a valid email address"
        elif ve.validator == "minLength":
            message = f"'{ve.json_path[2:]}' should be non-empty"
        return func.HttpResponse(json.dumps({'status': 'failure', 'reason': f'Bad Parameters: {message}'}), mimetype='application/json', status_code=400) 

    except Exception as ex:
        logging.error(f"Server error: {ex}")
        return func.HttpResponse(json.dumps({'status': 'failure', 'reason': str(ex)}), mimetype='application/json', status_code=500)

    return func.HttpResponse(json.dumps({'status': 'success'}), mimetype='application/json', status_code=200)