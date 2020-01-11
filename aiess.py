from notAiess import notAiess, helper, Handler
from datetime import datetime, timedelta
import aiohttp
import aiofiles
import asyncio
import config
from universal import db as connection

from universal.classes import Hook, Status, Mode


class Rememberer(Handler):
    def __init__(self):
        pass

    async def post_event(self, session, e, hook, embed):
        print("Posting to:", hook)
        r = await session.post(hook, json={
            'content': e.event_source_url,
            'embeds': [embed]
        })
        
        if r.status != 204:
            if (await r.json())['code'] in (50027, 10015):
                print("Revoking:", hook)
                await connection.query(["UPDATE hooks SET status='Cannot send hook, possibly gone -- Won't send anymore.' WHERE hook_url=?", [hook]])
        elif r.status == 429:
            print("Got rate limited; retrying")
            await asyncio.sleep(r.header['X-RateLimit-Reset-After'])
            await self.post_event(session, e, hook, embed)
        r.close()

    async def on_map_event(self, e):
        mode_mapping = {
            "osu": Mode.std,
            "taiko": Mode.taiko,
            "catch": Mode.catch,
            "mania": Mode.mania
        }

        status_mapping = {
            "Bubbled": Status.bubble,
            "Qualified": Status.qualify,
            "Disqualified": Status.disqualify,
            "Popped": Status.pop,
            "Ranked": Status.ranked,
            "Loved": Status.loved
        }

        print("Event received")
        print("Updating last count")
        async with aiofiles.open('last.txt', mode='w') as f:
            await f.write((e.time + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00"))

        print("Generating embed")
        embed = await helper.gen_embed(e)
        targets = []
        print("Querying targets")
        hooks = await connection.query("SELECT * FROM hooks")

        for hook in hooks:
            hook_cls = Hook(hook)
            for mode in e.gamemodes:
                if mode_mapping[mode] in hook_cls.mode and status_mapping[e.event_type] in hook_cls.push_status and not hook_cls.status:
                    targets.append(hook_cls.hook_url)

        targets = list(set(targets))
        for target in targets:
            async with aiohttp.ClientSession() as session:
                await self.post_event(session, e, target, embed)


def main():
    try:
        with open('last.txt', 'r') as f:
            dt = datetime.strptime(f.read().strip(),
                                   '%Y-%m-%dT%H:%M:%S+00:00')
    except:
        open('last.txt', 'w').close()
        dt = datetime(1990, 1, 1)

    handlers = [
        Rememberer()
    ]

    nA = notAiess(config.osu_token,
                  dt, handlers=handlers)
    nA.disable_user = True
    nA.run()


if __name__ == "__main__":
    main()
