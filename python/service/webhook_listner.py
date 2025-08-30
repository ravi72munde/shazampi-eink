import webhook_listener

def process_post_request(request, *args, **kwargs):
    body_raw = request.body.read(int(request.headers['Content-Length'])) if int(request.headers.get('Content-Length', 0)) > 0 else '{}'
    body = json.loads(body_raw.decode('utf-8'))
    print("Received webhook data:", body)

handlers = {'POST': process_post_request}
listener = webhook_listener.Listener(handlers=handlers)
listener.start()
