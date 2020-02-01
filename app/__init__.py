from universal import db as connection
from universal.classes import Mode, Status, Hook
import config
import re
import aiohttp
import copy

from authlib.integrations.starlette_client import OAuth

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.config import Config
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from starlette.templating import Jinja2Templates
from starlette.datastructures import Secret

import uvicorn

templates = Jinja2Templates(directory='app/templates')
cfg = Config('.env')

# OAUTH
oauth = OAuth(cfg)
oauth.register(
    name='discord',
    client_id=config.client_id,
    client_secret=config.client_secret,
    access_token_url='https://discordapp.com/api/oauth2/token',
    authorize_url='https://discordapp.com/api/oauth2/authorize',
    api_base_url='https://discordapp.com/api/v6/',
    client_kwargs={'scope': 'identify'},
)

# STATICS
UPDATE_HOOK = {
    "embeds": [{
        "title": ":information_source: notAiess Updated",
        "description": "Enabled mode: {}\r\nEnabled status: {}",
        "color": 9945713,
        "footer": {
            "icon_url": "https://a.ppy.sh/3378391",
            "text": "-Keitaro"
        }
    }]
}

GREETING_HOOK = {
    "embeds": [{
        "title": ":bell: notAiess running",
        "description": "Hello and thanks for using notAiess! I will now send you new updates from mapping! If you feel this is useful, please [Donate](https://paypal.me/rendyak)! (because I need to pay server rents)",
        "color": 9945713,
        "footer": {
            "icon_url": "https://a.ppy.sh/3378391",
            "text": "-Keitaro"
        }
    }, {
        "title": ":information_source: notAiess info",
        "description": "Enabled mode: {}\r\nEnabled status: {}",
        "color": 9945713,
        "footer": {
            "icon_url": "https://a.ppy.sh/3378391",
            "text": "-Keitaro"
        }
    }]
}

TEST_HOOK = {
    "embeds": [{
        "title": ":warning: notAiess test",
        "description": "If you see this, then notAiess *should* be working.",
        "color": 9945713,
        "footer": {
            "icon_url": "https://a.ppy.sh/3378391",
            "text": "-Keitaro"
        }
    }]
}

# HELPER
async def send_hook(url, js):
    async with aiohttp.ClientSession() as reqsession:
        async with reqsession.post(url, json=js) as response:
            if response.status >= 300:
                return response.status, await response.json()
            return response.status


async def request_discord(endpoint, token):
    async with aiohttp.ClientSession() as reqsession:
        async with reqsession.get('https://discordapp.com/api/v6/' + endpoint,
                                  headers={"Authorization": "Bearer " + token}) as response:
            return response.status, await response.json()

# REGEX STATIC
hook_re = re.compile(r'https://discordapp.com/api/webhooks/(\d+)/(.+)')
alert_pop = '<div class="alert alert-danger"><button type="button" class="close" data-dismiss="alert">&times;</button><strong>Error!</strong> {}</div>'

# ROUTES
async def not_found(request, exc):
    context = {
        'request': request
    }
    return templates.TemplateResponse("404.html", context)


async def server_error(request, exc):
    context = {
        'request': request
    }
    return templates.TemplateResponse("500.html", context)


async def root(request):
    user = request.session.get('user')
    username = None
    extras = None
    if user:
        status, js = await request_discord('users/@me', user)
        if 300 <= status < 500:
            extras = alert_pop.format(js['message'] + " - Please relogin.")
            request.session.pop('user')
        elif status >= 500:
            extras = alert_pop.format(js['Discord seems to be tripping.'])
            request.session.pop('user')
        else:
            username = js['username']
            request.session['uid'] = js['id']

    context = {
        'request': request,
        'extras': extras,
        'username': username
    }
    return templates.TemplateResponse("root.html", context)


async def add_hook(request):
    # Copy greet so it doesn't change globally
    greet = copy.copy(GREETING_HOOK)
    req_js = await request.json()
    uid = request.session.get('uid')

    if not uid:
        return JSONResponse({'err': 'Unauthorized.'}, status_code=401)

    hook_url = req_js.get('hook_url')
    mode = req_js.get('mode', 15)
    status = req_js.get('status', 63)

    # Invalid checks
    # mode -> 0 < mode < 16
    # status -> 0 < status < 64
    # URL should always match with hook_re.
    if type(mode) != int or not 0 < mode < 16:
        return JSONResponse({'err': 'Invalid mode: ' + str(mode)}, status_code=400)
    if type(status) != int or not 0 < status < 64:
        return JSONResponse({'err': 'Invalid status: ' + str(status)}, status_code=400)

    mode_class = Mode(mode)
    status_class = Status(status)
    match = hook_re.match(hook_url)

    if not match:
        return JSONResponse({'err': 'Invalid hook url.'}, status_code=400)

    # Group 1 is webhook id, group 2 is webhook token.
    # if one of them is missing, then it is not a valid hook url.
    hook_id, hook_token = match[1], match[2]
    hook_token = hook_token if hook_token[-1] != "/" else hook_token[0:-1]
    if not hook_id or not hook_token:
        return JSONResponse({'err': 'Invalid hook url.'}, status_code=400)

    # Check if webhook already exists by its token and id.
    # Do not check with URL as the check might fail if one character is different.
    existing = await connection.query([
        "SELECT * FROM hooks WHERE webhook_id=? AND webhook_token=?",
        [hook_id, hook_token]
    ])
    if existing:
        return JSONResponse({'err': 'Hook already exist.'}, status_code=400)

    # Embed stuff. TODO: Make it look nicer to read
    greet['embeds'][1]['description'] = greet['embeds'][1]['description'].format(
        str(mode_class), str(status_class))
    resp = await send_hook(hook_url, greet)

    # If send_hook returns a tuple, then something is wrong.
    if type(resp) == tuple:
        return JSONResponse({'err': resp[1]['message']}, status_code=400)

    await connection.query([
        "INSERT INTO hooks (hook_url, webhook_id, webhook_token, mode, push_status, uid) VALUES (?, ?, ?, ?, ?, ?)",
        [hook_url, hook_id, hook_token, mode,
            status, uid]
    ])
    return JSONResponse({"message": "OK!"})


async def test_hook(request):
    req_js = await request.json()
    hook_url = req_js.get('hook_url')

    match = hook_re.match(hook_url)
    if not match:
        return JSONResponse({'err': 'Invalid hook url.'}, status_code=400)

    hook_id, hook_token = match[1], match[2]
    hook_token = hook_token if hook_token[-1] != "/" else hook_token[0:-1]
    if not hook_id or not hook_token:
        return JSONResponse({'err': 'Invalid hook url.'}, status_code=400)

    resp = await send_hook(hook_url, TEST_HOOK)

    if type(resp) == tuple:
        return JSONResponse({'err': resp[1]['message']}, status_code=400)

    return JSONResponse({"message": "OK!"})


async def edit_hook(request):
    hook_id = request.path_params['hook_id']
    hook = await connection.query([
        "SELECT * FROM hooks WHERE webhook_id=?",
        [hook_id]
    ])

    if not hook:
        return JSONResponse({"err": "Hook doesn't exist."}, status_code=400)

    hook = Hook(hook[0])
    if request.method == "DELETE":
        await connection.query([
            "DELETE FROM hooks WHERE webhook_id=?",
            [hook_id]
        ])
        return JSONResponse({"message": "OK!"})
    elif request.method == "PATCH":
        update = copy.copy(UPDATE_HOOK)

        reqjs = await request.json()
        if "webhook_id" in reqjs: reqjs.pop("webhook_id")
        if "webhook_token" in reqjs: reqjs.pop("webhook_token")
        if "uid" in reqjs: reqjs.pop("uid")
        try:
            mode = reqjs.pop("mode")
            status = reqjs.pop("status")
        except:
            return JSONResponse({"err": "Missing mode or status."}, status_code=400)

        if type(mode) != int or not 0 < mode < 16:
            return JSONResponse({'err': 'Invalid mode: ' + str(mode)}, status_code=400)
        if type(status) != int or not 0 < status < 64:
            return JSONResponse({'err': 'Invalid status: ' + str(status)}, status_code=400)

        for k, v in reqjs.items():
            setattr(hook, k, v)
        hook.mode = Mode(mode)
        hook.push_status = Status(status)

        await connection.query([
            """
            UPDATE hooks
            SET hook_url = ?,
                webhook_id = ?,
                webhook_token = ?,
                mode = ?,
                push_status = ?,
                status = ?,
                uid = ?
            WHERE webhook_id = ?
            """,
            list(hook) + [hook_id]
        ])
        update['embeds'][0]['description'] = update['embeds'][0]['description'].format(
            str(hook.mode), str(hook.status))
        resp = await send_hook(hook.hook_url, update)

        return JSONResponse({"message": "OK!"})


async def list_hook(request):
    js = []
    hooks = await connection.query([
        "SELECT * FROM hooks WHERE uid=?",
        [request.session.get("uid")]
    ])
    for hook in hooks:
        js.append(Hook(hook).to_dict())
    return JSONResponse(js)


async def login(request):
    redirect_uri = request.url_for('auth')
    return await oauth.discord.authorize_redirect(request, redirect_uri)


async def auth(request):
    user = await oauth.discord.authorize_access_token(request)
    request.session['user'] = user['access_token']
    return RedirectResponse(request.url_for('root'))


async def logout(request):
    request.session.pop('user', None)
    return RedirectResponse(request.url_for('root'))

# APP
async def start():
    await connection.connect()

async def stop():
    await connection.db.close()

exception_handlers = {
    404: not_found,
    500: server_error
}

routes = [
    Route('/', root, name="root"),
    Route('/login', login, name="login"),
    Route('/auth', auth, name="auth"),
    Route('/logout', logout, name="logout"),
    Route('/list', list_hook),
    Route('/{hook_id:int}', edit_hook, methods=["DELETE", "PATCH"]),
    Route('/test', test_hook, methods=["POST"]),
    Route('/add', add_hook, methods=["POST"]),
    Mount('/', StaticFiles(directory="app/static"))
]

app = Starlette(debug=False, routes=routes, middleware=[
    Middleware(SessionMiddleware, secret_key=cfg('SECRET_KEY', cast=Secret))
], exception_handlers=exception_handlers, on_startup=[start], on_shutdown=[stop])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
