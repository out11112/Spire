"""Standalone Spire server tests (delegated LinkChat auth, room lifecycle, WS)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ['SPIRE_DATABASE_URL'] = 'sqlite://'

from fastapi.testclient import TestClient

from spire_server import auth as spire_auth
from spire_server.ids import new_id
from spire_server.main import app


class StandaloneSpireServerTests(unittest.TestCase):
    def setUp(self):
        spire_auth.clear_auth_cache()
        self.alice = spire_auth.SpireUser(id=new_id(), username='alice@example.com', nickname='Alice')
        self.bob = spire_auth.SpireUser(id=new_id(), username='bob@example.com', nickname='Bob')
        self.tokens = {
            'tok-alice': self.alice,
            'tok-bob': self.bob,
        }

        def fake_fetch(token: str) -> spire_auth.SpireUser:
            user = self.tokens.get(token)
            if not user:
                raise spire_auth.SpireApiError(401, 'invalid_token', '登录已过期或账号不可用，请重新登录。')
            return user

        self.patcher = patch.object(spire_auth, '_fetch_linkchat_user', side_effect=fake_fetch)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        spire_auth.clear_auth_cache()

    def test_health_and_unauthenticated_rejection(self):
        with TestClient(app) as client:
            health = client.get('/health')
            self.assertEqual(health.status_code, 200)
            body = health.json()
            self.assertEqual(body['status'], 'ok')
            self.assertEqual(body['database'], 'connected')
            self.assertEqual(body['protocol'], 8)

            unauth = client.get('/api/games/spire/rooms')
            self.assertEqual(unauth.status_code, 401)
            self.assertEqual(unauth.json()['error']['code'], 'unauthenticated')

    def test_room_create_list_ws_and_chat_with_bearer_session(self):
        with TestClient(app) as client:
            headers = {'Authorization': 'Bearer tok-alice'}
            catalog = client.get('/api/games/spire/catalog', headers=headers)
            self.assertEqual(catalog.status_code, 200)

            room_id = new_id()
            created = client.post(
                '/api/games/spire/rooms',
                headers=headers,
                json={'requestId': room_id, 'mode': 'solo'},
            )
            self.assertEqual(created.status_code, 200)
            self.assertEqual(created.json()['id'], room_id)

            listed = client.get('/api/games/spire/rooms', headers=headers)
            self.assertEqual(listed.status_code, 200)
            self.assertTrue(any(r['id'] == room_id for r in listed.json()['rooms']))

            with client.websocket_connect(
                f'/ws/games/spire/rooms/{room_id}?roomChat=1',
                headers=headers,
                subprotocols=['linkchat-game-v8'],
            ) as ws:
                first = ws.receive_json()
                self.assertEqual(first['protocol'], 8)
                self.assertIn('leaseId', first)
                ws.send_text('PING')
                self.assertEqual(ws.receive_text(), 'PONG')

                chat = client.post(
                    f'/api/games/spire/rooms/{room_id}/chat',
                    headers=headers,
                    json={'messageId': new_id(), 'leaseId': first['leaseId'], 'content': 'hello spire'},
                )
                self.assertEqual(chat.status_code, 200)


if __name__ == '__main__':
    unittest.main()
